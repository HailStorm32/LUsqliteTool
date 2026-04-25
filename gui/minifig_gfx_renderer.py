from __future__ import annotations

import copy
import logging
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import zlib

try:
    from PIL import Image, ImageDraw
except Exception:  # pragma: no cover - depends on local environment
    Image = None
    ImageDraw = None

from gui._vendor.swf.data import SWFShape
from gui._vendor.swf.geom import Matrix2
from gui._vendor.swf.movie import SWF
from gui._vendor.swf.tag import (
    TagDefineMorphShape,
    TagDefineMorphShape2,
    TagDefineShape,
    TagDefineShape2,
    TagDefineShape3,
    TagDefineShape4,
    TagDefineSprite,
    TagPlaceObject,
    TagPlaceObject2,
    TagPlaceObject3,
    TagRemoveObject,
    TagRemoveObject2,
    TagShowFrame,
)

log = logging.getLogger(__name__)

SHAPE_TAG_TYPES = (TagDefineShape, TagDefineShape2, TagDefineShape3, TagDefineShape4)
PLACE_TAG_TYPES = (TagPlaceObject, TagPlaceObject2, TagPlaceObject3)
REMOVE_TAG_TYPES = (TagRemoveObject, TagRemoveObject2)
MORPH_TAG_TYPES = (TagDefineMorphShape, TagDefineMorphShape2)
SUPERSAMPLE_SCALE = 4
CURVE_SEGMENTS = 10


@dataclass
class DrawOperation:
    kind: str
    points: list[tuple[float, float]]
    color: tuple[int, int, int, int]
    width: float = 1.0


@dataclass
class DisplayObjectState:
    character_id: int | None = None
    matrix: Matrix2 | None = None
    ratio: int = 0


def render_gfx_preview(source_path: Path, output_path: Path) -> Path | None:
    """Render the first frame of a Scaleform GFX file into a cached PNG."""
    if Image is None or ImageDraw is None:
        return None

    try:
        image = render_gfx_preview_image(source_path)
    except Exception:
        log.exception("Failed rendering GFX face preview from %s", source_path)
        return None

    if image is None:
        return None

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG")
    log.info("Cached minifig GFX face preview %s", output_path)
    return output_path


def render_gfx_preview_image(source_path: Path):
    """Render a transparent RGBA preview image for a face GFX asset."""
    swf = _load_gfx_as_swf(source_path)
    dictionary = swf.build_dictionary()
    operations: list[DrawOperation] = []
    _render_timeline(swf, dictionary, Matrix2(), operations)
    if not operations:
        return None
    return _rasterize_operations(operations, swf.header.frame_size)


def _load_gfx_as_swf(source_path: Path) -> SWF:
    raw = source_path.read_bytes()
    if raw[:3] != b"CFX":
        raise ValueError(f"{source_path} is not a supported CFX file.")
    swf_bytes = b"CWS" + raw[3:]
    return SWF(file=BytesIO(swf_bytes))


def _render_timeline(
    timeline,
    dictionary: dict[int, object],
    parent_matrix: Matrix2,
    operations: list[DrawOperation],
) -> None:
    display_list = _build_first_frame_display_list(timeline)
    for state in display_list:
        if state.character_id is None:
            continue
        definition = dictionary.get(state.character_id)
        if definition is None:
            continue

        combined_matrix = Matrix2(
            parent_matrix.a,
            parent_matrix.b,
            parent_matrix.c,
            parent_matrix.d,
            parent_matrix.tx,
            parent_matrix.ty,
        )
        if state.matrix is not None:
            combined_matrix.append_matrix(state.matrix)

        if isinstance(definition, SHAPE_TAG_TYPES):
            _render_shape(definition.shapes, combined_matrix, operations)
        elif isinstance(definition, MORPH_TAG_TYPES):
            shape = _coerce_morph_shape(definition, state.ratio)
            _render_shape(shape, combined_matrix, operations)
        elif isinstance(definition, TagDefineSprite):
            _render_timeline(definition, dictionary, combined_matrix, operations)


def _build_first_frame_display_list(timeline) -> list[DisplayObjectState]:
    display_by_depth: dict[int, DisplayObjectState] = {}

    for tag in timeline.tags:
        if isinstance(tag, TagShowFrame):
            break
        if isinstance(tag, REMOVE_TAG_TYPES):
            display_by_depth.pop(tag.depth, None)
            continue
        if not isinstance(tag, PLACE_TAG_TYPES):
            continue

        existing = display_by_depth.get(tag.depth)
        state = copy.deepcopy(existing) if existing is not None else DisplayObjectState()
        state.character_id = _get_character_id(tag, state)
        state.matrix = _get_matrix(tag, state)
        state.ratio = _get_ratio(tag, state)
        display_by_depth[tag.depth] = state

    return [display_by_depth[depth] for depth in sorted(display_by_depth)]


def _get_character_id(tag, existing: DisplayObjectState) -> int | None:
    if getattr(tag, "hasCharacter", False):
        return tag.characterId
    if isinstance(tag, TagPlaceObject):
        return tag.characterId
    return existing.character_id


def _get_matrix(tag, existing: DisplayObjectState) -> Matrix2 | None:
    if getattr(tag, "hasMatrix", False) or isinstance(tag, TagPlaceObject):
        return _swf_matrix_to_matrix2(tag.matrix)
    return existing.matrix


def _get_ratio(tag, existing: DisplayObjectState) -> int:
    if getattr(tag, "hasRatio", False):
        return int(tag.ratio)
    return existing.ratio


def _swf_matrix_to_matrix2(swf_matrix) -> Matrix2:
    return Matrix2(
        swf_matrix.scaleX,
        swf_matrix.rotateSkew0,
        swf_matrix.rotateSkew1,
        swf_matrix.scaleY,
        swf_matrix.translateX / 20.0,
        swf_matrix.translateY / 20.0,
    )


def _coerce_morph_shape(tag, ratio: int) -> SWFShape:
    # Static previews only need one frame, so morph shapes are rendered at the
    # placement ratio or their starting state when the ratio is absent.
    shape = copy.deepcopy(tag.startEdges)
    shape._fillStyles = [_coerce_morph_fill_style(style, ratio) for style in tag.morph_fill_styles]
    shape._lineStyles = [_coerce_morph_line_style(style, ratio) for style in tag.morph_line_styles]
    shape._edgeMapsCreated = False
    return shape


def _coerce_morph_fill_style(style, ratio: int):
    fill_type = getattr(style, "type", 0x0)
    fill = SimpleNamespace(type=fill_type)
    if fill_type == 0x0:
        fill.rgb = _interpolate_color(style.startColor, style.endColor, ratio)
    elif fill_type in {0x10, 0x12} and hasattr(style, "gradient"):
        records = []
        for record in getattr(style.gradient, "records", []):
            records.append(
                SimpleNamespace(
                    color=_interpolate_color(record.startColor, record.endColor, ratio),
                    ratio=int(round(_interpolate_value(record.startRatio, record.endRatio, ratio))),
                )
            )
        fill.gradient = SimpleNamespace(
            records=records,
            spreadmethod=0,
            interpolation_mode=0,
            focal_point=0.0,
        )
        fill.gradient_matrix = style.startGradientMatrix
    return fill


def _coerce_morph_line_style(style, ratio: int):
    line = SimpleNamespace(
        width=int(round(_interpolate_value(style.startWidth, style.endWidth, ratio))),
        start_caps_style=getattr(style, "startCapsStyle", 0),
        end_caps_style=getattr(style, "endCapsStyle", 0),
        joint_style=getattr(style, "jointStyle", 0),
        has_fill_flag=getattr(style, "hasFillFlag", False),
        no_hscale_flag=getattr(style, "noHScaleFlag", False),
        no_vscale_flag=getattr(style, "noVScaleFlag", False),
        pixelhinting_flag=getattr(style, "pixelHintingFlag", False),
        no_close=getattr(style, "noClose", False),
        miter_limit_factor=getattr(style, "miterLimitFactor", 3.0),
    )
    if line.has_fill_flag and getattr(style, "fillType", None) is not None:
        line.fill_type = _coerce_morph_fill_style(style.fillType, ratio)
    else:
        line.color = _interpolate_color(style.startColor, style.endColor, ratio)
        line.fill_type = None
    return line


def _interpolate_value(start: float, end: float, ratio: int) -> float:
    t = max(0.0, min(float(ratio) / 65535.0, 1.0))
    return start + (end - start) * t


def _interpolate_color(start: int, end: int, ratio: int) -> int:
    t = max(0.0, min(float(ratio) / 65535.0, 1.0))

    def channel(value: int, shift: int) -> int:
        return (value >> shift) & 0xFF

    start_a, start_r, start_g, start_b = (
        channel(start, 24),
        channel(start, 16),
        channel(start, 8),
        channel(start, 0),
    )
    end_a, end_r, end_g, end_b = (
        channel(end, 24),
        channel(end, 16),
        channel(end, 8),
        channel(end, 0),
    )
    result_a = int(round(start_a + (end_a - start_a) * t))
    result_r = int(round(start_r + (end_r - start_r) * t))
    result_g = int(round(start_g + (end_g - start_g) * t))
    result_b = int(round(start_b + (end_b - start_b) * t))
    return (result_a << 24) | (result_r << 16) | (result_g << 8) | result_b


def _render_shape(shape, matrix: Matrix2, operations: list[DrawOperation]) -> None:
    recorder = _ShapeRecorder(matrix, operations)
    shape.export(recorder)


class _ShapeRecorder:
    def __init__(self, matrix: Matrix2, operations: list[DrawOperation]) -> None:
        self._matrix = matrix
        self._operations = operations
        self._fill_color: tuple[int, int, int, int] | None = None
        self._line_color: tuple[int, int, int, int] | None = None
        self._line_width = 1.0
        self._fill_paths: list[list[tuple[float, float]]] = []
        self._line_paths: list[list[tuple[float, float]]] = []
        self._current_fill_path: list[tuple[float, float]] | None = None
        self._current_line_path: list[tuple[float, float]] | None = None
        self._last_point: tuple[float, float] | None = None

    def begin_shape(self):
        return None

    def end_shape(self):
        self._flush_fill()
        self._flush_line()

    def begin_fills(self):
        return None

    def end_fills(self):
        self._flush_fill()

    def begin_lines(self):
        return None

    def end_lines(self):
        self._flush_line()

    def begin_fill(self, color, alpha=1.0):
        self._flush_fill()
        self._fill_color = _argb_to_rgba(color, alpha)

    def begin_gradient_fill(self, _type, colors, alphas, _ratios, **_kwargs):
        fallback_color = colors[0] if colors else 0
        fallback_alpha = alphas[0] if alphas else 1.0
        self.begin_fill(fallback_color, fallback_alpha)

    def begin_bitmap_fill(self, *_args, **_kwargs):
        self._flush_fill()
        self._fill_color = None

    def end_fill(self):
        self._flush_fill()

    def line_style(
        self,
        thickness=float("nan"),
        color=0,
        alpha=1.0,
        *_args,
        **_kwargs,
    ):
        self._flush_line()
        self._line_color = _argb_to_rgba(color, alpha)
        self._line_width = 1.0 if thickness != thickness else max(float(thickness), 1.0)

    def line_gradient_style(self, thickness=float("nan"), *args, colors=None, alphas=None, **_kwargs):
        if colors is None and len(args) >= 8 and isinstance(args[7], list):
            colors = args[7]
        if alphas is None and len(args) >= 9 and isinstance(args[8], list):
            alphas = args[8]
        fallback_color = colors[0] if colors else 0
        fallback_alpha = alphas[0] if alphas else 1.0
        self.line_style(thickness=thickness, color=fallback_color, alpha=fallback_alpha)

    def line_bitmap_style(self, thickness=float("nan"), *_args, **_kwargs):
        self._flush_line()
        self._line_color = None
        self._line_width = 1.0 if thickness != thickness else max(float(thickness), 1.0)

    def move_to(self, x, y):
        point = self._transform_point(x, y)
        self._last_point = point
        if self._fill_color is not None:
            if self._current_fill_path:
                self._fill_paths.append(self._current_fill_path)
            self._current_fill_path = [point]
        if self._line_color is not None:
            if self._current_line_path:
                self._line_paths.append(self._current_line_path)
            self._current_line_path = [point]

    def line_to(self, x, y):
        point = self._transform_point(x, y)
        self._last_point = point
        if self._current_fill_path is not None:
            self._current_fill_path.append(point)
        if self._current_line_path is not None:
            self._current_line_path.append(point)

    def curve_to(self, cx, cy, ax, ay):
        if self._last_point is None:
            self.move_to(ax, ay)
            return
        start = self._last_point
        control = self._transform_point(cx, cy)
        end = self._transform_point(ax, ay)
        points = _sample_quadratic_curve(start, control, end, CURVE_SEGMENTS)
        if self._current_fill_path is not None:
            self._current_fill_path.extend(points)
        if self._current_line_path is not None:
            self._current_line_path.extend(points)
        self._last_point = end

    def _flush_fill(self):
        if self._current_fill_path:
            self._fill_paths.append(self._current_fill_path)
            self._current_fill_path = None
        if self._fill_color is not None:
            for path in self._fill_paths:
                if len(path) >= 3:
                    self._operations.append(DrawOperation("polygon", path, self._fill_color))
        self._fill_paths = []
        self._last_point = None

    def _flush_line(self):
        if self._current_line_path:
            self._line_paths.append(self._current_line_path)
            self._current_line_path = None
        if self._line_color is not None:
            for path in self._line_paths:
                if len(path) >= 2:
                    self._operations.append(DrawOperation("line", path, self._line_color, self._line_width))
        self._line_paths = []
        self._last_point = None

    def _transform_point(self, x: float, y: float) -> tuple[float, float]:
        tx, ty = self._matrix.multiply_point((x, y))
        return float(tx), float(ty)


def _sample_quadratic_curve(
    start: tuple[float, float],
    control: tuple[float, float],
    end: tuple[float, float],
    segments: int,
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for index in range(1, segments + 1):
        t = index / float(segments)
        omt = 1.0 - t
        x = (omt * omt * start[0]) + (2.0 * omt * t * control[0]) + (t * t * end[0])
        y = (omt * omt * start[1]) + (2.0 * omt * t * control[1]) + (t * t * end[1])
        points.append((x, y))
    return points


def _argb_to_rgba(color: int, alpha: float = 1.0) -> tuple[int, int, int, int]:
    embedded_alpha = (color >> 24) & 0xFF
    if color <= 0xFFFFFF:
        embedded_alpha = 0xFF
    alpha_component = max(0, min(255, int(round(embedded_alpha * alpha))))
    red = (color >> 16) & 0xFF
    green = (color >> 8) & 0xFF
    blue = color & 0xFF
    return red, green, blue, alpha_component


def _rasterize_operations(operations: list[DrawOperation], stage_bounds):
    point_values = [point for operation in operations for point in operation.points]
    if not point_values:
        return None

    min_x = min(stage_bounds.xmin / 20.0, min(point[0] for point in point_values))
    min_y = min(stage_bounds.ymin / 20.0, min(point[1] for point in point_values))
    max_x = max(stage_bounds.xmax / 20.0, max(point[0] for point in point_values))
    max_y = max(stage_bounds.ymax / 20.0, max(point[1] for point in point_values))

    padding = 4
    width = max(1, int(round((max_x - min_x) * SUPERSAMPLE_SCALE)) + (padding * 2))
    height = max(1, int(round((max_y - min_y) * SUPERSAMPLE_SCALE)) + (padding * 2))

    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")

    for operation in operations:
        points = [
            (
                ((point[0] - min_x) * SUPERSAMPLE_SCALE) + padding,
                ((point[1] - min_y) * SUPERSAMPLE_SCALE) + padding,
            )
            for point in operation.points
        ]
        if operation.kind == "polygon":
            draw.polygon(points, fill=operation.color)
        else:
            draw.line(
                points,
                fill=operation.color,
                width=max(1, int(round(operation.width * SUPERSAMPLE_SCALE))),
                joint="curve",
            )

    if SUPERSAMPLE_SCALE > 1:
        downsampled_width = max(1, width // SUPERSAMPLE_SCALE)
        downsampled_height = max(1, height // SUPERSAMPLE_SCALE)
        image = image.resize((downsampled_width, downsampled_height), Image.Resampling.LANCZOS)

    return image

from __future__ import annotations

import logging
import math
import re
import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, ttk

try:  # Optional so cached previews remain usable even before dependencies are refreshed.
    from PIL import Image
except Exception:  # pragma: no cover - depends on local environment
    Image = None

from .minifig_gfx_renderer import render_gfx_preview

log = logging.getLogger(__name__)

FACE_PREVIEW_BG = "#F2C94C"
FACE_PREVIEW_CACHE_DIR = "face_preview_cache"
FACE_FIELD_ORDER = ("eyebrowstyle", "eyesstyle", "mouthstyle")
FACE_PREVIEW_LAYER_OFFSETS = {
    "eyebrowstyle": (0, -18),
    "eyesstyle": (0, 0),
    "mouthstyle": (0, 18),
}


@dataclass(frozen=True)
class FaceAssetDefinition:
    field_name: str
    label: str
    cache_group: str
    relative_dirs: tuple[Path, ...]


@dataclass(frozen=True)
class FaceAssetOption:
    field_name: str
    asset_id: int
    source_path: Path
    preview_path: Path


@dataclass(frozen=True)
class FacePreviewCacheSummary:
    generated_count: int = 0
    failed_items: tuple[str, ...] = ()


FACE_ASSET_DEFINITIONS: dict[str, FaceAssetDefinition] = {
    "eyebrowstyle": FaceAssetDefinition(
        field_name="eyebrowstyle",
        label="Eyebrows",
        cache_group="eyebrows",
        relative_dirs=(
            Path("res/textures/minifig/minifigeyebrows/animated"),
            Path("textures/minifig/minifigeyebrows/animated"),
        ),
    ),
    "eyesstyle": FaceAssetDefinition(
        field_name="eyesstyle",
        label="Eyes",
        cache_group="eyes",
        relative_dirs=(
            Path("res/textures/minifig/minifigeyes/animated"),
            Path("textures/minifig/minifigeyes/animated"),
        ),
    ),
    "mouthstyle": FaceAssetDefinition(
        field_name="mouthstyle",
        label="Mouth",
        cache_group="mouths",
        relative_dirs=(
            Path("res/textures/minifig/minfigmouths/animated"),
            Path("textures/minifig/minfigmouths/animated"),
            Path("res/textures/minifig/minifigmouths/animated"),
            Path("textures/minifig/minifigmouths/animated"),
        ),
    ),
}


def get_face_preview_cache_root() -> Path:
    """Return the folder used to cache converted face preview PNGs."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / FACE_PREVIEW_CACHE_DIR
    return Path(__file__).resolve().parents[1] / FACE_PREVIEW_CACHE_DIR


def extract_asset_id(path: str | Path) -> int | None:
    """Extract the numeric face asset id from a client filename."""
    stem = Path(path).stem
    if stem.isdigit():
        return int(stem)
    matches = re.findall(r"\d+", stem)
    if not matches:
        return None
    # Face assets use names like brows_4, eyes_12, or mouths_10_g0.
    # The style id is the first numeric token; later tokens are frame/group suffixes.
    return int(matches[0])


def parse_face_id(raw_value: str | int | None) -> int | None:
    """Allow blank ids while validating that populated ids remain non-negative integers."""
    if raw_value is None:
        return None
    text = str(raw_value).strip()
    if text == "":
        return None
    if not text.isdigit():
        raise ValueError(f"'{text}' is not a valid non-negative integer id.")
    return int(text)


def resolve_face_asset_dir(client_path: Path, definition: FaceAssetDefinition) -> Path | None:
    """Accept either the client root or the nested res folder as the selected base path."""
    for relative_dir in definition.relative_dirs:
        candidate = client_path / relative_dir
        if candidate.is_dir():
            return candidate
    return None


def build_face_asset_index(client_path: Path) -> dict[str, list[FaceAssetOption]]:
    """Index face assets by field name, preferring DDS files when both DDS and GFX exist."""
    normalized_path = Path(client_path)
    cache_root = get_face_preview_cache_root()
    index: dict[str, list[FaceAssetOption]] = {}

    for field_name, definition in FACE_ASSET_DEFINITIONS.items():
        options_by_id: dict[int, FaceAssetOption] = {}
        asset_dir = resolve_face_asset_dir(normalized_path, definition)
        if asset_dir is None:
            index[field_name] = []
            continue

        for source_path in sorted(asset_dir.iterdir()):
            if not source_path.is_file():
                continue
            suffix = source_path.suffix.lower()
            if suffix not in {".dds", ".gfx"}:
                continue

            asset_id = extract_asset_id(source_path)
            if asset_id is None:
                continue

            preview_path = cache_root / definition.cache_group / f"{asset_id}.png"
            candidate = FaceAssetOption(
                field_name=field_name,
                asset_id=asset_id,
                source_path=source_path,
                preview_path=preview_path,
            )
            existing = options_by_id.get(asset_id)
            if existing is None or (existing.source_path.suffix.lower() != ".dds" and suffix == ".dds"):
                options_by_id[asset_id] = candidate

        index[field_name] = sorted(options_by_id.values(), key=lambda option: option.asset_id)

    return index


def ensure_preview_png(option: FaceAssetOption) -> Path | None:
    """Convert a DDS or GFX asset into a cached PNG on demand."""
    if option.preview_path.is_file():
        return option.preview_path
    if Image is None:
        return None

    source_suffix = option.source_path.suffix.lower()
    if source_suffix == ".gfx":
        return render_gfx_preview(option.source_path, option.preview_path)
    if source_suffix != ".dds":
        return None

    try:
        option.preview_path.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(option.source_path) as image:
            try:
                image.seek(0)
            except Exception:
                pass
            rgba_image = image.convert("RGBA")
            rgba_image.save(option.preview_path, format="PNG")
        log.info("Cached minifig face preview %s", option.preview_path)
        return option.preview_path
    except Exception:
        log.exception("Failed converting minifig face preview from %s", option.source_path)
        return None


def _get_uncached_face_options(asset_index: dict[str, list[FaceAssetOption]]) -> list[FaceAssetOption]:
    uncached: list[FaceAssetOption] = []
    for field_name in FACE_FIELD_ORDER:
        uncached.extend(
            option
            for option in asset_index.get(field_name, [])
            if not option.preview_path.is_file()
        )
    return uncached


def warm_face_preview_cache(
    parent: tk.Misc,
    asset_index: dict[str, list[FaceAssetOption]],
) -> FacePreviewCacheSummary:
    """Generate missing preview PNGs with a visible progress window on first use."""
    uncached_options = _get_uncached_face_options(asset_index)
    if not uncached_options or Image is None:
        return FacePreviewCacheSummary()

    owner = parent.winfo_toplevel()
    progress_window = tk.Toplevel(owner)
    progress_window.title("Preparing Face Previews")
    progress_window.transient(owner)
    progress_window.resizable(False, False)
    progress_window.protocol("WM_DELETE_WINDOW", lambda: None)
    progress_window.columnconfigure(0, weight=1)

    progress_frame = ttk.Frame(progress_window, padding=14)
    progress_frame.grid(row=0, column=0, sticky="nsew")
    progress_frame.columnconfigure(0, weight=1)

    ttk.Label(
        progress_frame,
        text="Generating face previews for this client folder.",
    ).grid(row=0, column=0, sticky="w")
    ttk.Label(
        progress_frame,
        text="This only happens the first time and can take a little while.",
        foreground="#92400e",
    ).grid(row=1, column=0, sticky="w", pady=(4, 10))

    progress_var = tk.StringVar(value=f"Preparing 0/{len(uncached_options)} previews...")
    ttk.Label(progress_frame, textvariable=progress_var).grid(row=2, column=0, sticky="w", pady=(0, 8))
    progress_bar = ttk.Progressbar(progress_frame, mode="determinate", maximum=len(uncached_options), length=320)
    progress_bar.grid(row=3, column=0, sticky="ew")

    progress_window.update_idletasks()
    failed_items: list[str] = []
    generated_count = 0

    try:
        for index, option in enumerate(uncached_options, start=1):
            progress_var.set(
                f"Caching {_format_field_name(option.field_name)} {option.asset_id} ({index}/{len(uncached_options)})..."
            )
            progress_bar.configure(value=index - 1)
            progress_window.update()

            preview_path = ensure_preview_png(option)
            if preview_path is None or not preview_path.is_file():
                failed_items.append(f"{_format_field_name(option.field_name)} {option.asset_id}")
            else:
                generated_count += 1

        progress_bar.configure(value=len(uncached_options))
        progress_var.set(f"Prepared {generated_count}/{len(uncached_options)} previews.")
        progress_window.update_idletasks()
    finally:
        try:
            progress_window.destroy()
        except Exception:
            pass

    return FacePreviewCacheSummary(generated_count=generated_count, failed_items=tuple(failed_items))


def _format_field_name(field_name: str) -> str:
    definition = FACE_ASSET_DEFINITIONS.get(field_name)
    return definition.label if definition is not None else field_name


class MinifigFaceEditorDialog:
    """Visual picker for the MinifigComponent face decal ids."""

    def __init__(
        self,
        parent: tk.Misc,
        client_path: Path,
        initial_values: dict[str, int | None],
        object_id: int | None = None,
        asset_index: dict[str, list[FaceAssetOption]] | None = None,
        cache_summary: FacePreviewCacheSummary | None = None,
    ) -> None:
        self._client_path = Path(client_path)
        self._object_id = object_id
        self._result: dict[str, int | None] | None = None
        self._asset_index = build_face_asset_index(self._client_path) if asset_index is None else asset_index
        self._cache_summary = FacePreviewCacheSummary() if cache_summary is None else cache_summary
        self._field_vars = {
            field_name: tk.StringVar(value="" if initial_values.get(field_name) is None else str(initial_values[field_name]))
            for field_name in FACE_FIELD_ORDER
        }
        self._tab_tiles: dict[tuple[str, int], tk.Frame] = {}
        self._base_images: dict[Path, tk.PhotoImage] = {}
        self._scaled_images: dict[tuple[Path, int, int], tk.PhotoImage] = {}
        self._canvas_images: dict[str, tk.PhotoImage | None] = {field_name: None for field_name in FACE_FIELD_ORDER}
        self._status_var = tk.StringVar(value=self._build_status_message())

        self.top = tk.Toplevel(parent)
        self.top.title("Face Editor")
        self.top.transient(parent.winfo_toplevel())
        self.top.resizable(True, True)
        self.top.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.top.columnconfigure(0, weight=1)
        self.top.rowconfigure(1, weight=1)

        self._build_dialog()
        self._refresh_all_selection_states()
        self._refresh_face_preview()

    def show(self) -> dict[str, int | None] | None:
        """Show the picker modally and return the chosen ids."""
        try:
            self.top.grab_set()
        except Exception:
            pass
        try:
            self.top.wait_window()
        except Exception:
            pass
        return self._result

    def _build_dialog(self) -> None:
        header = ttk.Frame(self.top, padding=10)
        header.grid(row=0, column=0, sticky="nsew")
        header.columnconfigure(1, weight=1)

        preview_frame = ttk.LabelFrame(header, text="Preview")
        preview_frame.grid(row=0, column=0, sticky="nw", padx=(0, 12))
        self.preview_canvas = tk.Canvas(
            preview_frame,
            width=180,
            height=140,
            background=FACE_PREVIEW_BG,
            highlightbackground="#b45309",
            highlightthickness=1,
        )
        self.preview_canvas.pack(padx=8, pady=8)
        self.preview_items = {
            field_name: self.preview_canvas.create_image(
                90 + FACE_PREVIEW_LAYER_OFFSETS.get(field_name, (0, 0))[0],
                70 + FACE_PREVIEW_LAYER_OFFSETS.get(field_name, (0, 0))[1],
            )
            for field_name in FACE_FIELD_ORDER
        }
        self.preview_hint_item = self.preview_canvas.create_text(
            90,
            126,
            text="",
            fill="#7c2d12",
            width=160,
            justify=tk.CENTER,
            font=("TkDefaultFont", 9),
        )

        controls = ttk.Frame(header)
        controls.grid(row=0, column=1, sticky="nsew")
        controls.columnconfigure(1, weight=1)

        ttk.Label(
            controls,
            text="Select a face visually or type the ids directly. Confirming will update the MinifigComponent fields.",
            wraplength=420,
            justify=tk.LEFT,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        for row_index, field_name in enumerate(FACE_FIELD_ORDER, start=1):
            ttk.Label(controls, text=f"{_format_field_name(field_name)} ID").grid(
                row=row_index,
                column=0,
                sticky="w",
                padx=(0, 8),
                pady=2,
            )
            entry = ttk.Entry(controls, textvariable=self._field_vars[field_name], width=16)
            entry.grid(row=row_index, column=1, sticky="w", pady=2)
            self._field_vars[field_name].trace_add(
                "write",
                lambda *_args, name=field_name: self._on_field_var_changed(name),
            )

        ttk.Label(
            controls,
            textvariable=self._status_var,
            wraplength=420,
            justify=tk.LEFT,
            foreground="#92400e",
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))

        notebook = ttk.Notebook(self.top)
        notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        for field_name in FACE_FIELD_ORDER:
            tab = ttk.Frame(notebook)
            tab.columnconfigure(0, weight=1)
            tab.rowconfigure(0, weight=1)
            notebook.add(tab, text=_format_field_name(field_name))
            self._build_asset_tab(tab, field_name)

        button_row = ttk.Frame(self.top, padding=(10, 0, 10, 10))
        button_row.grid(row=2, column=0, sticky="ew")
        button_row.columnconfigure(0, weight=1)
        ttk.Button(button_row, text="Cancel", command=self._on_cancel).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(button_row, text="Confirm", command=self._on_confirm).grid(row=0, column=2)

    def _build_asset_tab(self, parent: ttk.Frame, field_name: str) -> None:
        options = self._asset_index.get(field_name, [])
        if not options:
            ttk.Label(
                parent,
                text=(
                    f"No {_format_field_name(field_name).lower()} assets were found under the selected client path.\n"
                    "You can still type the id manually above."
                ),
                justify=tk.LEFT,
                padding=12,
            ).grid(row=0, column=0, sticky="nw")
            return

        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        for index, option in enumerate(options):
            row = index // 4
            column = index % 4
            tile = tk.Frame(
                inner,
                bd=1,
                relief=tk.SOLID,
                background="#fff7cc",
                cursor="hand2",
                highlightthickness=2,
                highlightbackground="#fff7cc",
                highlightcolor="#fff7cc",
            )
            tile.grid(row=row, column=column, padx=6, pady=6, sticky="nsew")
            preview = tk.Canvas(tile, width=96, height=60, background=FACE_PREVIEW_BG, highlightthickness=0)
            preview.pack(padx=6, pady=(6, 2))
            label = tk.Label(tile, text=str(option.asset_id), background="#fff7cc")
            label.pack(padx=6, pady=(0, 6))

            photo = self._load_photo(option, max_width=88, max_height=52)
            if photo is not None:
                preview.create_image(48, 30, image=photo)
            else:
                preview.create_text(
                    48,
                    30,
                    text="No\npreview",
                    fill="#7c2d12",
                    justify=tk.CENTER,
                    font=("TkDefaultFont", 8),
                )

            for widget in (tile, preview, label):
                widget.bind(
                    "<Button-1>",
                    lambda _event, name=field_name, asset_id=option.asset_id: self._select_visual_option(name, asset_id),
                    add=True,
                )

            self._tab_tiles[(field_name, option.asset_id)] = tile

    def _build_status_message(self) -> str:
        total_assets = sum(len(options) for options in self._asset_index.values())
        if total_assets == 0:
            return (
                "No matching face asset folders were found for this client path. "
                "You can still set the eyebrow, eye, and mouth ids manually."
            )
        if Image is None:
            return (
                "Visual previews will reuse cached PNGs when available. "
                "Install Pillow to generate new previews from DDS files automatically."
            )
        if self._cache_summary.failed_items:
            failed_text = ", ".join(self._cache_summary.failed_items[:4])
            if len(self._cache_summary.failed_items) > 4:
                failed_text += ", ..."
            return (
                f"Generated {self._cache_summary.generated_count} new previews. "
                f"{len(self._cache_summary.failed_items)} could not be rendered and will show No preview: {failed_text}. "
                "See the log for details."
            )
        if self._cache_summary.generated_count > 0:
            return (
                f"Generated {self._cache_summary.generated_count} new previews for this client folder. "
                "Future face edits will reuse the cache."
            )
        return "Preview PNGs are cached in the project folder so repeated face edits can reuse them."

    def _on_field_var_changed(self, field_name: str) -> None:
        self._refresh_selection_state(field_name)
        self._refresh_face_preview()

    def _select_visual_option(self, field_name: str, asset_id: int) -> None:
        self._field_vars[field_name].set(str(asset_id))

    def _refresh_all_selection_states(self) -> None:
        for field_name in FACE_FIELD_ORDER:
            self._refresh_selection_state(field_name)

    def _refresh_selection_state(self, field_name: str) -> None:
        try:
            selected_id = parse_face_id(self._field_vars[field_name].get())
        except ValueError:
            selected_id = None

        for option in self._asset_index.get(field_name, []):
            tile = self._tab_tiles.get((field_name, option.asset_id))
            if tile is None:
                continue
            if option.asset_id == selected_id:
                tile.configure(highlightbackground="#d97706", highlightcolor="#d97706", background="#fde68a")
                for child in tile.winfo_children():
                    if isinstance(child, tk.Label):
                        child.configure(background="#fde68a")
            else:
                tile.configure(highlightbackground="#fff7cc", highlightcolor="#fff7cc", background="#fff7cc")
                for child in tile.winfo_children():
                    if isinstance(child, tk.Label):
                        child.configure(background="#fff7cc")

    def _refresh_face_preview(self) -> None:
        preview_missing: list[str] = []
        for field_name in FACE_FIELD_ORDER:
            photo = None
            option = self._get_selected_option(field_name)
            if option is not None:
                photo = self._load_photo(option, max_width=164, max_height=112)
                if photo is None:
                    preview_missing.append(f"{_format_field_name(field_name)} {option.asset_id}")
            self._canvas_images[field_name] = photo
            self.preview_canvas.itemconfigure(self.preview_items[field_name], image=photo)

        hint_text = ""
        if preview_missing:
            hint_text = "Preview unavailable for: " + ", ".join(preview_missing)
        self.preview_canvas.itemconfigure(self.preview_hint_item, text=hint_text)

    def _get_selected_option(self, field_name: str) -> FaceAssetOption | None:
        try:
            selected_id = parse_face_id(self._field_vars[field_name].get())
        except ValueError:
            return None
        if selected_id is None:
            return None
        for option in self._asset_index.get(field_name, []):
            if option.asset_id == selected_id:
                return option
        return None

    def _load_photo(self, option: FaceAssetOption, max_width: int, max_height: int) -> tk.PhotoImage | None:
        preview_path = ensure_preview_png(option)
        if preview_path is None or not preview_path.is_file():
            return None

        base_image = self._base_images.get(preview_path)
        if base_image is None:
            try:
                base_image = tk.PhotoImage(file=str(preview_path))
            except Exception:
                log.exception("Failed loading cached minifig face preview %s", preview_path)
                return None
            self._base_images[preview_path] = base_image

        cache_key = (preview_path, max_width, max_height)
        cached_image = self._scaled_images.get(cache_key)
        if cached_image is not None:
            return cached_image

        width = max(base_image.width(), 1)
        height = max(base_image.height(), 1)
        scale_divisor = max(1, math.ceil(max(width / max_width, height / max_height)))
        scaled_image = base_image if scale_divisor == 1 else base_image.subsample(scale_divisor, scale_divisor)
        self._scaled_images[cache_key] = scaled_image
        return scaled_image

    def _collect_values(self) -> dict[str, int | None]:
        values: dict[str, int | None] = {}
        for field_name in FACE_FIELD_ORDER:
            try:
                values[field_name] = parse_face_id(self._field_vars[field_name].get())
            except ValueError as exc:
                raise ValueError(f"{_format_field_name(field_name)}: {exc}") from exc
        return values

    def _on_confirm(self) -> None:
        try:
            self._result = self._collect_values()
        except ValueError as exc:
            messagebox.showerror("Invalid face id", str(exc), parent=self.top)
            return

        log.info("Selected minifig face ids for object_id=%s: %s", self._object_id, self._result)
        self.top.destroy()

    def _on_cancel(self) -> None:
        self._result = None
        self.top.destroy()


def choose_minifig_face(
    parent: tk.Misc,
    client_path: Path,
    initial_values: dict[str, int | None],
    object_id: int | None = None,
) -> dict[str, int | None] | None:
    """Open the Minifig face picker and return the chosen ids when confirmed."""
    asset_index = build_face_asset_index(client_path)
    cache_summary = warm_face_preview_cache(parent, asset_index)
    dialog = MinifigFaceEditorDialog(
        parent,
        client_path,
        initial_values,
        object_id=object_id,
        asset_index=asset_index,
        cache_summary=cache_summary,
    )
    return dialog.show()

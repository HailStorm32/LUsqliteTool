from __future__ import annotations

from pathlib import Path

from gui.minifig_face_editor import FACE_PREVIEW_LAYER_OFFSETS, FaceAssetOption, build_face_asset_index, ensure_preview_png, extract_asset_id, parse_face_id
from gui.minifig_gfx_renderer import _ShapeRecorder
from gui._vendor.swf.geom import Matrix2


def test_extract_asset_id_uses_face_style_token() -> None:
    assert extract_asset_id("mf_eyes_0012.dds") == 12
    assert extract_asset_id("eyes_1_g0.dds") == 1
    assert extract_asset_id("mouths_10_g0.dds") == 10
    assert extract_asset_id("eyebrows12_variant3.gfx") == 12
    assert extract_asset_id("mouth.dds") is None


def test_parse_face_id_accepts_blank_and_non_negative_integers() -> None:
    assert parse_face_id("") is None
    assert parse_face_id("0") == 0
    assert parse_face_id(42) == 42


def test_build_face_asset_index_prefers_dds_and_supports_client_root(tmp_path: Path) -> None:
    client_root = tmp_path / "client"
    eyebrow_dir = client_root / "res" / "textures" / "minifig" / "minifigeyebrows" / "animated"
    eyes_dir = client_root / "res" / "textures" / "minifig" / "minifigeyes" / "animated"
    mouth_dir = client_root / "res" / "textures" / "minifig" / "minfigmouths" / "animated"
    eyebrow_dir.mkdir(parents=True)
    eyes_dir.mkdir(parents=True)
    mouth_dir.mkdir(parents=True)

    (eyebrow_dir / "eyebrow_7.gfx").write_text("")
    (eyebrow_dir / "eyebrow_7.dds").write_text("")
    (eyes_dir / "eyes_9_g0.dds").write_text("")
    (mouth_dir / "mouth_11.gfx").write_text("")

    index = build_face_asset_index(client_root)

    assert [option.asset_id for option in index["eyebrowstyle"]] == [7]
    assert index["eyebrowstyle"][0].source_path.suffix.lower() == ".dds"
    assert [option.asset_id for option in index["eyesstyle"]] == [9]
    assert [option.asset_id for option in index["mouthstyle"]] == [11]


def test_build_face_asset_index_supports_res_folder_input(tmp_path: Path) -> None:
    res_root = tmp_path / "client" / "res"
    eyes_dir = res_root / "textures" / "minifig" / "minifigeyes" / "animated"
    eyes_dir.mkdir(parents=True)
    (eyes_dir / "eyes_15.dds").write_text("")

    index = build_face_asset_index(res_root)

    assert [option.asset_id for option in index["eyesstyle"]] == [15]


def test_ensure_preview_png_delegates_gfx_rendering(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "brows_4.gfx"
    source_path.write_bytes(b"")
    preview_path = tmp_path / "brows_4.png"
    option = FaceAssetOption(
        field_name="eyebrowstyle",
        asset_id=4,
        source_path=source_path,
        preview_path=preview_path,
    )
    observed: dict[str, Path] = {}

    def fake_render_gfx_preview(source: Path, output: Path) -> Path:
        observed["source"] = source
        observed["output"] = output
        return output

    monkeypatch.setattr("gui.minifig_face_editor.render_gfx_preview", fake_render_gfx_preview)

    assert ensure_preview_png(option) == preview_path
    assert observed == {"source": source_path, "output": preview_path}


def test_shape_recorder_accepts_vendor_line_style_calls() -> None:
    recorder = _ShapeRecorder(Matrix2(), [])

    recorder.line_style(1.5, 0x123456, 0.5, False, 0, 0, 0, 0, 3.0)
    assert recorder._line_color == (0x12, 0x34, 0x56, 128)

    recorder.line_gradient_style(
        2.0,
        False,
        0,
        0,
        0,
        0,
        3.0,
        1,
        [0x010203, 0xAABBCC],
        [1.0, 0.5],
        [0, 255],
        None,
        0,
        0,
        0.0,
    )
    assert recorder._line_color == (0x01, 0x02, 0x03, 255)


def test_face_preview_raises_eyebrows_above_eyes() -> None:
    assert FACE_PREVIEW_LAYER_OFFSETS["eyebrowstyle"][1] < FACE_PREVIEW_LAYER_OFFSETS["eyesstyle"][1]

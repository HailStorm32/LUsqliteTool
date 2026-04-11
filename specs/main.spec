# -*- mode: python ; coding: utf-8 -*-

import ast
from pathlib import Path


project_root = Path(__file__).resolve().parent.parent
main_file = project_root / "main.py"
invalid_filename_chars = '<>:"/\\|?*'


def load_string_constant(name: str) -> str | None:
    """Read a top-level string constant from main.py without importing the Tk app."""
    module = ast.parse(main_file.read_text(encoding="utf-8"), filename=str(main_file))

    for node in module.body:
        value = None
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) == name:
            value = node.value
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if getattr(target, "id", None) == name:
                    value = node.value
                    break

        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            configured_value = value.value.strip()
            if configured_value:
                return configured_value

    return None


def build_executable_name() -> str:
    """Convert APP_TITLE into a filesystem-safe executable base name."""
    configured_title = load_string_constant("APP_TITLE")
    if not configured_title:
        return main_file.stem

    sanitized = "".join("_" if char in invalid_filename_chars else char for char in configured_title).strip()
    return sanitized or main_file.stem


configured_icon = load_string_constant("APP_ICON_PATH")
bundled_datas = []
exe_icon = None

if configured_icon:
    raw_icon_path = Path(configured_icon)
    resolved_icon_path = raw_icon_path if raw_icon_path.is_absolute() else project_root / raw_icon_path

    if resolved_icon_path.exists():
        bundle_target = "."
        if not raw_icon_path.is_absolute() and str(raw_icon_path.parent) not in {"", "."}:
            bundle_target = str(raw_icon_path.parent)

        bundled_datas.append((str(resolved_icon_path), bundle_target))
        if resolved_icon_path.suffix.lower() == ".ico":
            exe_icon = str(resolved_icon_path)


a = Analysis(
    [str(main_file)],
    pathex=[],
    binaries=[],
    datas=bundled_datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=build_executable_name(),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=exe_icon,
)

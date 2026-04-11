from __future__ import annotations

import ast
import os
import shlex
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
MAIN_FILE = PROJECT_ROOT / "main.py"
INVALID_FILENAME_CHARS = '<>:"/\\|?*'


def load_string_constant(name: str) -> str | None:
    """Read a top-level string constant from main.py without importing the Tk app."""
    module = ast.parse(MAIN_FILE.read_text(encoding="utf-8"), filename=str(MAIN_FILE))

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
        return MAIN_FILE.stem

    sanitized = "".join("_" if char in INVALID_FILENAME_CHARS else char for char in configured_title).strip()
    return sanitized or MAIN_FILE.stem


def build_command(extra_args: list[str]) -> list[str]:
    """Build a PyInstaller command that bundles the configured window icon."""
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--windowed",
        "--name",
        build_executable_name(),
    ]

    configured_icon = load_string_constant("APP_ICON_PATH")
    if configured_icon:
        raw_icon_path = Path(configured_icon)
        resolved_icon_path = raw_icon_path if raw_icon_path.is_absolute() else PROJECT_ROOT / raw_icon_path

        if resolved_icon_path.exists():
            bundle_target = "."
            if not raw_icon_path.is_absolute() and str(raw_icon_path.parent) not in {"", "."}:
                bundle_target = str(raw_icon_path.parent)

            command.extend(
                [
                    "--add-data",
                    f"{resolved_icon_path}{os.pathsep}{bundle_target}",
                ]
            )

            if resolved_icon_path.suffix.lower() == ".ico":
                command.extend(["--icon", str(resolved_icon_path)])
            else:
                print(
                    "APP_ICON_PATH is not a .ico file. The runtime asset will be bundled, "
                    "but the generated .exe icon will not be replaced.",
                    file=sys.stderr,
                )
        else:
            print(
                f"APP_ICON_PATH points to a missing file and will be skipped: {resolved_icon_path}",
                file=sys.stderr,
            )

    command.extend(extra_args)
    command.append(str(MAIN_FILE))
    return command


def main() -> None:
    command = build_command(sys.argv[1:])
    print("Running:", " ".join(shlex.quote(part) for part in command))
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


if __name__ == "__main__":
    main()

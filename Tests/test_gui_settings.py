from __future__ import annotations

from pathlib import Path

from gui.gui import get_saved_client_path, load_app_settings, normalize_directory_path, save_app_settings


def test_app_settings_round_trip(tmp_path: Path) -> None:
    settings_path = tmp_path / "app_settings.json"
    settings = {"client_path": str(tmp_path / "client")}

    assert save_app_settings(settings, settings_path=settings_path) is True
    assert load_app_settings(settings_path=settings_path) == settings


def test_get_saved_client_path_returns_existing_directory(tmp_path: Path) -> None:
    client_dir = tmp_path / "client"
    client_dir.mkdir()

    assert get_saved_client_path({"client_path": str(client_dir)}) == client_dir.resolve()


def test_get_saved_client_path_ignores_missing_directory(tmp_path: Path) -> None:
    missing_dir = tmp_path / "missing-client"

    assert get_saved_client_path({"client_path": str(missing_dir)}) is None


def test_normalize_directory_path_accepts_none() -> None:
    assert normalize_directory_path(None) is None

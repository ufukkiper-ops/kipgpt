"""Kalıcı veri dizini (Render disk, yerel proje kökü)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def get_data_dir() -> Path:
    explicit = (os.getenv("KIPGPT_DATA_DIR") or "").strip()
    if explicit:
        return Path(explicit)
    return ROOT_DIR


def ensure_data_dir() -> Path:
    path = get_data_dir()
    path.mkdir(parents=True, exist_ok=True)
    (path / "user_files").mkdir(parents=True, exist_ok=True)
    return path


def _migrate_legacy_file(name: str) -> Path:
    """Yerel kökteki dosyayı kalıcı dizine bir kez kopyala."""
    target = get_data_dir() / name
    if target.exists():
        return target
    legacy = ROOT_DIR / name
    if legacy.exists() and legacy.resolve() != target.resolve():
        try:
            shutil.copy2(legacy, target)
        except OSError:
            pass
    return target


def users_file_path() -> Path:
    return _migrate_legacy_file("users.json")


def chat_data_file_path() -> Path:
    return _migrate_legacy_file("data.json")


def user_files_root() -> Path:
    root = get_data_dir() / "user_files"
    root.mkdir(parents=True, exist_ok=True)
    legacy = ROOT_DIR / "user_files"
    if legacy.is_dir() and legacy.resolve() != root.resolve() and not any(root.iterdir()):
        try:
            shutil.copytree(legacy, root, dirs_exist_ok=True)
        except OSError:
            pass
    return root


def oauth_state_file_path() -> Path:
    explicit = (os.getenv("OAUTH_STATE_FILE") or "").strip()
    if explicit:
        return Path(explicit)
    path = get_data_dir() / "oauth_states.json"
    legacy = ROOT_DIR / "data" / "oauth_states.json"
    if not path.exists() and legacy.exists():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(legacy, path)
        except OSError:
            pass
    return path

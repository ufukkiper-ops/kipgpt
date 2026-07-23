import json
import re

from services.data_paths import chat_data_file_path, ensure_data_dir


def _data_file():
    ensure_data_dir()
    return chat_data_file_path()


def load_data():
    path = _data_file()
    if not path.exists():
        return {}

    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}


def save_data(data):
    path = _data_file()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def next_chat_id(chats):
    """Return a unique chatN id that does not collide with existing keys."""
    max_n = 0
    for key in (chats or {}):
        match = re.fullmatch(r"chat(\d+)", str(key))
        if match:
            max_n = max(max_n, int(match.group(1)))
    return f"chat{max_n + 1}"
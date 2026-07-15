import json
import os
import re

DATA_FILE = "data.json"


def load_data():
    if not os.path.exists(DATA_FILE):
        return {}

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def next_chat_id(chats):
    """Return a unique chatN id that does not collide with existing keys."""
    max_n = 0
    for key in (chats or {}):
        match = re.fullmatch(r"chat(\d+)", str(key))
        if match:
            max_n = max(max_n, int(match.group(1)))
    return f"chat{max_n + 1}"
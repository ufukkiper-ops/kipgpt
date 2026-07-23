"""Persistent per-user file library for AI-assisted mail attachments."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from services.file_service import (
    MAX_UPLOAD_SIZE,
    get_file_category,
    guess_mimetype,
    safe_filename,
)
from services.data_paths import user_files_root
from users import find_user_by_id, load_users, save_users


def _library_root() -> Path:
    return user_files_root()


def _now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _user_key(user):
    return (user.get("email") or user.get("username") or "").strip()


def _safe_user_dir(user):
    key = _user_key(user).lower() or "anon"
    safe = re.sub(r"[^a-z0-9._-]+", "_", key)[:80] or "anon"
    path = _library_root() / safe
    path.mkdir(parents=True, exist_ok=True)
    return path


def _find_user_index(users, user):
    key = _user_key(user).lower()
    for index, item in enumerate(users):
        email = (item.get("email") or "").strip().lower()
        username = (item.get("username") or "").strip().lower()
        if key and key in (email, username):
            return index
    return None


def list_files(user):
    files = list(user.get("file_library") or [])
    return sorted(files, key=lambda f: f.get("created_at") or "", reverse=True)


def get_file(user, file_id):
    for item in list_files(user):
        if item.get("id") == file_id:
            return item
    return None


def _read_stored_bytes(user, item):
    path = _safe_user_dir(user) / item.get("stored_name", "")
    if not path.is_file():
        raise FileNotFoundError("Dosya diskte bulunamadı.")
    return path.read_bytes()


def add_file(user, uploaded_file, note=""):
    if not uploaded_file or not uploaded_file.filename:
        raise ValueError("Dosya seçilmedi.")

    filename = safe_filename(uploaded_file.filename)
    data = uploaded_file.read()
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)

    if not data:
        raise ValueError("Boş dosya yüklenemez.")
    if len(data) > MAX_UPLOAD_SIZE:
        raise ValueError("Dosya boyutu 15 MB sınırını aşıyor.")

    file_id = uuid.uuid4().hex[:12]
    ext = Path(filename).suffix
    stored_name = f"{file_id}{ext}"
    dest = _safe_user_dir(user) / stored_name
    dest.write_bytes(data)

    mimetype = guess_mimetype(filename, getattr(uploaded_file, "mimetype", ""))
    item = {
        "id": file_id,
        "filename": filename,
        "stored_name": stored_name,
        "mimetype": mimetype,
        "category": get_file_category(filename, mimetype),
        "size": len(data),
        "note": (note or "").strip()[:300],
        "created_at": _now_iso(),
    }

    users = load_users()
    index = _find_user_index(users, user)
    if index is None:
        dest.unlink(missing_ok=True)
        raise ValueError("Kullanıcı bulunamadı.")

    library = list(users[index].get("file_library") or [])
    library.append(item)
    users[index]["file_library"] = library
    save_users(users)
    return item, find_user_by_id(_user_key(user))


def delete_file(user, file_id):
    users = load_users()
    index = _find_user_index(users, user)
    if index is None:
        raise ValueError("Kullanıcı bulunamadı.")

    library = list(users[index].get("file_library") or [])
    target = None
    remaining = []
    for item in library:
        if item.get("id") == file_id:
            target = item
        else:
            remaining.append(item)

    if not target:
        raise ValueError("Dosya bulunamadı.")

    path = _safe_user_dir(user) / target.get("stored_name", "")
    if path.is_file():
        path.unlink()

    users[index]["file_library"] = remaining
    save_users(users)
    return find_user_by_id(_user_key(user))


def load_attachment(user, file_id):
    item = get_file(user, file_id)
    if not item:
        raise ValueError("Kütüphane dosyası bulunamadı.")
    data = _read_stored_bytes(user, item)
    return {
        "filename": item["filename"],
        "mimetype": item.get("mimetype") or "application/octet-stream",
        "data": data,
    }


def load_attachments(user, file_ids):
    attachments = []
    for file_id in file_ids or []:
        file_id = (file_id or "").strip()
        if not file_id:
            continue
        attachments.append(load_attachment(user, file_id))
    return attachments


def _normalize_query(text):
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def resolve_attachment_queries(user, queries, limit=5):
    """Match natural-language file references to library items."""
    library = list_files(user)
    if not library or not queries:
        return []

    matched = []
    seen = set()

    for raw in queries:
        query = _normalize_query(raw)
        if not query:
            continue

        scored = []
        for item in library:
            name = _normalize_query(item.get("filename"))
            note = _normalize_query(item.get("note"))
            stem = _normalize_query(Path(item.get("filename") or "").stem)
            score = 0
            if query == name or query == stem:
                score = 100
            elif query in name or name in query:
                score = 80
            elif stem and (query in stem or stem in query):
                score = 70
            elif note and (query in note or any(tok in note for tok in query.split() if len(tok) > 2)):
                score = 50
            else:
                tokens = [t for t in re.split(r"[^\wçğıöşü]+", query) if len(t) > 2]
                hits = sum(1 for t in tokens if t in name or t in note)
                if hits:
                    score = 30 + hits * 10
            if score:
                scored.append((score, item))

        scored.sort(key=lambda pair: (-pair[0], pair[1].get("created_at") or ""), reverse=False)
        scored.sort(key=lambda pair: pair[0], reverse=True)

        for score, item in scored:
            if item["id"] in seen:
                continue
            seen.add(item["id"])
            matched.append({
                "id": item["id"],
                "filename": item["filename"],
                "mimetype": item.get("mimetype"),
                "size": item.get("size"),
                "score": score,
                "query": raw,
            })
            break

        if len(matched) >= limit:
            break

    return matched

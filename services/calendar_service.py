"""Per-user calendar events and reminders stored in users.json."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from users import find_user_by_id, load_users, save_users


def _now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _user_key(user):
    return (user.get("email") or user.get("username") or "").strip()


def _find_user_index(users, user):
    key = _user_key(user).lower()
    for index, item in enumerate(users):
        email = (item.get("email") or "").strip().lower()
        username = (item.get("username") or "").strip().lower()
        if key and key in (email, username):
            return index
    return None


def list_events(user, include_done=True):
    events = list(user.get("calendar_events") or [])
    if not include_done:
        events = [e for e in events if not e.get("done")]
    return sorted(
        events,
        key=lambda e: (e.get("start") or e.get("reminder_at") or e.get("created_at") or ""),
    )


def upcoming_reminders(user, limit=20):
    now = _now_iso()
    items = []
    for event in list_events(user, include_done=False):
        due = event.get("reminder_at") or event.get("start")
        if not due:
            continue
        items.append({**event, "due_at": due, "is_overdue": due <= now})
    items.sort(key=lambda e: e.get("due_at") or "")
    return items[:limit]


def create_event(user, payload):
    title = (payload.get("title") or "").strip()
    if not title:
        raise ValueError("Başlık gerekli.")

    event = {
        "id": uuid.uuid4().hex[:12],
        "title": title[:200],
        "description": (payload.get("description") or "").strip()[:2000],
        "start": (payload.get("start") or "").strip() or None,
        "end": (payload.get("end") or "").strip() or None,
        "reminder_at": (payload.get("reminder_at") or payload.get("start") or "").strip() or None,
        "all_day": bool(payload.get("all_day")),
        "done": False,
        "source": (payload.get("source") or "manual").strip()[:40],
        "source_mail_id": (payload.get("source_mail_id") or "").strip() or None,
        "created_at": _now_iso(),
    }

    users = load_users()
    index = _find_user_index(users, user)
    if index is None:
        raise ValueError("Kullanıcı bulunamadı.")

    events = list(users[index].get("calendar_events") or [])
    events.append(event)
    users[index]["calendar_events"] = events
    save_users(users)

    refreshed = find_user_by_id(_user_key(user))
    return event, refreshed


def update_event(user, event_id, payload):
    users = load_users()
    index = _find_user_index(users, user)
    if index is None:
        raise ValueError("Kullanıcı bulunamadı.")

    events = list(users[index].get("calendar_events") or [])
    updated = None
    for event in events:
        if event.get("id") != event_id:
            continue
        if "title" in payload and payload.get("title") is not None:
            title = str(payload.get("title") or "").strip()
            if title:
                event["title"] = title[:200]
        if "description" in payload:
            event["description"] = str(payload.get("description") or "").strip()[:2000]
        if "start" in payload:
            event["start"] = (payload.get("start") or "").strip() or None
        if "end" in payload:
            event["end"] = (payload.get("end") or "").strip() or None
        if "reminder_at" in payload:
            event["reminder_at"] = (payload.get("reminder_at") or "").strip() or None
        if "all_day" in payload:
            event["all_day"] = bool(payload.get("all_day"))
        if "done" in payload:
            event["done"] = bool(payload.get("done"))
        updated = event
        break

    if not updated:
        raise ValueError("Etkinlik bulunamadı.")

    users[index]["calendar_events"] = events
    save_users(users)
    return updated, find_user_by_id(_user_key(user))


def delete_event(user, event_id):
    users = load_users()
    index = _find_user_index(users, user)
    if index is None:
        raise ValueError("Kullanıcı bulunamadı.")

    events = list(users[index].get("calendar_events") or [])
    new_events = [e for e in events if e.get("id") != event_id]
    if len(new_events) == len(events):
        raise ValueError("Etkinlik bulunamadı.")

    users[index]["calendar_events"] = new_events
    save_users(users)
    return find_user_by_id(_user_key(user))


def create_events_from_actions(user, actions, source_mail_id=None):
    """Create reminder events from AI-suggested action items."""
    created = []
    for action in actions or []:
        title = ""
        reminder_at = None
        if isinstance(action, str):
            title = action.strip()
        elif isinstance(action, dict):
            title = (action.get("title") or action.get("text") or "").strip()
            reminder_at = (action.get("when") or action.get("reminder_at") or "").strip() or None
        if not title:
            continue
        event, user = create_event(
            user,
            {
                "title": title[:200],
                "reminder_at": reminder_at,
                "start": reminder_at,
                "source": "mail_ai",
                "source_mail_id": source_mail_id,
                "description": "Mail özetinden oluşturulan hatırlatıcı",
            },
        )
        created.append(event)
    return created, user

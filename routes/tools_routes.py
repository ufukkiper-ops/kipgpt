"""Calendar, reminders, file library, and mail AI summary/enrichment routes."""

from flask import Blueprint, jsonify, request, send_file, session
from io import BytesIO

from services.calendar_service import (
    create_event,
    create_events_from_actions,
    delete_event,
    list_events,
    upcoming_reminders,
    update_event,
)
from services.file_library_service import (
    add_file,
    delete_file,
    get_file,
    list_files,
    load_attachment,
)
from services.mail_accounts import resolve_active_mail_config
from services.mail_enrich_service import summarize_mail
from services.mail_ui import load_single_mail
from users import find_user_by_id

tools_bp = Blueprint("tools", __name__)


def _require_user():
    user = find_user_by_id(session.get("user"))
    if not user:
        return None
    return user


@tools_bp.route("/api/calendar/events", methods=["GET"])
def calendar_list():
    user = _require_user()
    if not user:
        return jsonify({"error": "Giriş gerekli."}), 401
    include_done = (request.args.get("include_done") or "1") != "0"
    return jsonify({
        "events": list_events(user, include_done=include_done),
        "reminders": upcoming_reminders(user),
    })


@tools_bp.route("/api/calendar/events", methods=["POST"])
def calendar_create():
    user = _require_user()
    if not user:
        return jsonify({"error": "Giriş gerekli."}), 401
    data = request.get_json(silent=True) or {}
    try:
        event, _ = create_event(user, data)
        return jsonify({"event": event})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tools_bp.route("/api/calendar/events/<event_id>", methods=["PATCH"])
def calendar_update(event_id):
    user = _require_user()
    if not user:
        return jsonify({"error": "Giriş gerekli."}), 401
    data = request.get_json(silent=True) or {}
    try:
        event, _ = update_event(user, event_id, data)
        return jsonify({"event": event})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tools_bp.route("/api/calendar/events/<event_id>", methods=["DELETE"])
def calendar_delete(event_id):
    user = _require_user()
    if not user:
        return jsonify({"error": "Giriş gerekli."}), 401
    try:
        delete_event(user, event_id)
        return jsonify({"ok": True})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tools_bp.route("/api/files", methods=["GET"])
def files_list():
    user = _require_user()
    if not user:
        return jsonify({"error": "Giriş gerekli."}), 401
    return jsonify({"files": list_files(user)})


@tools_bp.route("/api/files", methods=["POST"])
def files_upload():
    user = _require_user()
    if not user:
        return jsonify({"error": "Giriş gerekli."}), 401
    uploaded = request.files.get("file")
    note = (request.form.get("note") or "").strip()
    try:
        item, _ = add_file(user, uploaded, note=note)
        return jsonify({"file": item})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tools_bp.route("/api/files/<file_id>", methods=["DELETE"])
def files_delete(file_id):
    user = _require_user()
    if not user:
        return jsonify({"error": "Giriş gerekli."}), 401
    try:
        delete_file(user, file_id)
        return jsonify({"ok": True})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tools_bp.route("/api/files/<file_id>/download", methods=["GET"])
def files_download(file_id):
    user = _require_user()
    if not user:
        return jsonify({"error": "Giriş gerekli."}), 401
    try:
        if not get_file(user, file_id):
            return jsonify({"error": "Dosya bulunamadı."}), 404
        attachment = load_attachment(user, file_id)
        return send_file(
            BytesIO(attachment["data"]),
            mimetype=attachment.get("mimetype") or "application/octet-stream",
            as_attachment=True,
            download_name=attachment["filename"],
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 404


@tools_bp.route("/mail/ai-summary", methods=["POST"])
def mail_ai_summary():
    user = _require_user()
    if not user:
        return jsonify({"error": "Giriş gerekli."}), 401

    data = request.get_json(silent=True) or {}
    sender = (data.get("sender") or "").strip()
    subject = (data.get("subject") or "").strip()
    content = (data.get("content") or "").strip()
    mail_id = (data.get("mail_id") or "").strip()
    create_reminders = bool(data.get("create_reminders"))

    if not content and mail_id:
        mail_config, _ = resolve_active_mail_config(user, session, data.get("account"))
        folder = (data.get("folder") or "inbox").strip()
        if mail_config:
            try:
                mail = load_single_mail(folder, mail_config, mail_id)
                sender = sender or mail.get("sender", "")
                subject = subject or mail.get("subject", "")
                content = mail.get("content") or mail.get("body") or ""
            except Exception:
                pass

    if not content:
        return jsonify({"error": "Özetlenecek mail içeriği yok."}), 400

    try:
        summary = summarize_mail(sender, subject, content)
        created = []
        if create_reminders:
            actions = list(summary.get("reminders") or [])
            for item in summary.get("action_items") or []:
                actions.append({"title": item})
            created, _ = create_events_from_actions(user, actions, source_mail_id=mail_id)
        return jsonify({
            "summary": summary,
            "reminders_created": created,
        })
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        return jsonify({"error": f"Özet oluşturulamadı: {e}"}), 500

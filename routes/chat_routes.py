from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for



from services.chat_service import (

    analyze_uploaded_file,

    generate_chat_response,

    generate_chat_title,

    get_client,

)

from storage import load_data, save_data

from html_helpers import render_chat_list, render_messages



chat_bp = Blueprint("chat", __name__)





def _require_login():

    if "user" not in session:

        return redirect(url_for("auth.login"))

    return None





def _user_data(username):

    data = load_data()

    if username not in data or not isinstance(data[username], dict):

        data[username] = {

            "active_chat": "chat1",

            "chats": {"chat1": []},

            "chat_titles": {},

        }

    return data





def _chat_title(chat_titles, chat_id):

    return chat_titles.get(chat_id, "Yeni Sohbet")





@chat_bp.route("/new_chat")

def new_chat():

    redirect_response = _require_login()

    if redirect_response:

        return redirect_response



    username = session["user"]

    data = _user_data(username)

    chats = data[username].setdefault("chats", {"chat1": []})

    new_id = f"chat{len(chats) + 1}"

    chats[new_id] = []

    data[username]["active_chat"] = new_id

    save_data(data)

    return redirect(url_for("chat.index"))





@chat_bp.route("/switch/<chat_id>")

def switch_chat(chat_id):

    redirect_response = _require_login()

    if redirect_response:

        return redirect_response



    username = session["user"]

    data = load_data()

    if (

        username in data

        and "chats" in data[username]

        and chat_id in data[username]["chats"]

    ):

        data[username]["active_chat"] = chat_id

        save_data(data)



    return redirect(url_for("chat.index"))





@chat_bp.route("/clear_chat", methods=["POST"])

def clear_chat():

    redirect_response = _require_login()

    if redirect_response:

        return redirect_response



    username = session["user"]

    data = load_data()

    if username in data:

        active_chat = data[username].get("active_chat", "chat1")

        if active_chat in data[username]["chats"]:

            data[username]["chats"][active_chat] = []

            save_data(data)



    return redirect(url_for("chat.index"))





@chat_bp.route("/", methods=["GET", "POST"])

def index():

    redirect_response = _require_login()

    if redirect_response:

        return redirect_response



    username = session["user"]

    data = _user_data(username)

    active_chat = data[username].get("active_chat", "chat1")

    chats = data[username].setdefault("chats", {"chat1": []})

    chat_titles = data[username].setdefault("chat_titles", {})

    gecmis = chats.setdefault(active_chat, [])



    if request.method == "POST":

        action = request.form.get("action", "text")

        client = get_client()



        if client is None:

            return jsonify({

                "status": "error",

                "error": "Sunucuda OPENAI_API_KEY ayarlı değil.",

            }), 400



        if action == "text":

            soru = request.form.get("soru", "").strip()

            if soru:

                gecmis.append({"role": "user", "content": soru})

                try:

                    cevap = generate_chat_response([

                        {"role": m["role"], "content": m["content"]}

                        for m in gecmis

                    ])

                    if active_chat not in chat_titles:

                        try:

                            chat_titles[active_chat] = generate_chat_title(soru)

                        except Exception:

                            chat_titles[active_chat] = soru[:30]

                except Exception as e:

                    cevap = f"AI hatası: {e}"



                gecmis.append({"role": "assistant", "content": cevap})

                data[username]["chats"][active_chat] = gecmis

                data[username]["chat_titles"] = chat_titles

                save_data(data)



                return jsonify({

                    "status": "success",

                    "answer": cevap,

                    "chat_title": _chat_title(chat_titles, active_chat),

                    "chat_id": active_chat,

                })



        elif action in ("image", "file"):

            uploaded_file = request.files.get("image") or request.files.get("file")

            if not uploaded_file or uploaded_file.filename == "":

                return jsonify({"status": "error", "error": "Dosya seçilmedi."})



            prompt = request.form.get("image_prompt", "").strip() or "Bu dosyayı detaylı analiz et ve Türkçe yorumla."



            try:

                cevap, file_meta = analyze_uploaded_file(uploaded_file, prompt)

                user_text = request.form.get("soru", "").strip()

                content = user_text or f"[DOSYA] {file_meta['name']}"



                user_message = {

                    "role": "user",

                    "content": content,

                    "file": file_meta,

                }

                if file_meta.get("preview"):

                    user_message["image"] = file_meta["preview"]



                gecmis.append(user_message)

                gecmis.append({"role": "assistant", "content": cevap})



                if active_chat not in chat_titles:

                    chat_titles[active_chat] = file_meta["name"][:30]



                data[username]["chat_titles"] = chat_titles

                data[username]["chats"][active_chat] = gecmis

                save_data(data)



                return jsonify({

                    "status": "success",

                    "answer": cevap,

                    "chat_title": _chat_title(chat_titles, active_chat),

                    "chat_id": active_chat,

                    "file": file_meta,

                })



            except Exception as e:

                return jsonify({"status": "error", "error": str(e)})



    chat_list_html = render_chat_list(chats, chat_titles, active_chat)

    messages_html = render_messages(gecmis)

    active_title = _chat_title(chat_titles, active_chat)



    return render_template(

        "chat.html",

        username=username,

        active_chat=active_chat,

        active_title=active_title,

        chat_list_html=chat_list_html,

        messages_html=messages_html,

        title="KipGPT",

    )



from flask import Flask, request, render_template_string, redirect, url_for
from openai import OpenAI

app = Flask(__name__)
client = OpenAI()

gecmis = []

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Asistan</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial;
            background: #0f172a;
            margin: 0;
        }

        .chat-box {
            max-width: 600px;
            margin: auto;
            background: #1e293b;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }

        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 15px;
        }

        .user {
            text-align: right;
            color: #38bdf8;
            margin: 10px 0;
        }

        .bot {
            text-align: left;
            color: #22c55e;
            margin: 10px 0;
        }

        form {
            display: flex;
            padding: 10px;
            background: #020617;
        }

        input {
            flex: 1;
            padding: 10px;
            border: none;
            border-radius: 5px;
        }

        button {
            margin-left: 10px;
            padding: 10px;
            border: none;
            background: #38bdf8;
            color: black;
            border-radius: 5px;
        }

        .top {
            padding: 10px;
            background: #020617;
            text-align: center;
            color: white;
        }

        .clear-btn {
            background: red;
            color: white;
        }
    </style>
</head>

<body>

<div class="chat-box">

    <div class="top">
        AI Asistan
    </div>

    <div class="messages">
        {% for mesaj in gecmis %}
            {% if mesaj.role == 'user' %}
                <p class="user">Sen: {{ mesaj.content }}</p>
            {% else %}
                <p class="bot">AI: {{ mesaj.content }}</p>
            {% endif %}
        {% endfor %}
    </div>

    <form method="post">
        <input type="text" name="soru" placeholder="Mesaj yaz..." autofocus>
        <button type="submit">Gönder</button>
    </form>

    <form action="/temizle" method="post">
        <button class="clear-btn">Temizle</button>
    </form>

</div>

</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    global gecmis

    if request.method == "POST":
        soru = request.form["soru"]

        if soru.strip() != "":
            gecmis.append({"role": "user", "content": soru})

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=gecmis
            )

            cevap = response.choices[0].message.content
            gecmis.append({"role": "assistant", "content": cevap})

    return render_template_string(HTML, gecmis=gecmis)

@app.route("/temizle", methods=["POST"])
def temizle():
    global gecmis
    gecmis = []
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)




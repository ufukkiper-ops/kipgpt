from flask import Blueprint
import os

chat_bp = Blueprint("chat", __name__)

@chat_bp.route("/test")
def test():
    return {
        "cwd": os.getcwd(),
        "files": os.listdir("."),
        "static_exists": os.path.exists("static"),
        "static_files": os.listdir("static") if os.path.exists("static") else []
    }
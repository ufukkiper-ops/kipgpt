"""KipGPT masaüstü uygulaması.

Yerel Flask sunucusunu başlatır ve native pencerede açar (pywebview).
Uzaktan sunucu için: KIPGPT_SERVER_URL=https://...
"""

from __future__ import annotations

import os
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path


def _project_root() -> Path:
    if getattr(sys, "frozen", False):
        # PyInstaller: exe yanındaki klasör (veya _MEIPASS içi)
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            bundled = Path(meipass)
            if (bundled / "app.py").exists() or (bundled / "templates").exists():
                return bundled
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


ROOT = _project_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.chdir(ROOT)

# Masaüstü modu: üretim benzeri, reloader yok
os.environ.setdefault("KIPGPT_DESKTOP", "1")
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

WINDOW_TITLE = "KipGPT"


def _load_env() -> None:
    env_path = ROOT / ".env"
    # Exe yanındaki .env (kullanıcı yapılandırması)
    if getattr(sys, "frozen", False):
        beside = Path(sys.executable).resolve().parent / ".env"
        if beside.exists():
            env_path = beside
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path)
    except Exception:
        pass


def _settings() -> dict:
    port = int(os.environ.get("KIPGPT_DESKTOP_PORT") or os.environ.get("PORT") or "5001")
    host = "127.0.0.1"
    start = (os.environ.get("KIPGPT_DESKTOP_START") or "/login").strip() or "/login"
    return {
        "host": host,
        "port": port,
        "local_base": f"http://{host}:{port}",
        "start_path": start,
        "width": int(os.environ.get("KIPGPT_DESKTOP_WIDTH") or "1280"),
        "height": int(os.environ.get("KIPGPT_DESKTOP_HEIGHT") or "860"),
    }


def _wait_ready(base_url: str, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    health = base_url.rstrip("/") + "/health"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(health, timeout=1.5) as resp:
                if 200 <= getattr(resp, "status", 200) < 500:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.25)
    return False


def _run_flask(host: str, port: int) -> None:
    from app import app

    app.run(
        host=host,
        port=port,
        debug=False,
        use_reloader=False,
        threaded=True,
    )


def _default_remote_server() -> str:
    """Sunucu PC tünel adresi (geliştirme PC / diğer istemciler)."""
    for path in (
        ROOT / "desktop" / "default_server_url.txt",
        ROOT / "tunnel" / "current_url.txt",
        Path(sys.executable).resolve().parent / "default_server_url.txt",
    ):
        try:
            if path.is_file():
                url = path.read_text(encoding="utf-8").strip().splitlines()[0].strip()
                if url.startswith("http://") or url.startswith("https://"):
                    return url.rstrip("/")
        except OSError:
            continue
    env_public = (os.environ.get("PUBLIC_BASE_URL") or "").strip().rstrip("/")
    if env_public.startswith("http"):
        return env_public
    return ""


def _resolve_target_url(settings: dict) -> tuple[str, bool]:
    """(url, starts_local_server).

    Varsayılan: uzak sunucu (bu evdeki sunucu PC / tünel).
    Yerel Flask ancak KIPGPT_USE_LOCAL=1 veya KIPGPT_SERVER_URL=local.
    """
    use_local = (os.environ.get("KIPGPT_USE_LOCAL") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    remote = (os.environ.get("KIPGPT_SERVER_URL") or "").strip().rstrip("/")
    if remote.lower() in {"local", "localhost", "self"}:
        use_local = True
        remote = ""

    if use_local:
        return settings["local_base"] + settings["start_path"], True

    if not remote:
        remote = _default_remote_server()

    if remote:
        return remote + settings["start_path"], False

    # Dosya yoksa eski davranış: yerel sunucu
    return settings["local_base"] + settings["start_path"], True


def _icon_path() -> str | None:
    candidates = [
        ROOT / "static" / "img" / "kipgpt-app.ico",
        ROOT / "desktop" / "kipgpt.ico",
        ROOT / "static" / "img" / "kipgpt-icon.png",
        ROOT / "static" / "icon.png",
        Path(sys.executable).resolve().parent / "kipgpt.ico",
        Path(sys.executable).resolve().parent / "kipgpt-icon.png",
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    return None


def main() -> int:
    _load_env()
    settings = _settings()
    target_url, start_local = _resolve_target_url(settings)

    if start_local:
        thread = threading.Thread(
            target=_run_flask,
            kwargs={"host": settings["host"], "port": settings["port"]},
            name="kipgpt-flask",
            daemon=True,
        )
        thread.start()
        if not _wait_ready(settings["local_base"]):
            print(
                f"KipGPT sunucusu {settings['local_base']} üzerinde başlamadı. "
                "Port meşgul olabilir veya bağımlılıklar eksik.",
                file=sys.stderr,
            )
            return 1

    try:
        import webview
    except ImportError:
        print(
            "pywebview yüklü değil. Kurulum:\n"
            "  pip install -r desktop/requirements.txt",
            file=sys.stderr,
        )
        return 1

    icon = _icon_path()
    window_kwargs = {
        "title": WINDOW_TITLE,
        "url": target_url,
        "width": settings["width"],
        "height": settings["height"],
        "min_size": (900, 600),
        "confirm_close": False,
    }
    if icon:
        try:
            webview.create_window(**window_kwargs, icon=icon)
        except TypeError:
            webview.create_window(**window_kwargs)
    else:
        webview.create_window(**window_kwargs)

    gui = (os.environ.get("KIPGPT_WEBVIEW_GUI") or "").strip() or None
    webview.start(gui=gui)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — Windows masaüstü KipGPT.exe."""

from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent.parent

block_cipher = None

datas = [
    (str(ROOT / "templates"), "templates"),
    (str(ROOT / "static"), "static"),
    (str(ROOT / ".env.example"), "."),
]

hiddenimports = [
    "dotenv",
    "flask",
    "jinja2",
    "werkzeug",
    "cryptography",
    "openai",
    "httpx",
    "google.oauth2",
    "google.auth",
    "google_auth_oauthlib",
    "googleapiclient",
    "webview",
    "routes.auth_routes",
    "routes.chat_routes",
    "routes.mail_page",
    "routes.mail_oauth",
    "routes.mobile_api",
    "routes.tools_routes",
    "services.oauth_mail",
    "services.google_auth",
    "services.gmail_api",
    "services.microsoft_auth",
    "services.yahoo_auth",
    "services.security",
    "services.env_setup",
    "mail",
    "users",
    "storage",
    "html_helpers",
]

a = Analysis(
    [str(ROOT / "desktop" / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="KipGPT",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "static" / "img" / "kipgpt-icon.png")
    if (ROOT / "static" / "img" / "kipgpt-icon.png").exists()
    else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="KipGPT",
)

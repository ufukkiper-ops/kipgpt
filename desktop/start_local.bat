@echo off
cd /d "%~dp0\.."
setlocal

REM Sadece gelistirme: bu makinede Flask acar (sunucu PC degilse)
set KIPGPT_USE_LOCAL=1

if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  call .venv\Scripts\activate.bat
  pip install -r requirements.txt
  pip install -r desktop\requirements.txt
) else (
  call .venv\Scripts\activate.bat
)

echo KipGPT masaustu - YEREL sunucu modu
python desktop\main.py
if errorlevel 1 pause
endlocal

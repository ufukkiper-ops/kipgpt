@echo off
cd /d "%~dp0\.."
setlocal

if not exist ".venv\Scripts\python.exe" (
  echo Sanal ortam yok. Olusturuluyor...
  py -3 -m venv .venv
  call .venv\Scripts\activate.bat
  pip install -r requirements.txt
  pip install -r desktop\requirements.txt
) else (
  call .venv\Scripts\activate.bat
)

if not exist ".env" (
  if exist ".env.example" copy ".env.example" ".env" >nul
  echo .env olusturuldu — FLASK_SECRET_KEY ve OPENAI_API_KEY doldurun.
)

echo KipGPT masaustu baslatiliyor...
python desktop\main.py
if errorlevel 1 pause
endlocal

@echo off
cd /d "%~dp0\.."
setlocal

REM Masaustu = ince istemci. Sunucu bu (ev) PC'de start_public.bat ile calisir.
REM Adres: desktop\default_server_url.txt

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
)

if exist "desktop\default_server_url.txt" (
  set /p _URL=<desktop\default_server_url.txt
  echo KipGPT masaustu - uzak sunucu: %_URL%
) else (
  echo UYARI: desktop\default_server_url.txt yok. Yerel sunucu denenir.
)

echo.
python desktop\main.py
if errorlevel 1 pause
endlocal

@echo off
cd /d "%~dp0"
setlocal EnableDelayedExpansion

set "LAN_IP="
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
  set "CAND=%%a"
  set "CAND=!CAND: =!"
  if not "!CAND!"=="127.0.0.1" if "!LAN_IP!"=="" set "LAN_IP=!CAND!"
)

echo ========================================
echo   KipGPT
echo   Bu PC:  http://127.0.0.1:5001/mail
if not "%LAN_IP%"=="" (
  echo   Telefon: http://%LAN_IP%:5001/mail
  echo   API:     http://%LAN_IP%:5001/api/v1/
) else (
  echo   Telefon: Wi-Fi IP bulunamadi - ipconfig bakin
)
echo ========================================
echo.
echo Telefondan acmiyorsa: ayni Wi-Fi, Windows Guvenlik Duvari,
echo veya kurumsal Wi-Fi cihazlar arasi engeli olabilir.
echo Bu pencereyi kapatmayin.
echo Veriler bu klasorde kalir: users.json, data.json, user_files\
echo.

set "PUBLIC_BASE_URL=http://%LAN_IP%:5001"
if "%LAN_IP%"=="" set "PUBLIC_BASE_URL=http://127.0.0.1:5001"

set "PY=%~dp0.venv\Scripts\python.exe"
if exist "%PY%" (
  "%PY%" app.py
) else (
  py -3 app.py
)
pause

@echo off
cd /d "%~dp0"
echo ========================================
echo   Kip Asistan - Gmail Arayuzu
echo   Adres: http://127.0.0.1:5001/mail
echo ========================================
echo.
echo Eski sunucu 10000 portunda calisiyorsa KAPATIN!
echo Bu pencereyi kapatmayin.
echo.
py -3 app.py
pause

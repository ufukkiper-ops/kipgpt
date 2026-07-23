@echo off
cd /d "%~dp0"
setlocal EnableDelayedExpansion

echo ========================================
echo   KipGPT  -  PC sunucu + dis erisim
echo ========================================
echo.
echo Veriler bu PC'de kalir.
echo Disaridan erisim: Cloudflare Tunnel
echo Bu pencereyi KAPATMAYIN.
echo.

set "CF=cloudflared"
if exist "%ProgramFiles(x86)%\cloudflared\cloudflared.exe" set "CF=%ProgramFiles(x86)%\cloudflared\cloudflared.exe"
if exist "%ProgramFiles%\cloudflared\cloudflared.exe" set "CF=%ProgramFiles%\cloudflared\cloudflared.exe"

where cloudflared >nul 2>&1
if errorlevel 1 (
  if not exist "%CF%" (
    echo HATA: cloudflared bulunamadi.
    echo Kurulum: winget install Cloudflare.cloudflared
    pause
    exit /b 1
  )
)

REM Yerel sunucuyu ayri pencerede baslat
if exist "%~dp0.venv\Scripts\python.exe" (
  start "KipGPT Server" "%~dp0.venv\Scripts\python.exe" "%~dp0app.py"
) else (
  start "KipGPT Server" py -3 "%~dp0app.py"
)

timeout /t 3 /nobreak >nul

if exist "%~dp0tunnel\config.yml" (
  echo Sabit tunnel kullaniliyor: tunnel\config.yml
  echo.
  echo Telefonda / Store uygulamasi sunucu adresi:
  echo   https://SENIN-ALAN-ADIN/api/v1/
  echo.
  "%CF%" tunnel --config "%~dp0tunnel\config.yml" run
) else (
  echo Gecici public URL aciliyor ^(her acilista degisebilir^).
  echo Sabit adres icin: tunnel\SETUP.txt
  echo.
  echo Asagida https://....trycloudflare.com satiri cikacak.
  echo Uygulamada kaydet:  https://XXXX.trycloudflare.com/api/v1/
  echo.
  "%CF%" tunnel --url http://127.0.0.1:5001
)

pause

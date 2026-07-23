@echo off
cd /d "%~dp0"
setlocal EnableDelayedExpansion

echo ========================================
echo   KipGPT - Sunucu guncelle
echo   (git pull + yeniden baslat)
echo ========================================
echo.

set "GIT="
if exist "%ProgramFiles%\Git\cmd\git.exe" set "GIT=%ProgramFiles%\Git\cmd\git.exe"
if exist "%ProgramFiles(x86)%\Git\cmd\git.exe" set "GIT=%ProgramFiles(x86)%\Git\cmd\git.exe"
if "%GIT%"=="" (
  where git >nul 2>&1 && set "GIT=git"
)
if "%GIT%"=="" (
  echo HATA: Git yok. winget install Git.Git
  pause
  exit /b 1
)

if not exist "%~dp0.git" (
  echo HATA: Bu klasor henuz git deposu degil.
  echo Once:  ilk-kurulum-git.bat
  pause
  exit /b 1
)

echo [1/4] Degisiklikler cekiliyor...
"%GIT%" pull
if errorlevel 1 (
  echo.
  echo git pull basarisiz. Internet / remote URL / cakisma kontrol et.
  pause
  exit /b 1
)

echo.
echo [2/4] Bagimliliklar...
if exist "%~dp0.venv\Scripts\pip.exe" (
  "%~dp0.venv\Scripts\pip.exe" install -r requirements.txt -q
) else (
  echo .venv yok - atlandi. Gerekiyorsa: py -3 -m venv .venv ^&^& pip install -r requirements.txt
)

echo.
echo [3/4] Eski sunucu / tunnel kapatiliyor...
taskkill /FI "WINDOWTITLE eq KipGPT Server*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq KipGPT Public*" /F >nul 2>&1
taskkill /IM cloudflared.exe /F >nul 2>&1
timeout /t 2 /nobreak >nul

echo.
echo [4/4] start_public.bat baslatiliyor...
start "KipGPT Public" cmd /c "%~dp0start_public.bat"

echo.
echo Tamam. Veriler (users.json vb.) yerinde kaldi.
echo Tunnel URL degistiyse telefonda / APK'da guncelle.
pause

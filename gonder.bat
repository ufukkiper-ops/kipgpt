@echo off
cd /d "%~dp0"
setlocal

echo ========================================
echo   KipGPT - Gelistirici PC: GitHub'a gonder
echo ========================================
echo.

set "GIT="
if exist "%ProgramFiles%\Git\cmd\git.exe" set "GIT=%ProgramFiles%\Git\cmd\git.exe"
if exist "%ProgramFiles(x86)%\Git\cmd\git.exe" set "GIT=%ProgramFiles(x86)%\Git\cmd\git.exe"
if "%GIT%"=="" where git >nul 2>&1 && set "GIT=git"
if "%GIT%"=="" (
  echo HATA: Git yok. winget install Git.Git
  pause
  exit /b 1
)

"%GIT%" status
echo.
set /p MSG=Commit mesaji (bos = "guncelleme"): 
if "%MSG%"=="" set "MSG=guncelleme"

"%GIT%" add -A
"%GIT%" status
echo.
echo .env / users.json / data.json git'e EKLENMEMELI (.gitignore).
echo.
"%GIT%" commit -m "%MSG%"
if errorlevel 1 (
  echo Commit yok veya hata ^(degisiklik yok olabilir^).
) else (
  "%GIT%" push
  if errorlevel 1 (
    echo push basarisiz. Remote var mi?  git remote -v
    pause
    exit /b 1
  )
  echo.
  echo Gonderildi. Sunucu PC'de guncelle.bat calistir.
)

pause

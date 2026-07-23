@echo off
cd /d "%~dp0"
setlocal EnableDelayedExpansion

echo ========================================
echo   KipGPT - Git ilk kurulum (bu PC)
echo ========================================
echo.

set "GIT="
if exist "%ProgramFiles%\Git\cmd\git.exe" set "GIT=%ProgramFiles%\Git\cmd\git.exe"
if exist "%ProgramFiles(x86)%\Git\cmd\git.exe" set "GIT=%ProgramFiles(x86)%\Git\cmd\git.exe"
if "%GIT%"=="" where git >nul 2>&1 && set "GIT=git"
if "%GIT%"=="" (
  echo HATA: Git yok. Kurulum bitince bu dosyayi tekrar calistir.
  echo   winget install Git.Git
  pause
  exit /b 1
)

if exist "%~dp0.git" (
  echo Zaten git deposu var.
  "%GIT%" remote -v
  echo.
  set /p REMOTE=Yeni remote URL (bos = atla): 
  if not "!REMOTE!"=="" (
    "%GIT%" remote remove origin 2>nul
    "%GIT%" remote add origin !REMOTE!
    "%GIT%" push -u origin main
  )
  pause
  exit /b 0
)

"%GIT%" init
"%GIT%" branch -M main
"%GIT%" add -A
"%GIT%" commit -m "Ilk commit: KipGPT sunucu + gelistirme akisi"

echo.
echo Sonraki adim - GitHub'da bos repo olustur:
echo   https://github.com/new
echo   Isim ornek: kipgpt
echo   README EKLEME.
echo.
set /p REMOTE=Repo HTTPS URL yapistir (orn. https://github.com/KULLANICI/kipgpt.git): 
if "!REMOTE!"=="" (
  echo URL girilmedi. Sonra: git remote add origin URL ^&^& git push -u origin main
  pause
  exit /b 0
)

"%GIT%" remote add origin "!REMOTE!"
"%GIT%" push -u origin main
if errorlevel 1 (
  echo.
  echo Push basarisiz. GitHub girisi gerekebilir:
  echo   git push -u origin main
)

echo.
echo Tamam. Gelistirici PC: git clone AYNI_URL
echo Sunucu PC guncelleme: guncelle.bat
pause

@echo off
cd /d "%~dp0\.."
setlocal

call .venv\Scripts\activate.bat 2>nul
if errorlevel 1 (
  py -3 -m venv .venv
  call .venv\Scripts\activate.bat
  pip install -r requirements.txt
  pip install -r desktop\requirements.txt
)

pip install -r desktop\requirements.txt

echo PyInstaller ile KipGPT.exe derleniyor...
pyinstaller --noconfirm --clean desktop\kipgpt.spec

echo.
echo Cikti: dist\KipGPT\KipGPT.exe
echo .env dosyasini dist\KipGPT\ yanina kopyalayin.
echo.
pause
endlocal

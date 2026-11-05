@echo off
rem Builds "German Text to Speech.exe" in this folder. Needs: pip install -r requirements-dev.txt
cd /d "%~dp0"
".venv\Scripts\pyinstaller.exe" --noconfirm --onefile --windowed ^
  --name "German Text to Speech" --icon "assets\icon.ico" ^
  --add-data "assets\icon.ico;assets" --add-data "assets\icon.png;assets" ^
  --collect-all customtkinter text_to_audio.py
if errorlevel 1 exit /b 1
copy /y "dist\German Text to Speech.exe" . >nul
echo Done: German Text to Speech.exe

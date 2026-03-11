@echo off
echo ==========================================
echo      RadioMix - Build Executable
echo ==========================================

echo Installing Build Dependencies...
pip install pyinstaller
pip install -r requirements.txt

echo.
echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del /q *.spec

echo.
echo Building EXE...
pyinstaller --noconsole --onefile --name "RadioMix" radio_mix.py --clean

echo.
echo Build Complete! Executable is in the 'dist' folder.
pause
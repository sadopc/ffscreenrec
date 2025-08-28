@echo off
echo Building FFScreenRec...
echo.

REM Activate virtual environment if exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
echo.

REM Run tests
echo Running tests...
python -m pytest tests/ -v
if errorlevel 1 (
    echo Tests failed! Fix issues before building.
    pause
    exit /b 1
)
echo.

REM Clean previous builds
echo Cleaning previous builds...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
echo.

REM Build executable
echo Building executable...
pyinstaller ffscreenrec.spec --clean
echo.

if exist dist\FFScreenRec.exe (
    echo Build successful!
    echo Executable created at: dist\FFScreenRec.exe
    echo.
    echo File size:
    dir dist\FFScreenRec.exe | find "FFScreenRec"
) else (
    echo Build failed!
    exit /b 1
)

echo.
echo Done!
pause
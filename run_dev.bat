@echo off
echo Starting FFScreenRec in development mode...
echo.

REM Activate virtual environment if exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Install dependencies if not already installed
pip install -q -r requirements.txt

REM Run the application
python app.py

pause
@echo off
echo ========================================
echo Setting up Question Paper Predictor (Flask)
echo ========================================
echo.

REM Activate virtual environment
call venv\Scripts\activate

REM Install Flask dependencies
echo Installing Flask dependencies...
pip install -r requirements_flask.txt

REM Create required folders
echo Creating folders...
if not exist templates mkdir templates
if not exist static mkdir static
if not exist static\css mkdir static\css
if not exist static\js mkdir static\js
if not exist static\img mkdir static\img
if not exist uploads mkdir uploads
if not exist models mkdir models

echo.
echo ✅ Setup complete!
echo.
echo To run the application:
echo python run.py
echo.
pause
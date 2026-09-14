@echo off
setlocal
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
  echo Creating virtual environment...
  python -m venv venv || goto :error
)
call "venv\Scripts\activate.bat"
python -m pip install -r requirements.txt || goto :error
cd backend
python app.py
exit /b 0
:error
echo.
echo Setup failed. Read the error above and try again.
pause
exit /b 1

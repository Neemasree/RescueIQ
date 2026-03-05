@echo off
setlocal
cd /d "%~dp0backend"

if not exist ".venv\Scripts\activate.bat" (
  echo [ERROR] Backend virtual environment not found at backend\.venv
  echo Create it first, for example:
  echo   python -m venv .venv
  echo   .venv\Scripts\pip install -r requirements.txt
  pause
  exit /b 1
)

call ".venv\Scripts\activate.bat"
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

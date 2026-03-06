@echo off
setlocal

cd /d "%~dp0"

echo [RescueIQ] Backend bootstrap starting...

if not exist ".venv\Scripts\python.exe" (
  echo [RescueIQ] Creating virtual environment at .venv
  where py >nul 2>&1
  if %errorlevel%==0 (
    py -3 -m venv .venv
  ) else (
    python -m venv .venv
  )

  if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
  )
)

call ".venv\Scripts\activate.bat"
if %errorlevel% neq 0 (
  echo [ERROR] Could not activate virtual environment.
  pause
  exit /b 1
)

echo [RescueIQ] Upgrading pip...
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
  echo [ERROR] pip upgrade failed.
  pause
  exit /b 1
)

echo [RescueIQ] Installing requirements...
pip install -r requirements.txt
if %errorlevel% neq 0 (
  echo [ERROR] Requirement installation failed.
  pause
  exit /b 1
)

echo [RescueIQ] Starting backend server at http://0.0.0.0:8000
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
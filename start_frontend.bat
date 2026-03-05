@echo off
setlocal
cd /d "%~dp0frontend"

if not exist "package.json" (
  echo [ERROR] package.json not found in frontend folder.
  pause
  exit /b 1
)

if not exist "node_modules" (
  echo Installing frontend dependencies...
  call npm install
  if errorlevel 1 (
    echo [ERROR] npm install failed.
    pause
    exit /b 1
  )
)

call npm run dev

@echo off
setlocal
cd /d "%~dp0"

echo.
echo  ========================================
echo   J.A.R.V.I.S  — starting local server
echo  ========================================
echo.

where py >nul 2>&1
if %ERRORLEVEL%==0 (
  set PY=py -3
) else (
  where python >nul 2>&1
  if %ERRORLEVEL%==0 (
    set PY=python
  ) else (
    echo [ERROR] Python not found. Install Python 3.11+ from https://www.python.org/downloads/
    echo         Tick "Add python.exe to PATH" during install.
    pause
    exit /b 1
  )
)

if not exist ".env" (
  echo [WARN] .env not found. Copying from .env.example ...
  copy /Y ".env.example" ".env" >nul
  echo         Edit .env and add OPENAI_API_KEY or ANTHROPIC_API_KEY, then re-run.
  echo.
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creating virtualenv .venv ...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create venv.
    pause
    exit /b 1
  )
)

echo [2/3] Installing / updating dependencies ...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] pip install failed.
  pause
  exit /b 1
)

echo [3/3] Launching Jarvis on http://127.0.0.1:8765 ...
echo       Browser khulega automatically. Close this window to stop.
echo.

start "" "http://127.0.0.1:8765"
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8765

pause

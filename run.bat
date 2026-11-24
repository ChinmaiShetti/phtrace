@echo off
rem PharmaTrace launcher. Double-click, or run from a terminal:
rem   run.bat          set up if needed, then start the API and the web app and open the browser
rem   run.bat reset    rebuild the database with fresh demo data first (do this just before a demo)
rem   run.bat setup    only install dependencies and build the database, start nothing
setlocal
cd /d "%~dp0"
set "UV_PROJECT_ENVIRONMENT=.venv"
set "MODE=%~1"

rem ---- 1. settings -------------------------------------------------------------
if not exist ".env" (
    copy /y ".env.example" ".env" >nul
    echo Created .env from .env.example.
    echo Set PG_ADMIN_PASSWORD to your local PostgreSQL "postgres" password, save, then run this file again.
    notepad ".env"
    goto :end
)
findstr /r /c:"^PG_ADMIN_PASSWORD=CHANGE_ME" ".env" >nul && (
    echo PG_ADMIN_PASSWORD in .env is still CHANGE_ME. Edit .env, then run this file again.
    notepad ".env"
    goto :end
)

rem ---- 2. tools ------------------------------------------------------------------
where uv >nul 2>nul || (echo uv is not installed: https://docs.astral.sh/uv/ & goto :fail)
where npm >nul 2>nul || (echo Node.js / npm is not installed: https://nodejs.org/ & goto :fail)

rem ---- 3. dependencies (first run only) ------------------------------------------
if not exist "backend\.venv" (
    echo Installing backend dependencies...
    pushd backend & uv sync || (popd & goto :fail)
    popd
)
if not exist "frontend\node_modules" (
    echo Installing frontend dependencies...
    pushd frontend & call npm install || (popd & goto :fail)
    popd
)

rem ---- 4. database (first run, or "reset") ----------------------------------------
if /i "%MODE%"=="reset" del /q "backend\.db_ready" 2>nul
if not exist "backend\.db_ready" (
    echo Building the PharmaTrace database with demo data...
    pushd backend
    uv run python -m scripts.reset_db || (popd & echo Is PostgreSQL running, and is the password in .env right? & goto :fail)
    echo built> .db_ready
    popd
)
pushd backend
.venv\Scripts\python.exe -m scripts.check_db || (popd & goto :fail)
popd
if /i "%MODE%"=="setup" (echo Setup complete. Run run.bat to start PharmaTrace. & goto :end)

rem ---- 5. start ------------------------------------------------------------------------
echo Starting the API (port 8000) and the web app (port 5173) in two new windows...
start "PharmaTrace API" /D "%~dp0backend" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --port 8000"
start "PharmaTrace Web" /D "%~dp0frontend" cmd /k "npm run dev -- --strictPort"
powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; foreach ($i in 1..30) { try { if ((Invoke-RestMethod http://localhost:5173/api/health -TimeoutSec 2).status -eq 'ok') { exit 0 } } catch {}; Start-Sleep -Seconds 1 }; exit 1" || (echo Cannot reach the API through the web app. Check the PharmaTrace API and Web windows. & goto :fail)
start "" "http://localhost:5173"
echo.
echo PharmaTrace is running at http://localhost:5173   (API docs: http://localhost:8000/docs)
echo Demo logins: admin@pharmatrace.local / admin123, qm@pharmatrace.local / qm123,
echo              investigator@pharmatrace.local / investigator123, operator@pharmatrace.local / operator123
echo To stop, close the two PharmaTrace windows.
goto :end

:fail
echo.
echo Something went wrong; see the message above.
:end
echo.
pause
endlocal

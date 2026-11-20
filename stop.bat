@echo off
rem Stops PharmaTrace: the API (port 8000) and the web app (port 5173) started by run.bat.
rem The database (PostgreSQL service) keeps running; it is not part of the app processes.
setlocal
echo Stopping PharmaTrace...

rem the two windows opened by run.bat, with everything running inside them
taskkill /FI "WINDOWTITLE eq PharmaTrace API*" /T /F >nul 2>nul
taskkill /FI "WINDOWTITLE eq PharmaTrace Web*" /T /F >nul 2>nul

rem anything still listening on the two ports (e.g. started by hand)
for %%P in (8000 5173) do (
    for /f "tokens=5" %%I in ('netstat -ano ^| findstr /r /c:":%%P .*LISTENING"') do (
        taskkill /PID %%I /T /F >nul 2>nul && echo   stopped process %%I on port %%P
    )
)

echo PharmaTrace stopped.
echo.
pause
endlocal

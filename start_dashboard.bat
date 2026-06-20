@echo off
cd /d "%~dp0"

echo Checking PostgreSQL service...
for /f "delims=" %%S in ('powershell -NoProfile -Command "(Get-Service postgresql* -ErrorAction SilentlyContinue | Select-Object -First 1).Name"') do set PG_SERVICE=%%S

if "%PG_SERVICE%"=="" (
    echo No PostgreSQL service found. Please confirm PostgreSQL is installed.
    pause
    exit /b 1
)

powershell -NoProfile -Command "if ((Get-Service '%PG_SERVICE%').Status -ne 'Running') { Start-Service '%PG_SERVICE%' }"
if errorlevel 1 (
    echo.
    echo Failed to start %PG_SERVICE%. Try running this shortcut as Administrator,
    echo or start it manually using services.msc.
    pause
    exit /b 1
)

echo Starting Dashboard...
python -m streamlit run app\dashboard.py

pause

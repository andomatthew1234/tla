@echo off
setlocal enabledelayedexpansion
title ConvertTLA Installer

echo ===================================================
echo             ConvertTLA - Installing
echo ===================================================

:: Check if Python is globally installed
echo [+] Inspecting system environment for Python 3...
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [!] Python is missing or not bound to your environment path variable.
    echo [+] Preparing automated Python Runtime deployment...
    
    set "PYTHON_EXE_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
    set "PYTHON_INSTALLER=%TEMP%\python_installer.exe"
    
    echo [+] Retrieving Python runtime binaries...
    curl -L -s -o "!PYTHON_INSTALLER!" "!PYTHON_EXE_URL!"
    
    echo [+] Executing silent installation engine...
    echo [*] Please wait. This environment adjustment takes up to 60 seconds...
    start /wait "" "!PYTHON_INSTALLER!" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    
    :: Force an immediate, active environment variable path refresh inside this script instance
    echo [+] Re-mapping live environment variables...
    for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "Path=%%B;%Path%"
    
    :: Fallback validation check
    python --version >nul 2>&1
    if !ERRORLEVEL! neq 0 (
        echo [!] CRITICAL: Automatic Python deployment timed out or failed installation validation.
        echo [*] Please manually install Python from python.org, check 'Add to PATH', and run this again.
        pause
        exit /b
    )
) else (
    echo [+] Validated Python installation state successfully.
)

:: Ensure pip environment is up to date
echo [+] Optimizing Python Package Manager (pip)...
python -m pip install --upgrade pip --quiet --no-warn-script-location

:: Install application prerequisites
echo [+] Syncing core framework assets...
python -m pip install customtkinter tkinterdnd2 --quiet --no-warn-script-location

:: Verify internal deployment of FFmpeg via Winget engine
echo [+] Inspecting core background encoding pipelines (FFmpeg)...
ffmpeg -version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [+] Deploying missing FFmpeg runtime via Winget engine...
    winget install ffmpeg --exact --no-upgrade --quiet
    
    :: Refresh path maps again to catch winget's mutations
    for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "Path=%%B;%Path%"
) else (
    echo [+] Validated component encoding architecture pipelines (FFmpeg).
)

:: Final Hand-off to onboarding workflow
if exist "onboarding.py" (
    echo [+] Initializing configuration workflows...
    python onboarding.py
) else (
    echo [!] SYSTEM NOTICE: onboarding.py is missing from current repository context.
    echo [*] Ready for codebase deployment.
    pause
)

endlocal
@echo off
setlocal enabledelayedexpansion
title ConvertTLA Downloader

echo ===================================================
echo             ConvertTLA - Downloading
echo ===================================================

:: --- DYNAMIC DESKTOP DETECTION ---
echo [+] Detecting active Desktop location (Local/OneDrive)...
for /f "tokens=2*" %%A in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders" /v Desktop 2^>nul') do (
    set "RAW_DESKTOP=%%B"
)
:: Expand variables like %USERPROFILE% if they are returned by the registry
call set "DESKTOP_DIR=%RAW_DESKTOP%"

echo [+] Target Desktop identified: %DESKTOP_DIR%

:: Define URLs and Paths
set "REPO_ZIP_URL=https://github.com/andomatthew1234/tla/archive/refs/heads/main.zip"
set "ZIP_FILE=%TEMP%\ConvertTLA_Latest.zip"
set "EXTRACT_DIR=%DESKTOP_DIR%\ConvertTLA"

echo [+] Downloading latest ConvertTLA bundle from GitHub...
powershell -Command "Invoke-WebRequest -Uri '%REPO_ZIP_URL%' -OutFile '%ZIP_FILE%'"
if %ERRORLEVEL% neq 0 (
    echo [!] CRITICAL: Failed to download the zip file. Check your internet connection.
    pause
    exit /b
)

echo [+] Extracting archive directly to active Desktop...
if exist "%EXTRACT_DIR%" rmdir /s /q "%EXTRACT_DIR%"
powershell -Command "Expand-Archive -Path '%ZIP_FILE%' -DestinationPath '%EXTRACT_DIR%' -Force"

:: The GitHub default zip structure nests files inside 'tla-main/'
set "REPO_INNER_DIR=%EXTRACT_DIR%\tla-main"

if exist "%REPO_INNER_DIR%" (
    echo [+] Navigating to repository root...
    cd /d "%REPO_INNER_DIR%"
    
    if exist "installer.bat" (
        echo [+] Handoff to installer.bat initiated.
        call "installer.bat"
    ) else (
        echo [!] ERROR: installer.bat not found inside the extracted repository package.
        pause
    )
) else (
    echo [!] ERROR: Extraction failed or folder structure mismatch.
    pause
)

endlocal
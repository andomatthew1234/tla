@echo off
setlocal enabledelayedexpansion
title ConvertTLA Downloader

echo ===================================================
echo             ConvertTLA - Downloading
echo ===================================================

:: Define URLs and Paths
set "REPO_ZIP_URL=https://github.com/andomatthew1234/tla/archive/refs/heads/main.zip"
set "DESKTOP_DIR=%USERPROFILE%\Desktop"
set "ZIP_FILE=%TEMP%\ConvertTLA_Latest.zip"
set "EXTRACT_DIR=%DESKTOP_DIR%\ConvertTLA"

echo [+] Downloading latest ConvertTLA bundle from GitHub...
curl -L -s -o "%ZIP_FILE%" "%REPO_ZIP_URL%"
if %ERRORLEVEL% neq 0 (
    echo [!] CRITICAL: Failed to download the zip file. Check your internet connection.
    pause
    exit /b
)

echo [+] Extracting archive directly to Desktop...
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
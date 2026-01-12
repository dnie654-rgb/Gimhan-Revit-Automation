@echo off
title Gimhan Revit Extensions Installer
color 0A

echo ========================================================
echo       Gimhan Revit Extensions - Auto Installer
echo ========================================================
echo.

:: 1. Check for pyRevit
echo [*] Checking for pyRevit CLI...
where pyrevit >nul 2>nul
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] pyRevit CLI not found!
    echo.
    echo Please make sure pyRevit is installed and added to your PATH.
    echo You can install it from: https://github.com/eirannejad/pyRevit/releases
    echo.
    pause
    exit /b
)
echo [OK] pyRevit found.

:: 2. Define Paths
set "REPO_URL=https://github.com/dnie654-rgb/Gimhan-Revit-Automation/archive/refs/heads/master.zip"
set "INSTALL_DIR=%APPDATA%\GimhanRevitExtensions"
set "ZIP_FILE=%TEMP%\GimhanRevitExtensions_Master.zip"

:: 3. Prepare Directory
if exist "%INSTALL_DIR%" (
    echo [*] Cleaning up previous installation...
    rmdir /s /q "%INSTALL_DIR%"
)
mkdir "%INSTALL_DIR%"

:: 4. Download
echo [*] Downloading extensions from GitHub...
echo     URL: %REPO_URL%
powershell -Command "Invoke-WebRequest -Uri '%REPO_URL%' -OutFile '%ZIP_FILE%'"
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Download failed!
    echo Please check your internet connection or ensure the URL is correct.
    pause
    exit /b
)

:: 5. Extract
echo [*] Extracting file...
powershell -Command "Expand-Archive -Path '%ZIP_FILE%' -DestinationPath '%INSTALL_DIR%' -Force"
del "%ZIP_FILE%"

:: 6. Register with pyRevit
:: GitHub zips usually extract to a folder named "RepoName-branch" (e.g. Gimhan-Revit-Automation-master)
set "EXTRACTED_FOLDER=%INSTALL_DIR%\Gimhan-Revit-Automation-master"

if not exist "%EXTRACTED_FOLDER%" (
    color 0C
    echo [ERROR] Extraction directory not found: %EXTRACTED_FOLDER%
    echo The structure might be different than expected.
    pause
    exit /b
)

echo [*] Registering extensions with pyRevit...
pyrevit extend paths --add "%EXTRACTED_FOLDER%"

echo.
echo ========================================================
echo [SUCCESS] Extensions have been installed!
echo.
echo Please Restart Revit or Reload pyRevit to see the new tabs.
echo ========================================================
echo.
pause

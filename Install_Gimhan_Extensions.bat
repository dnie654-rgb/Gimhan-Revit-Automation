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
    echo.
    pause
    exit /b
)
echo [OK] pyRevit found.

:: 2. Define Paths
set "REPO_URL=https://github.com/dnie654-rgb/Gimhan-Revit-Automation/archive/refs/heads/master.zip"
:: Standard pyRevit extensions path: %APPDATA%\pyRevit\Extensions
:: This automatically handles the Username variable
set "EXTENSIONS_DIR=%APPDATA%\pyRevit\Extensions"
set "INSTALL_NAME=Gimhan-Revit-Automation"
set "FINAL_DIR=%EXTENSIONS_DIR%\%INSTALL_NAME%"
set "ZIP_FILE=%TEMP%\GimhanRevitExtensions_Master.zip"

:: 3. Prepare Directory
echo [*] Target Directory: %EXTENSIONS_DIR%
if not exist "%EXTENSIONS_DIR%" (
    echo [*] Creating extensions directory...
    mkdir "%EXTENSIONS_DIR%"
)

if exist "%FINAL_DIR%" (
    echo [*] Removing old version...
    rmdir /s /q "%FINAL_DIR%"
)

:: 4. Download
echo [*] Downloading extensions from GitHub...
powershell -Command "Invoke-WebRequest -Uri '%REPO_URL%' -OutFile '%ZIP_FILE%'"
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Download failed!
    pause
    exit /b
)

:: 5. Extract
echo [*] Extracting files...
set "TEMP_EXTRACT=%TEMP%\Gimhan_Extract"
if exist "%TEMP_EXTRACT%" rmdir /s /q "%TEMP_EXTRACT%"
powershell -Command "Expand-Archive -Path '%ZIP_FILE%' -DestinationPath '%TEMP_EXTRACT%' -Force"

:: 6. Move to Target
if exist "%TEMP_EXTRACT%\Gimhan-Revit-Automation-master" (
    move "%TEMP_EXTRACT%\Gimhan-Revit-Automation-master" "%FINAL_DIR%"
) else (
    move "%TEMP_EXTRACT%" "%FINAL_DIR%"
)

:: Clean up
del "%ZIP_FILE%"
rmdir /s /q "%TEMP_EXTRACT%"

:: 7. Register
echo [*] Registering extensions with pyRevit...
pyrevit extend paths --add "%FINAL_DIR%"

echo.
echo ========================================================
echo [SUCCESS] Extensions installed to:
echo %FINAL_DIR%
echo.
echo Please Restart Revit to see the new tools.
echo ========================================================
echo.
pause

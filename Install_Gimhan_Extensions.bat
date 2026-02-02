@echo off
title Gimhan Revit Extensions Installer
color 0A

echo ========================================================
echo       Gimhan Revit Extensions - Auto Installer
echo ========================================================
echo.

:: 1. Define Paths
set "REPO_URL=https://github.com/dnie654-rgb/Gimhan-Revit-Automation/archive/refs/heads/master.zip"
set "EXTENSIONS_DIR=%APPDATA%\pyRevit\Extensions"
set "ZIP_FILE=%TEMP%\GimhanRevitExtensions_Master.zip"
set "TEMP_EXTRACT=%TEMP%\Gimhan_Extract"

:: 2. Prepare Directory
if not exist "%EXTENSIONS_DIR%" mkdir "%EXTENSIONS_DIR%"

:: 3. Download
echo [*] Downloading extensions from GitHub...
powershell -Command "Invoke-WebRequest -Uri '%REPO_URL%' -OutFile '%ZIP_FILE%'"
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Download failed!
    pause
    exit /b
)

:: 4. Extract
echo [*] Extracting file...
if exist "%TEMP_EXTRACT%" rmdir /s /q "%TEMP_EXTRACT%"
powershell -Command "Expand-Archive -Path '%ZIP_FILE%' -DestinationPath '%TEMP_EXTRACT%' -Force"

:: 5. Install (Move folders individually)
echo [*] Installing extensions...

:: Handle GitHub zip structure (Repo-master folder)
if exist "%TEMP_EXTRACT%\Gimhan-Revit-Automation-master" (
    set "SOURCE_DIR=%TEMP_EXTRACT%\Gimhan-Revit-Automation-master"
) else (
    set "SOURCE_DIR=%TEMP_EXTRACT%"
)

:: Move each extension folder to the main Extensions directory
:: Note: This overwrites existing extensions with the same name
if exist "%SOURCE_DIR%\ParamTransfer.extension" (
    if exist "%EXTENSIONS_DIR%\ParamTransfer.extension" rmdir /s /q "%EXTENSIONS_DIR%\ParamTransfer.extension"
    move "%SOURCE_DIR%\ParamTransfer.extension" "%EXTENSIONS_DIR%\"
)

if exist "%SOURCE_DIR%\LinkTools.extension" (
    if exist "%EXTENSIONS_DIR%\LinkTools.extension" rmdir /s /q "%EXTENSIONS_DIR%\LinkTools.extension"
    move "%SOURCE_DIR%\LinkTools.extension" "%EXTENSIONS_DIR%\"
)

if exist "%SOURCE_DIR%\HostTools.extension" (
    if exist "%EXTENSIONS_DIR%\HostTools.extension" rmdir /s /q "%EXTENSIONS_DIR%\HostTools.extension"
    move "%SOURCE_DIR%\HostTools.extension" "%EXTENSIONS_DIR%\"
)

if exist "%SOURCE_DIR%\DimensionTools.extension" (
    if exist "%EXTENSIONS_DIR%\DimensionTools.extension" rmdir /s /q "%EXTENSIONS_DIR%\DimensionTools.extension"
    move "%SOURCE_DIR%\DimensionTools.extension" "%EXTENSIONS_DIR%\"
)

if exist "%SOURCE_DIR%\Update.extension" (
    if exist "%EXTENSIONS_DIR%\Update.extension" rmdir /s /q "%EXTENSIONS_DIR%\Update.extension"
    move "%SOURCE_DIR%\Update.extension" "%EXTENSIONS_DIR%\"
)

:: Clean up
del "%ZIP_FILE%"
rmdir /s /q "%TEMP_EXTRACT%"

echo.
echo ========================================================
echo [SUCCESS] Extensions have been installed to:
echo %EXTENSIONS_DIR%
echo.
echo Please Restart Revit or Reload pyRevit.
echo (Since they are in the default folder, no registration is needed!)
echo ========================================================
echo.
pause

@echo off
title Gimhan Revit Extensions - Local Dev Install
color 0B

echo ========================================================
echo       Gimhan Revit Extensions - Local Dev Copy
echo ========================================================
echo.

set "EXTENSIONS_DIR=%APPDATA%\pyRevit\Extensions"
set "SOURCE_DIR=%~dp0"

echo [*] Target Directory: %EXTENSIONS_DIR%
echo [*] Source Directory: %SOURCE_DIR%
echo.

:: ParamTransfer
echo [*] Copying ParamTransfer.extension...
if exist "%EXTENSIONS_DIR%\ParamTransfer.extension" rmdir /s /q "%EXTENSIONS_DIR%\ParamTransfer.extension"
xcopy "%SOURCE_DIR%ParamTransfer.extension" "%EXTENSIONS_DIR%\ParamTransfer.extension\" /E /I /Y /Q

:: LinkTools
echo [*] Copying LinkTools.extension...
if exist "%EXTENSIONS_DIR%\LinkTools.extension" rmdir /s /q "%EXTENSIONS_DIR%\LinkTools.extension"
xcopy "%SOURCE_DIR%LinkTools.extension" "%EXTENSIONS_DIR%\LinkTools.extension\" /E /I /Y /Q

:: HostTools
echo [*] Copying HostTools.extension...
if exist "%EXTENSIONS_DIR%\HostTools.extension" rmdir /s /q "%EXTENSIONS_DIR%\HostTools.extension"
xcopy "%SOURCE_DIR%HostTools.extension" "%EXTENSIONS_DIR%\HostTools.extension\" /E /I /Y /Q

:: RebarTools
echo [*] Copying RebarTools.extension...
if exist "%EXTENSIONS_DIR%\RebarTools.extension" rmdir /s /q "%EXTENSIONS_DIR%\RebarTools.extension"
xcopy "%SOURCE_DIR%RebarTools.extension" "%EXTENSIONS_DIR%\RebarTools.extension\" /E /I /Y /Q

:: Update Extension
echo [*] Copying Update.extension...
if exist "%EXTENSIONS_DIR%\Update.extension" rmdir /s /q "%EXTENSIONS_DIR%\Update.extension"
xcopy "%SOURCE_DIR%Update.extension" "%EXTENSIONS_DIR%\Update.extension\" /E /I /Y /Q

echo.
echo ========================================================
echo [SUCCESS] Local files copied to extensions folder.
echo You may need to Reload pyRevit.
echo ========================================================
pause

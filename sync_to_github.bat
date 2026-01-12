@echo off
title Sync to GitHub
color 0A

:: Check for Git
where git >nul 2>nul
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Git is not installed!
    echo.
    echo This script relies on Git. Please install it first:
    echo https://git-scm.com/downloads
    echo.
    echo Once installed, restart your computer and run this script again.
    pause
    exit /b
)

:: Navigate to script location
cd /d "%~dp0"

echo =========================================
echo      Syncing changes to GitHub
echo =========================================
echo.

:: Add files
echo [*] Adding files...
git add .

:: Commit
set /p commit_msg="Enter commit message (Press Enter for 'Auto Update'): "
if "%commit_msg%"=="" set commit_msg=Auto Update

git commit -m "%commit_msg%"

:: Push
echo.
echo [*] Pushing to GitHub...
git push origin master

if %errorlevel% neq 0 (
    color 0C
    echo.
    echo [ERROR] Push failed. 
    echo Please check your internet connection or GitHub credentials.
    pause
    exit /b
)

echo.
echo [SUCCESS] Changes synced!
pause

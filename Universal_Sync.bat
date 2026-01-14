@echo off
title Universal Sync - Gimhan Revit Automation
color 0A

:: Configuration
set "REPO_URL=https://github.com/dnie654-rgb/Gimhan-Revit-Automation.git"
set "BRANCH_NAME=master"

:: Check for Git
where git >nul 2>nul
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Git is not installed!
    echo Please install Git from https://git-scm.com/downloads
    pause
    exit /b
)

:: Navigate to script directory
cd /d "%~dp0"

echo ========================================================
echo   Universal Sync Tool for Gimhan Revit Automation
echo ========================================================
echo.

:: Initialize Git if not present
if not exist ".git" (
    echo [INIT] No git repository found. Setting up...
    echo.
    
    git init
    if %errorlevel% neq 0 goto ERROR
    
    git branch -M %BRANCH_NAME%
    
    git remote add origin %REPO_URL%
    if %errorlevel% neq 0 (
        echo [WARNING] Remote 'origin' might already exist or failed to add.
    )

    echo [INIT] Downloading existing files from GitHub...
    :: We use allow-unrelated-histories to merge the remote content 
    :: with whatever local files you currently have.
    git pull origin %BRANCH_NAME% --allow-unrelated-histories
    
    if %errorlevel% neq 0 (
        echo.
        echo [WARNING] Initial pull had issues. You might have merge conflicts.
        echo Please resolve them before running this script again.
        pause
        exit /b
    )
    echo [INIT] Setup complete.
    echo.
)

:: Normal Sync Process
echo [SYNC] Pulling latest changes from everyone else...
git pull origin %BRANCH_NAME% --rebase
if %errorlevel% neq 0 (
    color 0E
    echo.
    echo [WARNING] Pull failed or had conflicts.
    echo Please resolve conflicts manually and then run this script again.
    pause
    exit /b
)

echo.
echo [SYNC] Adding your local files...
git add .

echo.
set /p commit_msg="Enter description of changes (Press Enter for 'Update'): "
if "%commit_msg%"=="" set commit_msg=Update

git commit -m "%commit_msg%"

echo.
echo [SYNC] Uploading to GitHub...
git push origin %BRANCH_NAME%

if %errorlevel% neq 0 (
    color 0C
    echo.
    echo [ERROR] Push failed. 
    echo Check your internet, permissions, or if someone else pushed new code.
    echo Try running the script again to pull latest changes.
    pause
    exit /b
)

echo.
echo [SUCCESS] Synchronization complete!
pause

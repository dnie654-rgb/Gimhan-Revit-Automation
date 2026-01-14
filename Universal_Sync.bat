@echo off
setlocal EnableDelayedExpansion
title Universal Sync - Gimhan Revit Automation
color 0A

:: ========================================================
:: Configuration
:: ========================================================
set "REPO_URL=https://github.com/dnie654-rgb/Gimhan-Revit-Automation.git"
set "BRANCH_NAME=master"
set "VERIFIED_FOLDER=Riyan LK Projects - Revit_Custom_Extensions"

:: ========================================================
:: Initialization
:: ========================================================
where git >nul 2>nul
if !errorlevel! neq 0 (
    color 0C
    echo [ERROR] Git is not installed!
    echo Please install Git from https://git-scm.com/downloads
    pause
    exit /b
)

:: Ensure we are in the script's directory
cd /d "%~dp0"

echo ========================================================
echo   Universal Sync Tool for Gimhan Revit Automation
echo ========================================================
echo Current Folder: %CD%
echo.

:: 1. Folder Verification
echo [*] Verifying folder...
echo %CD% | findstr /I /C:"!VERIFIED_FOLDER!" >nul
if !errorlevel! neq 0 (
    echo [WARNING] This folder is not the primary verified SharePoint folder.
    echo Proceed with caution if you are trying to sync a different folder.
    echo.
) else (
    echo [SUCCESS] Verified SharePoint folder detected.
)

:: 2. Git Setup Check
if not exist ".git" (
    echo [INIT] No git repository found. Setting up...
    git init
    git branch -M !BRANCH_NAME!
    git remote add origin !REPO_URL!
    echo [INIT] Fetching latest code from GitHub...
    git pull origin !BRANCH_NAME! --allow-unrelated-histories
) else (
    :: Verify Remote URL
    set "CURRENT_REMOTE="
    for /f "delims=" %%i in ('git config --get remote.origin.url 2^>nul') do set "CURRENT_REMOTE=%%i"
    
    if "!CURRENT_REMOTE!"=="" (
        for /f "tokens=2" %%i in ('git remote -v ^| findstr "origin" ^| findstr "(fetch)"') do set "CURRENT_REMOTE=%%i"
    )

    :: Check if remote matches
    echo !CURRENT_REMOTE! | findstr /I /C:"Gimhan-Revit-Automation" >nul
    if !errorlevel! neq 0 (
        echo [WARNING] Local remote does not match the target Repo.
        echo Current: !CURRENT_REMOTE!
        echo Target:  !REPO_URL!
        echo.
        set /p fix_remote="Would you like to fix the remote? (y/n): "
        if /I "!fix_remote!"=="y" (
            git remote set-url origin !REPO_URL!
            echo [SUCCESS] Remote updated to: !REPO_URL!
        )
    ) else (
        echo [SUCCESS] Remote repository verified.
    )
)

:: 3. SharePoint Sync Safety Check
if exist "~$*" (
    echo [NOTICE] Active Office files detected. 
    echo Please close any open Excel/Word/PowerPoint files in this folder 
    echo to ensure SharePoint sync is complete.
    echo.
)

:: 4. Sync Process
echo [SYNC] Pulling latest changes from GitHub...
:: Added --autostash to handle uncommitted changes automatically
git pull origin !BRANCH_NAME! --rebase --autostash

if !errorlevel! neq 0 (
    color 0E
    echo.
    echo [WARNING] Pull failed or had conflicts.
    echo Common reasons:
    echo 1. SharePoint is still syncing files.
    echo 2. Someone else pushed changes or you have local changes that conflict.
    echo.
    echo [TIP] Try running the script again. 
    echo If it still fails, you may need to resolve conflicts manually.
    pause
    exit /b
)

echo.
echo [SYNC] Adding your changes...
git add .
git status -s

echo.
echo Press Enter if you don't want to add a message (will use 'Update').
set /p commit_msg="Enter description of what you added/changed: "
if "!commit_msg!"=="" set commit_msg=Update

:: Attempt commit
git commit -m "!commit_msg!" >nul 2>&1
if !errorlevel! equ 0 (
    echo [SYNC] Commit created.
) else (
    echo [SYNC] Nothing new to commit.
)

echo.
echo [SYNC] Uploading to GitHub...
git push origin !BRANCH_NAME!

if !errorlevel! neq 0 (
    color 0C
    echo.
    echo [ERROR] Push failed. 
    echo If this persists, run the script again to pull latest changes.
    pause
    exit /b
)

echo.
echo [SUCCESS] Everything is synced and verified!
pause



@echo off
chcp 65001 >nul
title Git Push - CIT-CQT to GitHub

cd /d "%~dp0"

:: Remove garbled .git if init failed earlier
if exist ".git" (
    echo [1/5] Git repository exists.
) else (
    echo [1/5] Initializing git repository...
    git init
)

:: Set remote
echo [2/5] Setting remote origin...
git remote remove origin 2>nul
git remote add origin https://github.com/LucaSun-456/CIT-CQT.git

:: Set committer identity (repo-level, won't affect global git config)
echo [3/5] Setting committer identity...
git config user.name "LucaSun-456"
git config user.email "13964313628@163.com"

:: Stage all files (.gitignore will filter sensitive files)
echo [4/5] Staging files...
git add .

:: Commit
echo [5/5] Committing...
git commit -m "Initial commit - CIT/CQT mock interrogation system"

:: Push
echo [5/5] Pushing to GitHub (master branch)...
git push -u origin master

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo   Upload successful!
    echo   Repo: https://github.com/LucaSun-456/CIT-CQT
    echo ============================================================
) else (
    echo.
    echo [ERROR] Push failed. Common causes:
    echo   1. Remote repo not created yet on GitHub
    echo   2. Not authenticated with GitHub
    echo   3. Default branch is 'master' instead of 'main'
    echo.
    echo   Try: git push -u origin master
    echo   Or login first: gh auth login
)

pause

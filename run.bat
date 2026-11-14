@echo off
setlocal
chcp 65001 >nul 2>&1
cd /d "%~dp0" || exit /b 1
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONDONTWRITEBYTECODE=1"
py run.py %*
exit /b %errorlevel%

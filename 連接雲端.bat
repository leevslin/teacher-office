@echo off
rem Teacher Office: connect to the cloud (GitHub). Keep this file ASCII-only.
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
title Teacher Office - Connect to cloud

set "PY="
py -3 -c "import sys" >nul 2>nul && set "PY=py -3"
if not defined PY python -c "import sys" >nul 2>nul && set "PY=python"
if not defined PY (
  echo  [!] Python 3 was not found. Please run the office once first.
  pause
  exit /b 1
)

where git >nul 2>nul && goto havegit
if exist "C:\Program Files\Git\cmd\git.exe" goto havegit
echo.
echo  Git is not installed. Installing Git for Windows ...
winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
if exist "C:\Program Files\Git\cmd\git.exe" goto havegit
echo.
echo  [!] Could not install Git automatically.
echo      Please install it from https://git-scm.com/download/win (keep all default options),
echo      then run this file again.
start "" "https://git-scm.com/download/win"
pause
exit /b 1

:havegit
set "PATH=C:\Program Files\Git\cmd;%PATH%"
echo.
echo  Step 1. Create an EMPTY PRIVATE repository on GitHub first:
echo          https://github.com/new   (name: teacher-office, choose Private, do not add README)
echo.
echo  Step 2. Paste the repository address below.
echo          Just press Enter to use: https://github.com/leevslin/teacher-office.git
echo.
set "URL="
set /p "URL=Repository address: "
if "%URL%"=="" set "URL=https://github.com/leevslin/teacher-office.git"
%PY% tools\cloud_sync.py setup "%URL%"
echo.
pause

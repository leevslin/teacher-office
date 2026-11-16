@echo off
rem Teacher Office launcher (keep this file ASCII-only)
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
title Teacher Office

set "PY="
py -3 -c "import sys" >nul 2>nul && set "PY=py -3"
if defined PY goto havepy
python -c "import sys" >nul 2>nul && set "PY=python"
if defined PY goto havepy
echo.
echo  [!] Python 3 was not found on this computer.
echo      Please install it from https://www.python.org/downloads/
echo      and tick "Add python.exe to PATH" during setup, then run this file again.
echo.
start "" "https://www.python.org/downloads/"
pause
exit /b 1

:havepy
%PY% -c "import docx, openpyxl" >nul 2>nul
if errorlevel 1 (
  echo Installing python-docx and openpyxl ...
  %PY% -m pip install --user python-docx openpyxl
)

%PY% tools\office_server.py
echo.
echo The office has stopped.
pause

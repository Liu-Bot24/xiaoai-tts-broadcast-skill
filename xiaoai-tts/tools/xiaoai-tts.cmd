@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "TOOL=%SCRIPT_DIR%xiaoai-tts"

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 "%TOOL%" %*
  exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
  python "%TOOL%" %*
  exit /b %ERRORLEVEL%
)

echo Python 3 is required but was not found in PATH. 1>&2
exit /b 1

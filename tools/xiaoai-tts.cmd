@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "TOOL=%SCRIPT_DIR%..\xiaoai-tts\tools\xiaoai-tts.cmd"

if not exist "%TOOL%" (
  echo ERROR: nested tool not found: %TOOL% 1>&2
  exit /b 1
)

call "%TOOL%" %*
exit /b %ERRORLEVEL%

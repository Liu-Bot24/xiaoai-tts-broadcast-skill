@echo off
setlocal
set "PYTHONIOENCODING=utf-8:replace"
set "SCRIPT_DIR=%~dp0"
set "TOOL=%SCRIPT_DIR%xiaoai-tts"

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 8)" >nul 2>nul
  if %ERRORLEVEL%==0 (
    py -3 "%TOOL%" %*
    exit /b %ERRORLEVEL%
  )
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
  python -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 8)" >nul 2>nul
  if %ERRORLEVEL%==0 (
    python "%TOOL%" %*
    exit /b %ERRORLEVEL%
  )
)

echo Python 3.8 or newer is required but was not found in PATH. 1>&2
exit /b 1

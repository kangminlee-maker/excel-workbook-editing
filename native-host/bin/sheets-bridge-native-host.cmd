@echo off
setlocal

set "SCRIPT_DIR=%~dp0"

where py >NUL 2>NUL
if %ERRORLEVEL% EQU 0 (
  py -3 "%SCRIPT_DIR%sheets-bridge-native-host"
) else (
  python "%SCRIPT_DIR%sheets-bridge-native-host"
)

exit /b %ERRORLEVEL%

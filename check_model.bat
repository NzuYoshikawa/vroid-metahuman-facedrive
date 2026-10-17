@echo off
rem Double-click to check an imported model (height, bone names, morphs, spring bones).
call "%~dp0settings.bat"
if not exist "%PROJECT%" (
  echo Project not found: %PROJECT%
  echo Edit settings.bat first.
  pause
  exit /b 1
)
if exist "%~dp0model_report.json" del "%~dp0model_report.json"
"%UE_DIR%\Engine\Binaries\Win64\UnrealEditor.exe" "%PROJECT%" -ExecutePythonScript="%~dp0ue_check_model.py" -nullrhi -unattended -nosplash -abslog="%~dp0check_model.log"
echo.
if exist "%~dp0model_report.json" (
  echo Finished. See model_report.json.
) else (
  echo Failed. See check_model.log ^(search for "SystemExit" or "Error"^).
)
pause

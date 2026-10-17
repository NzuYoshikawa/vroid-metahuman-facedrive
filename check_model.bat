@echo off
rem Double-click to check an imported model (height, bone names, morphs, spring bones).
call "%~dp0settings.bat"
if not exist "%PROJECT%" (
  echo Project not found: %PROJECT%
  pause
  exit /b 1
)
"%UE_DIR%\Engine\Binaries\Win64\UnrealEditor.exe" "%PROJECT%" -ExecutePythonScript="%~dp0ue_check_model.py" -nullrhi -unattended -nosplash -abslog="%~dp0check_model.log"
echo.
echo Finished. See model_report.json.
pause

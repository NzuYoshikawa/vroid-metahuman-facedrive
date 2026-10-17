@echo off
rem Double-click to run every step inside Unreal Editor (no PowerShell needed).
rem Before running: write "vrm" and "vroid_dir" in config.json, and set the paths in settings.bat.
call "%~dp0settings.bat"
if not exist "%PROJECT%" (
  echo Project not found: %PROJECT%
  echo Edit settings.bat first.
  pause
  exit /b 1
)
if not exist "%UE_DIR%\Engine\Binaries\Win64\UnrealEditor.exe" (
  echo Unreal Editor not found: %UE_DIR%
  echo Edit settings.bat first.
  pause
  exit /b 1
)
if exist "%~dp0run_all_done.txt" del "%~dp0run_all_done.txt"
set TRIES=0
:run
set /a TRIES+=1
echo Starting Unreal Editor (no window is shown). This takes several minutes. Do not close this window. [try %TRIES% of 3]
"%UE_DIR%\Engine\Binaries\Win64\UnrealEditor.exe" "%PROJECT%" -ExecutePythonScript="%~dp0ue_run_all.py" -nullrhi -unattended -nosplash -NoTextureStreaming -abslog="%~dp0run_all.log"
if exist "%~dp0run_all_done.txt" goto finished
if %TRIES% LSS 3 (
  echo Unreal Editor stopped before finishing. Trying again...
  goto run
)
echo.
echo Unreal Editor stopped before finishing 3 times. See run_all.log.
pause
exit /b 1
:finished
echo.
echo Finished. See run_all_report.json (result of each step) and run_all.log.
pause

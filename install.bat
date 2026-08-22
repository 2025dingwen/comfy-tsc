@echo off
setlocal EnableExtensions
cd /d "%~dp0"
chcp 65001 >nul

echo [comfy-tsc] Installing dependencies...
echo.

set "PY="

if exist "F:\comflyui\ComfyUI\python_embeded\python.exe" (
  set "PY=F:\comflyui\ComfyUI\python_embeded\python.exe"
) else if exist "F:\ComfyUI\python_embeded\python.exe" (
  set "PY=F:\ComfyUI\python_embeded\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
  set "PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
) else (
  where python >nul 2>&1
  if not errorlevel 1 set "PY=python"
)

if not defined PY (
  echo ERROR: Python not found.
  echo Run manually: ^<ComfyUI-python^> -m pip install -r requirements.txt
  pause
  exit /b 1
)

echo Using: %PY%
echo.

"%PY%" -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo ERROR: pip install failed.
  pause
  exit /b 1
)

if not exist config.json (
  copy /Y config.example.json config.json >nul
  echo Created config.json - EDIT models and llama_server_exe paths for your machine.
)

echo.
echo [comfy-tsc] Done.
echo   1. Copy this folder to ComfyUI\custom_nodes\
echo   2. Edit config.json if needed
echo   3. Restart ComfyUI
echo   4. Open browser: http://127.0.0.1:8188
echo   5. Drag example_workflow.json into ComfyUI, or search nodes: TSC
echo.
echo Note: "Ignoring invalid distribution ~ip" is a broken pip entry on your
echo       system Python - safe to ignore; it does not affect this plugin.
echo.
pause

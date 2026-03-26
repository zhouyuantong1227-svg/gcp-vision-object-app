@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1

if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 goto :error
)

".venv\Scripts\python.exe" -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
".venv\Scripts\python.exe" -m pip install -r requirements-packaging.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
if errorlevel 1 (
  ".venv\Scripts\python.exe" -m pip install -r requirements-packaging.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
  if errorlevel 1 goto :error
)

".venv\Scripts\python.exe" -m PyInstaller --noconfirm vision_app.spec
if errorlevel 1 goto :error

echo EXE created at dist\VisionObjectApp.exe
pause
exit /b 0

:error
echo Build failed. Please send the full error output.
pause
exit /b 1

@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1

if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 goto :error
)

".venv\Scripts\python.exe" -c "import fastapi, uvicorn, multipart" >nul 2>nul
if errorlevel 1 (
  ".venv\Scripts\python.exe" -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
  ".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
  if errorlevel 1 (
    ".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
    if errorlevel 1 goto :error
  )
)

".venv\Scripts\python.exe" launcher.py
exit /b 0

:error
echo Launch failed. Please send the full error output.
pause
exit /b 1

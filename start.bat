@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .env copy .env.example .env >nul
if not exist .venv (
  echo Создаю виртуальное окружение...
  py -3 -m venv .venv 2>nul || python -m venv .venv
)
call .venv\Scripts\activate.bat
echo Проверяю библиотеки...
python -m pip install -q -r requirements.txt
python server.py
pause

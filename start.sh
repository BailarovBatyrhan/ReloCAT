#!/usr/bin/env bash
cd "$(dirname "$0")"
[ -f .env ] || cp .env.example .env
if [ ! -d .venv ]; then
  echo "Создаю виртуальное окружение..."
  python3 -m venv .venv
fi
source .venv/bin/activate
echo "Проверяю библиотеки..."
python -m pip install -q -r requirements.txt
python server.py

@echo off
cd /d "%~dp0backend"
if not exist "venv\Scripts\python.exe" (
    echo Backend virtual environment not found. Follow backend\README.md to create it.
    exit /b 1
)
"venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000

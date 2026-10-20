@echo off
cd /d "%~dp0backend"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000
    exit /b %errorlevel%
)
if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000
    exit /b %errorlevel%
)
python manage.py runserver 127.0.0.1:8000
exit /b %errorlevel%

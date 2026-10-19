@echo off
cd /d "%~dp0backend"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" manage.py runserver localhost:8000 --settings=usp_backend.xampp_settings
    exit /b %errorlevel%
)
if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" manage.py runserver localhost:8000 --settings=usp_backend.xampp_settings
    exit /b %errorlevel%
)
python manage.py runserver localhost:8000 --settings=usp_backend.xampp_settings
exit /b %errorlevel%

@echo off
setlocal
cd /d "%~dp0"
title CrisSteel - CrisFerreterias
set "DB_NAME=CrisFerreterias"
set "DB_USER=crisferreterias_app"
set "DB_PASSWORD=crissteel_xampp_2026"
set "DB_HOST=127.0.0.1"
set "DB_PORT=3306"
echo ==========================================
echo    CRISSTEEL - MARIADB DE XAMPP
echo ==========================================
echo.
if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno virtual...
    py -3 -m venv .venv
)
if not exist ".venv\Scripts\python.exe" (
    echo No se pudo crear el entorno virtual.
    pause
    exit /b 1
)
echo Verificando dependencias...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto error
echo Preparando MariaDB de XAMPP en el puerto 3306...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\preparar_xampp.ps1"
if errorlevel 1 goto error
echo Aplicando migraciones...
".venv\Scripts\python.exe" manage.py migrate
if errorlevel 1 goto error
echo Poblando CrisFerreterias...
".venv\Scripts\python.exe" manage.py poblar_crisferreterias
if errorlevel 1 goto error
echo Iniciando sitio en http://127.0.0.1:8000/
start "Servidor CrisSteel" cmd /k ""%~dp0.venv\Scripts\python.exe" "%~dp0manage.py" runserver 127.0.0.1:8000"
exit /b 0
:error
echo No fue posible iniciar CrisSteel. Revisa el mensaje anterior.
pause
exit /b 1

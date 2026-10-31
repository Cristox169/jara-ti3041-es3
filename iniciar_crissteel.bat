@echo off
setlocal
cd /d "%~dp0"
title CrisSteel - CrisFerreterias
echo ==========================================
echo    CRISSTEEL - MARIADB CRISFERRETERIAS
echo ==========================================
echo.
if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno virtual...
    py -3.13 -m venv .venv
)
if not exist ".venv\Scripts\python.exe" (
    echo No se pudo crear el entorno virtual.
    pause
    exit /b 1
)
echo Verificando dependencias...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto error
echo Iniciando MariaDB 11.4 en el puerto 3307...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\iniciar_mariadb.ps1"
if errorlevel 1 goto error
echo Aplicando migraciones...
".venv\Scripts\python.exe" manage.py migrate
if errorlevel 1 goto error
echo Poblando CrisFerreterias...
".venv\Scripts\python.exe" manage.py poblar_crisferreterias
if errorlevel 1 goto error
echo Iniciando sitio en http://127.0.0.1:8000/
start "Servidor CrisSteel" cmd /k ""%~dp0.venv\Scripts\python.exe" "%~dp0manage.py" runserver 127.0.0.1:8000"
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:8000/"
exit /b 0
:error
echo No fue posible iniciar CrisSteel. Revisa el mensaje anterior.
pause
exit /b 1

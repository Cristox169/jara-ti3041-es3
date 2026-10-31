@echo off
setlocal
cd /d "%~dp0"
title CrisSteel - Entrega portatil
set "DB_ENGINE=sqlite"

echo ==========================================
echo    CRISSTEEL - ENTREGA PORTATIL
echo ==========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno virtual...
    where py >nul 2>&1
    if errorlevel 1 (
        python -m venv .venv
    ) else (
        py -3 -m venv .venv
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo No se pudo crear el entorno virtual.
    pause
    exit /b 1
)

echo Instalando dependencias...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto error

echo Preparando la base local...
".venv\Scripts\python.exe" manage.py migrate
if errorlevel 1 goto error
".venv\Scripts\python.exe" manage.py poblar_crisferreterias
if errorlevel 1 goto error

echo Abriendo http://127.0.0.1:8000/
start "Servidor CrisSteel" cmd /k ""%~dp0.venv\Scripts\python.exe" "%~dp0manage.py" runserver 127.0.0.1:8000"
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:8000/"
exit /b 0

:error
echo No fue posible iniciar CrisSteel. Revisa el mensaje anterior.
pause
exit /b 1

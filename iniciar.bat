@echo off
REM ==========================================================================
REM  Diplonautic DEMO - arranque en Windows con doble clic
REM  1. Crea el entorno virtual .venv si no existe
REM  2. Instala las dependencias de requirements.txt
REM  3. Arranca la web en http://127.0.0.1:5000
REM ==========================================================================
setlocal
cd /d "%~dp0"
chcp 65001 >nul

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] No se encuentra Python. Instala Python 3.10 o superior desde https://www.python.org
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno virtual...
    python -m venv .venv || goto :error
)

echo Instalando dependencias...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt || goto :error

echo.
echo Abriendo http://127.0.0.1:5000 ... (Ctrl+C para detener)
start "" "http://127.0.0.1:5000"
".venv\Scripts\python.exe" run.py
goto :eof

:error
echo [ERROR] No se pudo preparar el entorno. Revisa los mensajes anteriores.
pause
exit /b 1

@echo off
chcp 65001 >nul
title ANE Scraper
cd /d "%~dp0"

if exist "%~dp0.venv\Scripts\python.exe" goto venv_ok
echo [0] Creando entorno virtual e instalando dependencias...
python -m venv .venv || goto fallo
".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto fallo
:venv_ok

set PY=.venv\Scripts\python.exe
if not exist "%PY%" set PY=python
set "SCRAPE_ARGS="

:menu
cls
echo ============================================================
echo   ANE Scraper - www.ane.cr   (menu principal)
echo ============================================================
echo.
echo  [1] Ejecutar (normal)
echo      Usa lo ya scrapeado. Si todo esta completo, solo
echo      regenera los Excel en segundos.
echo.
echo  [2] Actualizar: buscar puestos nuevos
echo      Re-escanea el portal, AGREGA los puestos nuevos y
echo      CONSERVA el historico (nada se borra). Los puestos
echo      dados de baja se quedan en el archivo. (~5-10 min)
echo.
echo  [3] Actualizar: datos frescos desde cero
echo      BORRA todo y re-scrapea el portal completo. El CSV
echo      refleja EXACTAMENTE lo que hay hoy: entran los
echo      nuevos, salen los dados de baja. (~30-40 min)
echo.
echo  [4] Solo regenerar Excel
echo      Sin scraping ni sesion. Segundos. NOTA: el filtro de
echo      puestos nuevos usa el historial, asi que hagalo cuando
echo      no haya un scrape corriendo.
echo.
echo  [5] Comprobar sesion ANE
echo      Dice si la sesion sigue activa (LOGIN ACTIVO).
echo      Si caduco, inicie sesion en Brave y vuelva aqui.
echo.
echo  [0] Salir
echo ------------------------------------------------------------
echo  Cada operacion genera TRES archivos en salida\:
echo    puestos.xlsx            TODOS los registros (estadistica)
echo    puestos_vigentes.xlsx   SOLO vacantes vigentes (las que
echo                            NO han vencido al dia de hoy),
echo                            para buscar trabajo sin ruido
echo    puestos_nuevos_FECHA    SOLO puestos nuevos (no registrados en el
echo                            historial); si no hay, el archivo del dia
echo                            se conserva + actualiza historial_ids.txt
echo ============================================================
set "op="
set /p "op=  Opcion: "
if defined op set "op=%op:~0,1%"
if "%op%"=="1" goto op1
if "%op%"=="2" goto op2
if "%op%"=="3" goto op3
if "%op%"=="4" goto op4
if "%op%"=="5" goto op5
if "%op%"=="0" goto fin
if "%op%"=="" goto fin
echo.
echo  Opcion no valida: "%op%"
pause
goto menu

:op1
set "SCRAPE_ARGS="
goto pipeline

:op2
echo.
echo [*] Reseteando marcadores (los datos ya scrapeados se conservan)...
"%PY%" reset_state.py || goto fallo
set "SCRAPE_ARGS="
goto pipeline

:op3
set "SCRAPE_ARGS=--limpiar"
goto pipeline

:op4
echo.
echo [*] Regenerando columnas derivadas...
"%PY%" reglas.py || goto fallo
echo [*] Generando Excel (TODOS)...
"%PY%" a_excel.py || goto fallo
echo [*] Generando Excel (SOLO vigentes)...
"%PY%" a_excel.py --vigentes --salida "%~dp0salida\puestos_vigentes.xlsx" || goto fallo
echo [*] Generando Excel (SOLO nuevos vs historial)...
"%PY%" a_excel.py --nuevos || goto fallo
call :listo
pause
goto menu

:op5
echo.
"%PY%" check_session.py
if errorlevel 1 echo  (sin sesion activa, o error CDP arriba)
echo.
pause
goto menu

:pipeline
echo.
echo [1/4] Brave / CDP puerto 9222...
netstat -an | findstr /c:":9222 " | findstr /c:"LISTENING" >nul
if not errorlevel 1 goto puerto_ok
echo       Puerto libre. Relanzando Brave con depuracion...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_brave.ps1"
if errorlevel 1 goto fallo
set /a _int=0
:espera_puerto
netstat -an | findstr /c:":9222 " | findstr /c:"LISTENING" >nul
if not errorlevel 1 goto puerto_ok
set /a _int+=1
if %_int% geq 30 goto fallo
ping -n 2 127.0.0.1 >nul
goto espera_puerto
:puerto_ok
echo       Puerto 9222 activo.

echo [2/4] Sesion ANE...
"%PY%" check_session.py
if errorlevel 1 goto sin_sesion

echo [3/4] Scraping %SCRAPE_ARGS%...
"%PY%" scrape.py %SCRAPE_ARGS%
if errorlevel 1 goto fallo

echo [4/4] Columnas + Excel...
"%PY%" reglas.py || goto fallo
"%PY%" a_excel.py || goto fallo
"%PY%" a_excel.py --vigentes --salida "%~dp0salida\puestos_vigentes.xlsx" || goto fallo
"%PY%" a_excel.py --nuevos || goto fallo
call :listo
pause
goto menu

:listo
echo.
echo LISTO - tres archivos en salida\:
echo   puestos.xlsx            TODOS los registros
echo   puestos_vigentes.xlsx   SOLO vigentes (sin fecha vencida)
echo   puestos_nuevos_FECHA    SOLO nuevos vs historial_ids.txt
start "" "%~dp0salida\puestos_vigentes.xlsx"
echo.
exit /b 0

:sin_sesion
echo.
echo  No hay sesion ANE activa.
echo  1. Abra https://www.ane.cr/ en Brave e inicie sesion.
echo  2. Elija [5] para comprobar, luego repita su opcion.
echo.
pause
goto menu

:fallo
echo.
echo  ERROR: un paso fallo (revise el mensaje anterior).
echo.
pause
goto menu

:fin
exit /b 0

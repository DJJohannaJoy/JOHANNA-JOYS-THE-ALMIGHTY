@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title Johanna Joy's THE ALMIGHTY - FIRST SPARK
set "PYTHONPATH="
set "PIP_NO_CACHE_DIR=1"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "SET_SCANNER=%~dp0"
set "PYEXE=%~dp0.venv_py312\Scripts\python.exe"
if not exist "%PYEXE%" goto prepare
if not exist "%~dp0engine\audfprint\audfprint.py" goto prepare
if not exist "%~dp0tools\ffmpeg\ffmpeg.exe" goto prepare
if not exist "%~dp0tools\node\node.exe" goto prepare
if not exist "%~dp0engine\mix-id\node_modules\shazam-api" goto prepare
goto launch
:prepare
echo.
echo =========================================================
echo  SET SCANNER - Vollautomatische Ersteinrichtung
echo  Nichts suchen, nichts manuell installieren.
echo  Beim ersten Mal wird Internet benoetigt.
echo =========================================================
echo.
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 "%~dp0setup_components.py"
) else (
  where python >nul 2>&1
  if errorlevel 1 goto no_python
  python "%~dp0setup_components.py"
)
if errorlevel 1 goto failed
:launch
"%PYEXE%" -c "import PIL" >nul 2>&1
if errorlevel 1 "%PYEXE%" -m pip install --no-cache-dir "Pillow>=10"
set "PATH=%~dp0tools\node;%~dp0tools\ffmpeg;%PATH%"
"%PYEXE%" "%~dp0scanner.py"
if errorlevel 1 goto failed
exit /b 0
:no_python
echo Python nicht installiert. Die vollautomatische Engine-Einrichtung konnte nicht starten.
echo Offizielle Installationsadresse: https://www.python.org/downloads/windows/
echo [Python wird fuer die Windows-Oberflaeche benoetigt.]
goto failed
:failed
echo.
echo SET SCANNER konnte nicht gestartet werden.
echo Protokoll: "%~dp0Protokolle\EINRICHTUNG.txt"
pause
exit /b 1

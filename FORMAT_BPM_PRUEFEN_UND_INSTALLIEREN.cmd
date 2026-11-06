@echo off
setlocal EnableExtensions
chcp 65001 >nul
set "PROJECT=%~dp0"
set "DESKTOP=%USERPROFILE%\Desktop"
for /f "usebackq delims=" %%D in (`powershell.exe -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"`) do set "DESKTOP=%%D"
set "TARGET=%DESKTOP%\SET SCANNER"
set "PYTHON=%TARGET%\.venv_py312\Scripts\python.exe"
if not exist "%PYTHON%" (
  echo Der vorhandene Desktop-Scanner mit Python 3.12 wurde nicht gefunden.
  pause
  exit /b 1
)
echo Format und BPM werden geprueft. Es werden keine Audiodateien hochgeladen.
"%PYTHON%" "%PROJECT%tests\static_check.py"
if errorlevel 1 goto failed
"%PYTHON%" "%PROJECT%tests\metadata_test.py"
if errorlevel 1 goto failed
"%PYTHON%" "%PROJECT%tests\ui_smoke.py"
if errorlevel 1 goto failed
"%PYTHON%" "%PROJECT%tests\result_merge.py"
if errorlevel 1 goto failed
"%PYTHON%" "%PROJECT%tests\parallel_scan.py"
if errorlevel 1 goto failed
set "BACKUP=%TARGET%\Sicherung_Format_BPM_%RANDOM%"
mkdir "%BACKUP%"
if errorlevel 1 goto failed
for %%F in (scanner_core.py scanner.py ui_first_spark.py ui_workspace.py ui_ai_review.py ai_adaptive.py ai_method.py rekordbox_export.py ui_rekordbox.py ui_text.py set_library.py engine_external.py scan_jobs.py online_requests.py mixid_probe.mjs track_results.py) do (
  if exist "%TARGET%\%%F" (
    copy /y "%TARGET%\%%F" "%BACKUP%\%%F" >nul
    if errorlevel 1 goto failed
  )
)
for %%F in (scanner_core.py scanner.py ui_first_spark.py ui_workspace.py ui_ai_review.py ai_adaptive.py ai_method.py rekordbox_export.py ui_rekordbox.py ui_text.py set_library.py engine_external.py scan_jobs.py online_requests.py mixid_probe.mjs track_results.py) do (
  copy /y "%PROJECT%APP\%%F" "%TARGET%\%%F" >nul
  if errorlevel 1 goto failed
)
echo.
echo Installiert. Bitte Scanner neu starten.
echo Sicherung: %BACKUP%
pause
exit /b 0
:failed
echo.
echo Pruefung oder Installation fehlgeschlagen. Die vorherigen Dateien liegen ggf. in der Sicherung.
pause
exit /b 1

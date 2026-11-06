@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Johanna Joy's THE ALMIGHTY 0.71 FIRST SPARK
set "DESKTOP=%USERPROFILE%\Desktop"
for /f "usebackq delims=" %%D in (`powershell.exe -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"`) do set "DESKTOP=%%D"
set "APPDIR=%DESKTOP%\SET SCANNER"
if not exist "%~dp0APP\scanner.py" (
  echo Bitte diese ZIP vollstaendig entpacken. APP fehlt.
  pause
  exit /b 1
)
if not exist "%APPDIR%" mkdir "%APPDIR%"
if not exist "%APPDIR%\engine" mkdir "%APPDIR%\engine"
if not exist "%APPDIR%\assets" mkdir "%APPDIR%\assets"
copy /y "%~dp0APP\assets\approved_banner.png" "%APPDIR%\assets\approved_banner.png" >nul
if errorlevel 1 goto failed
copy /y "%~dp0APP\assets\first_spark_header.png" "%APPDIR%\assets\first_spark_header.png" >nul
if errorlevel 1 goto failed
copy /y "%~dp0APP\assets\first_spark_header_v2.png" "%APPDIR%\assets\first_spark_header_v2.png" >nul
if errorlevel 1 goto failed
copy /y "%~dp0APP\assets\johanna_joy_logo_weiss.png" "%APPDIR%\assets\johanna_joy_logo_weiss.png" >nul
if errorlevel 1 goto failed
copy /y "%~dp0APP\assets\drop_texture_left.png" "%APPDIR%\assets\drop_texture_left.png" >nul
if errorlevel 1 goto failed
copy /y "%~dp0APP\assets\drop_texture_right.png" "%APPDIR%\assets\drop_texture_right.png" >nul
if errorlevel 1 goto failed
rem Only replace program files, never data, results, environment or user settings.
copy /y "%~dp0APP\assets\almighty_icon.png" "%APPDIR%\assets\almighty_icon.png" >nul
if errorlevel 1 goto failed
copy /y "%~dp0APP\assets\almighty_icon.ico" "%APPDIR%\assets\almighty_icon.ico" >nul
if errorlevel 1 goto failed
for %%F in (scanner.py scan_jobs.py online_requests.py mixid_probe.mjs track_results.py set_library.py ai_adaptive.py ai_method.py rekordbox_export.py ui_rekordbox.py ui_ai_review.py ui_text.py ui_workspace.py ui_first_spark.py scanner_core.py engine_external.py local_ai.py audfprint_utf8.py setup_components.py requirements.txt "2_SET_SCANNER_STARTEN.bat" "THE ALMIGHTY - STARTEN.bat" WAS_IST_WO.txt LOKALE_KI_LM_STUDIO_INSTALLIEREN.url ALTERNATIVE_OLLAMA_INSTALLIEREN.url) do (
   copy /y "%~dp0APP\%%~F" "%APPDIR%\%%~F" >nul
   if errorlevel 1 goto failed
)
echo SET SCANNER auf Desktop installiert. Original-Tracks und Datenbank bleiben unveraendert.
call "%APPDIR%\2_SET_SCANNER_STARTEN.bat"
exit /b %errorlevel%
:failed
echo Fehler beim Kopieren. Bitte ZIP vollstaendig entpacken.
pause
exit /b 1

@echo off
setlocal
set "JARVIS_PROJECT_DIR=%~dp0"
if exist "%JARVIS_PROJECT_DIR%run_jarvis.py" goto verify_project
set "JARVIS_PROJECT_DIR=%~dp0JARVIS-AFNICA\"
if exist "%JARVIS_PROJECT_DIR%run_jarvis.py" goto verify_project
goto missing_project

:verify_project
if not exist "%JARVIS_PROJECT_DIR%jarvis\__main__.py" goto missing_project
set "JARVIS_BUNDLED_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%JARVIS_BUNDLED_PYTHON%" goto check_py
"%JARVIS_BUNDLED_PYTHON%" -c "import sys, tkinter; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if not errorlevel 1 goto run_bundled

:check_py
py -3 -c "import sys, tkinter; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if not errorlevel 1 goto run_py

:check_python
python -c "import sys, tkinter; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if not errorlevel 1 goto run_python

echo Instaleaza Python 3.11 sau mai nou, cu Tcl/Tk, apoi reincearca.
echo Scurtatura Microsoft Store nu este o instalare Python functionala.
pause
exit /b 1

:run_bundled
"%JARVIS_BUNDLED_PYTHON%" -X utf8 "%JARVIS_PROJECT_DIR%run_jarvis.py" %*
goto finished

:run_py
py -3 -X utf8 "%JARVIS_PROJECT_DIR%run_jarvis.py" %*
goto finished

:run_python
python -X utf8 "%JARVIS_PROJECT_DIR%run_jarvis.py" %*

:finished
set "JARVIS_EXIT_CODE=%errorlevel%"
if not "%JARVIS_EXIT_CODE%"=="0" pause
exit /b %JARVIS_EXIT_CODE%

:missing_project
echo JARVIS: pachet incomplet sau launcher mutat separat.
echo Dezarhiveaza TOT fisierul ZIP, apoi deschide folderul JARVIS-AFNICA.
echo Start-Jarvis.cmd, run_jarvis.py si folderul jarvis trebuie sa ramana impreuna.
echo Nu porni aplicatia direct din arhiva ZIP.
pause
exit /b 2

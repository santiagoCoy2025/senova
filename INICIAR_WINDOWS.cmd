@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>&1
if not errorlevel 1 (
  python "%~dp0iniciar.py" %*
  goto resultado
)
where py >nul 2>&1
if not errorlevel 1 (
  py -3 "%~dp0iniciar.py" %*
  goto resultado
)
echo Instala Python 3.12 a 3.15 de 64 bits desde https://www.python.org/downloads/windows/
set "gesicom_resultado=2"
goto fin
:resultado
set "gesicom_resultado=%errorlevel%"
:fin
if not "%gesicom_resultado%"=="0" (
  echo No se completo el inicio. Revisa el mensaje anterior y docs\VSCODE.md.
  if "%~1"=="" pause
)
exit /b %gesicom_resultado%

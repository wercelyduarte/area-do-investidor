@echo off
REM Roda o Gerenciador a partir do codigo-fonte (precisa de Python 3.10+).
REM Na 1a vez instala as dependencias via pip.
cd /d "%~dp0"
setlocal
set "PY_CMD="
where py >nul 2>nul && set "PY_CMD=py -3"
if not defined PY_CMD where python >nul 2>nul && set "PY_CMD=python"
if not defined PY_CMD (
  echo Python NAO encontrado. Instale o Python 3.10+ de https://www.python.org/downloads/
  echo e marque "Add python.exe to PATH". Ou use o instalador .msi, que nao precisa de Python.
  pause
  exit /b 1
)
%PY_CMD% -c "import googleapiclient, google_auth_oauthlib, ttkbootstrap" 2>nul || (
  echo Instalando dependencias...
  %PY_CMD% -m pip install -r requirements.txt || (pause & exit /b 1)
)
%PY_CMD% gerenciador.py
endlocal

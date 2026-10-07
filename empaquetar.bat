@echo off
REM Kolontai - construir el .exe en un Windows con Python 3.12 instalado
REM SPDX-License-Identifier: GPL-3.0-or-later
cd /d "%~dp0"
if not exist .venv-win python -m venv .venv-win || goto :error
call .venv-win\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller || goto :error
python -m pytest -q pruebas || goto :error
pyinstaller --noconfirm kolontai.spec || goto :error
echo.
echo Listo: dist\Kolontai\Kolontai.exe
set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
  for /f %%v in ('python -c "import kolontai; print(kolontai.__version__)"') do %ISCC% /DVersion=%%v instalador\kolontai.iss
) else (
  echo Inno Setup no esta instalado: se omite el instalador.
)
pause
exit /b 0
:error
echo Hubo un error. Revise los mensajes de arriba.
pause
exit /b 1

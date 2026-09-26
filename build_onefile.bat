@echo off
setlocal

cd /d "%~dp0"

echo ========================================
echo Build ATG_DIGICAM WebServer onefile (ATG_WEBSERVER.exe)
echo ========================================

REM ========================================
REM WEB-REL-1A: chon dung Python cua project (Python 3.10)
REM Uu tien 1: .venv\Scripts\python.exe
REM Uu tien 2: C:\Python310\python.exe
REM Fallback : python (PATH)
REM ========================================
set "PYTHON_BIN="
if exist "%~dp0.venv\Scripts\python.exe" set "PYTHON_BIN=%~dp0.venv\Scripts\python.exe"
if not defined PYTHON_BIN if exist "C:\Python310\python.exe" set "PYTHON_BIN=C:\Python310\python.exe"
if not defined PYTHON_BIN (
    set "PYTHON_BIN=python"
    echo Canh bao: khong thay .venv\Scripts\python.exe hoac C:\Python310\python.exe. Dung python trong PATH.
)

echo Python build: %PYTHON_BIN%
"%PYTHON_BIN%" --version
if errorlevel 1 (
    echo Loi: khong chay duoc Python: %PYTHON_BIN%
    pause
    exit /b 1
)

"%PYTHON_BIN%" -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 10) else 1)"
if errorlevel 1 (
    echo Canh bao: Python build KHONG phai 3.10. Nen build bang Python 3.10 cua project.
)

"%PYTHON_BIN%" -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
    echo PyInstaller chua duoc cai trong Python build. Dang cai dat...
    "%PYTHON_BIN%" -m pip install pyinstaller
    if errorlevel 1 (
        echo Loi: khong cai duoc PyInstaller.
        pause
        exit /b 1
    )
)

"%PYTHON_BIN%" -m PyInstaller --noconfirm --clean build_onefile.spec

if errorlevel 1 (
    echo.
    echo Build that bai.
    pause
    exit /b 1
)

echo.
echo Build thanh cong: dist\ATG_WEBSERVER.exe
copy /Y webserver_config.json dist\webserver_config.json >nul
if errorlevel 1 (
    echo Canh bao: khong copy duoc webserver_config.json vao dist.
) else (
    echo Da copy webserver_config.json vao dist.
)
copy /Y HUONG_DAN_CAI_DAT_CHAY_AN.txt dist\HUONG_DAN_CAI_DAT_CHAY_AN.txt >nul
if errorlevel 1 (
    echo Canh bao: khong copy duoc HUONG_DAN_CAI_DAT_CHAY_AN.txt vao dist.
) else (
    echo Da copy HUONG_DAN_CAI_DAT_CHAY_AN.txt vao dist.
)

set "FFMPEG_SRC="
if exist "%~dp0bin\ffmpeg.exe" set "FFMPEG_SRC=%~dp0bin\ffmpeg.exe"
if not defined FFMPEG_SRC if exist "D:\PYTHON-TCR\bin\ffmpeg.exe" set "FFMPEG_SRC=D:\PYTHON-TCR\bin\ffmpeg.exe"
if not defined FFMPEG_SRC if exist "D:\PYTHON-TCR\1. EXE\ATG_AI_SYSTEM_RECORD\bin\ffmpeg.exe" set "FFMPEG_SRC=D:\PYTHON-TCR\1. EXE\ATG_AI_SYSTEM_RECORD\bin\ffmpeg.exe"

if defined FFMPEG_SRC (
    if not exist dist\bin mkdir dist\bin
    copy /Y "%FFMPEG_SRC%" dist\bin\ffmpeg.exe >nul
    if errorlevel 1 (
        echo Canh bao: khong copy duoc ffmpeg.exe vao dist\bin.
    ) else (
        echo Da copy ffmpeg.exe vao dist\bin.
    )
) else (
    echo Canh bao: khong tim thay ffmpeg.exe. File MKV/TS co the khong xem truc tiep duoc tren trinh duyet.
)
echo Dat webserver_config.json canh file exe neu muon dung cau hinh rieng ben ngoai.
pause

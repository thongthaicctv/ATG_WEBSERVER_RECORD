@echo off
setlocal

cd /d "%~dp0"

echo ========================================
echo Build ATG_WEBSERVER onefile
echo ========================================

where pyinstaller >nul 2>nul
if errorlevel 1 (
    echo PyInstaller chua duoc cai. Dang cai dat...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo Loi: khong cai duoc PyInstaller.
        pause
        exit /b 1
    )
)

pyinstaller ^
  --noconfirm ^
  --clean ^
  build_onefile.spec

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
echo Dat webserver_config.json canh file exe neu muon dung cau hinh rieng ben ngoai.
pause

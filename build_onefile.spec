# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


block_cipher = None
project_dir = Path(SPECPATH)


datas = [
    (str(project_dir / "templates"), "templates"),
    (str(project_dir / "static"), "static"),
    (str(project_dir / "icon.ico"), "."),
    (str(project_dir / "logo.png"), "."),
    (str(project_dir / "banner.png"), "."),
    (str(project_dir / "webserver_config.json"), "."),
]

hiddenimports = [
    "waitress",
    "pymysql",
    "openpyxl",
    "werkzeug.security",
    "win32com",
    "win32com.client",
    "pythoncom",
    "win32crypt",
    "win32api",
    "win32con",
    "win32gui",
]
hiddenimports += collect_submodules("openpyxl")
hiddenimports += collect_submodules("pymysql")


a = Analysis(
    ["main.py"],
    pathex=[str(project_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ATG_WEBSERVER",
    icon=str(project_dir / "icon.ico"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

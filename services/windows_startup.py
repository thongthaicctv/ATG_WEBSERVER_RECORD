# services/windows_startup.py
# -*- coding: utf-8 -*-

import os
import sys
from pathlib import Path


APP_NAME = "ATG_WEBSERVER"


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent.parent


def exe_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()

    return app_root() / "ATG_WEBSERVER.exe"


def startup_folder() -> Path:
    return Path(os.environ["APPDATA"]) / r"Microsoft\Windows\Start Menu\Programs\Startup"


def shortcut_path() -> Path:
    return startup_folder() / f"{APP_NAME}.lnk"


def is_startup_enabled() -> bool:
    return shortcut_path().exists()


def enable_startup():
    import win32com.client

    startup_folder().mkdir(parents=True, exist_ok=True)

    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(str(shortcut_path()))

    target = exe_path()

    shortcut.Targetpath = str(target)
    shortcut.WorkingDirectory = str(app_root())
    shortcut.IconLocation = str(target)
    shortcut.Description = "ATG_WEBSERVER - Auto start with Windows"
    shortcut.save()

    return True


def disable_startup():
    path = shortcut_path()

    if path.exists():
        path.unlink()

    return True
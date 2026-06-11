# services/windows_startup.py
# -*- coding: utf-8 -*-

import os
import sys
import winreg
import gc
from pathlib import Path


APP_NAME = "ATG_WEBSERVER"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent.parent


def exe_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()

    dist_exe = app_root() / "dist" / "ATG_WEBSERVER.exe"
    if dist_exe.exists():
        return dist_exe

    return app_root() / "ATG_WEBSERVER.exe"


def startup_command() -> str:
    return f'"{exe_path()}" --minimized'


def icon_path() -> Path:
    path = app_root() / "icon.ico"
    if path.exists():
        return path

    return exe_path()


def startup_folder() -> Path:
    return Path(os.environ["APPDATA"]) / r"Microsoft\Windows\Start Menu\Programs\Startup"


def shortcut_path() -> Path:
    return startup_folder() / f"{APP_NAME}.lnk"


def is_startup_enabled() -> bool:
    return _shortcut_is_valid() or _registry_run_is_valid()


def enable_startup():
    startup_folder().mkdir(parents=True, exist_ok=True)
    _set_registry_run()

    try:
        _save_startup_shortcut()
    except Exception as exc:
        print(f"STARTUP SHORTCUT WARNING: {exc}")

    return True


def _save_startup_shortcut():
    pythoncom = _co_initialize()
    shell = None
    shortcut = None
    try:
        import win32com.client

        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(shortcut_path()))

        target = exe_path()

        shortcut.Targetpath = str(target)
        shortcut.WorkingDirectory = str(app_root())
        shortcut.Arguments = "--minimized"
        shortcut.WindowStyle = 7
        shortcut.IconLocation = str(icon_path())
        shortcut.Description = "ATG_WEBSERVER - Auto start with Windows"
        shortcut.save()
    finally:
        shortcut = None
        shell = None
        gc.collect()
        _co_uninitialize(pythoncom)


def _co_initialize():
    import pythoncom

    pythoncom.CoInitialize()
    return pythoncom


def _co_uninitialize(pythoncom):
    if pythoncom is None:
        return

    try:
        pythoncom.CoUninitialize()
    except Exception:
        pass


def _startup_shortcut_target(path):
    pythoncom = _co_initialize()
    shell = None
    shortcut = None
    try:
        import win32com.client

        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(path))
        target = shortcut.Targetpath
        return target
    finally:
        shortcut = None
        shell = None
        gc.collect()
        _co_uninitialize(pythoncom)


def disable_startup():
    path = shortcut_path()

    if path.exists():
        path.unlink()

    _delete_registry_run()

    return True


def _shortcut_is_valid() -> bool:
    path = shortcut_path()
    if not path.exists():
        return False

    try:
        target = Path(_startup_shortcut_target(path))
        return target.exists()
    except Exception:
        return False


def _registry_run_is_valid() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _value_type = winreg.QueryValueEx(key, APP_NAME)
    except FileNotFoundError:
        return False
    except Exception:
        return False

    target = value.strip().split('"')
    if len(target) >= 2:
        return Path(target[1]).exists()

    return Path(value.split()[0]).exists()


def _set_registry_run():
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, startup_command())


def _delete_registry_run():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        pass

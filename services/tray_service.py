# services/tray_service.py
# -*- coding: utf-8 -*-

import os
import sys
import time
import threading
import webbrowser
import ctypes
from pathlib import Path
from urllib.parse import urlparse


user32 = ctypes.windll.user32


def set_win_timer(hwnd, timer_id, interval_ms):
    result = user32.SetTimer(int(hwnd), int(timer_id), int(interval_ms), None)
    if not result:
        raise ctypes.WinError()
    return result


def kill_win_timer(hwnd, timer_id):
    user32.KillTimer(int(hwnd), int(timer_id))


APP_NAME = "ATG WEBSERVER"
MENU_OPEN_ID = 1001
MENU_EXIT_ID = 1002
_exit_requested = threading.Event()


def resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def icon_path() -> Path:
    bundled_icon = resource_root() / "icon.ico"
    if bundled_icon.exists():
        return bundled_icon

    external_icon = Path(sys.executable).resolve().parent / "icon.ico"
    if external_icon.exists():
        return external_icon

    return bundled_icon


def start_tray_icon(host, port, public_host=""):
    if os.name != "nt":
        return None

    thread = threading.Thread(
        target=_run_tray_icon,
        args=(host, int(port), public_host or ""),
        daemon=True,
    )
    thread.start()
    return thread


def _local_web_url(port):
    return f"http://127.0.0.1:{port}/"


def _public_web_url(port, public_host):
    public_host = str(public_host or "").strip()
    if not public_host:
        return _local_web_url(port)

    if "://" not in public_host:
        public_host = f"http://{public_host}"

    parsed = urlparse(public_host)
    scheme = parsed.scheme or "http"
    host = (parsed.netloc or parsed.path).strip("/")
    if ":" not in host:
        host = f"{host}:{port}"

    return f"{scheme}://{host}/"


def _open_webserver(port):
    url = _local_web_url(port)

    if os.name == "nt":
        try:
            import win32api
            import win32con

            win32api.ShellExecute(0, "open", url, None, None, win32con.SW_SHOWNORMAL)
            return
        except Exception:
            pass

        try:
            os.startfile(url)  # noqa: S606 - URL is generated locally from configured port.
            return
        except Exception:
            pass

    webbrowser.open_new_tab(url)


def _run_tray_icon(host, port, public_host):
    try:
        import win32api
        import win32con
        import win32gui
    except Exception as exc:
        print(f"TRAY INIT WARNING: {exc}")
        return

    message_id = win32con.WM_USER + 20
    left_click_timer_id = 1
    class_name = "ATG_WEBSERVER_TRAY"
    menu_visible = False

    def show_menu(hwnd):
        nonlocal menu_visible
        if menu_visible:
            return

        menu_visible = True
        try:
            _show_menu(hwnd, win32gui, win32con, port)
        finally:
            menu_visible = False

    def window_proc(hwnd, msg, wparam, lparam):
        if msg == message_id:
            if lparam == win32con.WM_LBUTTONDBLCLK:
                try:
                    kill_win_timer(hwnd, left_click_timer_id)
                except Exception:
                    pass
                _open_webserver(port)
            elif lparam == win32con.WM_LBUTTONUP:
                set_win_timer(hwnd, left_click_timer_id, 250)
            elif lparam in (
                win32con.WM_RBUTTONUP,
                win32con.WM_CONTEXTMENU,
                win32con.WM_USER,
                win32con.WM_USER + 1,
            ):
                show_menu(hwnd)
            return True

        if msg == win32con.WM_COMMAND:
            command_id = int(wparam) & 0xFFFF
            if command_id == MENU_OPEN_ID:
                _open_webserver(port)
                return True
            if command_id == MENU_EXIT_ID:
                _exit_app(hwnd, win32gui)
                return True

        if msg == win32con.WM_TIMER and wparam == left_click_timer_id:
            kill_win_timer(hwnd, left_click_timer_id)
            show_menu(hwnd)
            return True

        if msg == win32con.WM_DESTROY:
            _remove_icon(hwnd, win32gui)
            win32gui.PostQuitMessage(0)
            return True

        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    wc = win32gui.WNDCLASS()
    wc.hInstance = win32api.GetModuleHandle(None)
    wc.lpszClassName = class_name
    wc.lpfnWndProc = window_proc

    try:
        win32gui.RegisterClass(wc)
    except Exception:
        pass

    hwnd = win32gui.CreateWindow(
        class_name,
        APP_NAME,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        wc.hInstance,
        None,
    )

    hicon = _load_icon(win32gui, win32con)
    tooltip = f"{APP_NAME} - http://127.0.0.1:{port}"
    _add_icon(hwnd, hicon, tooltip, message_id, win32gui)

    public_text = _public_web_url(port, public_host)
    _show_balloon(hwnd, hicon, tooltip, message_id, public_text, win32gui)

    win32gui.PumpMessages()


def _load_icon(win32gui, win32con):
    path = icon_path()
    if path.exists():
        return win32gui.LoadImage(
            0,
            str(path),
            win32con.IMAGE_ICON,
            0,
            0,
            win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE,
        )

    return win32gui.LoadIcon(0, win32con.IDI_APPLICATION)


def _add_icon(hwnd, hicon, tooltip, message_id, win32gui):
    flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
    nid = (hwnd, 0, flags, message_id, hicon, tooltip)
    win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)


def _show_balloon(hwnd, hicon, tooltip, message_id, public_text, win32gui):
    flags = (
        win32gui.NIF_ICON
        | win32gui.NIF_MESSAGE
        | win32gui.NIF_TIP
        | win32gui.NIF_INFO
    )
    info = "WebServer đang chạy"
    info_title = APP_NAME
    nid = (
        hwnd,
        0,
        flags,
        message_id,
        hicon,
        tooltip,
        info,
        10,
        info_title,
        win32gui.NIIF_INFO,
    )
    win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, nid)
    print(f"{info}: {public_text}")


def _remove_icon(hwnd, win32gui):
    try:
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (hwnd, 0))
    except Exception:
        pass


def _show_menu(hwnd, win32gui, win32con, port):
    menu = win32gui.CreatePopupMenu()

    win32gui.AppendMenu(menu, win32con.MF_STRING, MENU_OPEN_ID, "Mo WebServer")
    win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
    win32gui.AppendMenu(menu, win32con.MF_STRING, MENU_EXIT_ID, "Exit WebServer")
    try:
        win32gui.SetMenuDefaultItem(menu, MENU_OPEN_ID, False)
    except Exception:
        pass

    pos = win32gui.GetCursorPos()
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass

    try:
        command = win32gui.TrackPopupMenu(
            menu,
            win32con.TPM_LEFTALIGN
            | win32con.TPM_RETURNCMD
            | win32con.TPM_NONOTIFY
            | win32con.TPM_LEFTBUTTON
            | win32con.TPM_RIGHTBUTTON,
            pos[0],
            pos[1],
            0,
            hwnd,
            None,
        )
    finally:
        win32gui.PostMessage(hwnd, win32con.WM_NULL, 0, 0)
        win32gui.DestroyMenu(menu)

    if command == MENU_OPEN_ID:
        _open_webserver(port)
    elif command == MENU_EXIT_ID:
        _exit_app(hwnd, win32gui)


def _exit_app(hwnd, win32gui):
    if _exit_requested.is_set():
        return
    _exit_requested.set()

    thread = threading.Thread(
        target=_force_exit_process,
        args=(hwnd, win32gui),
        daemon=False,
    )
    thread.start()


def _force_exit_process(hwnd, win32gui):
    _remove_icon(hwnd, win32gui)
    try:
        win32gui.PostMessage(hwnd, 0x0010, 0, 0)  # WM_CLOSE
    except Exception:
        pass
    try:
        win32gui.DestroyWindow(hwnd)
    except Exception:
        pass

    time.sleep(0.1)
    os._exit(0)

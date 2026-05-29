# services/single_instance.py
# -*- coding: utf-8 -*-

import ctypes
import os


ERROR_ALREADY_EXISTS = 183
_mutex_handle = None


def ensure_single_instance(name="Global\\ATG_WEBSERVER_SINGLE_INSTANCE"):
    if os.name != "nt":
        return True

    global _mutex_handle
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _mutex_handle = kernel32.CreateMutexW(None, False, name)

    if not _mutex_handle:
        return True

    return ctypes.get_last_error() != ERROR_ALREADY_EXISTS

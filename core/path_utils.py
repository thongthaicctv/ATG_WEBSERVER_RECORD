# core/path_utils.py
# -*- coding: utf-8 -*-

import sys
from pathlib import Path


def app_root() -> Path:
    """
    Khi chạy source:
        trả về thư mục project ATG_WEBSERVER.

    Khi build exe:
        trả về thư mục chứa file ATG_WEBSERVER.exe.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent.parent


def get_config_path() -> Path:
    return app_root() / "webserver_config.json"


def get_log_path() -> Path:
    return app_root() / "logs" / "webserver.log"
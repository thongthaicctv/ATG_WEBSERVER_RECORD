# core/config_manager.py
# -*- coding: utf-8 -*-

import json
from copy import deepcopy
from core.path_utils import get_config_path


DEFAULT_CONFIG = {
    "app": {
        "name": "ATG_WEBSERVER",
        "host": "0.0.0.0",
        "port": 8088,
        "public_host": "",
        "debug": False
    },
    "database": {
        "host": "127.0.0.1",
        "port": 3306,
        "user": "atg_app",
        "password": "atg_password",
        "database": "atg_order_system",
        "charset": "utf8mb4"
    },
    "video": {
        "allow_play": True,
        "allow_download": True
    },
    "security": {
        "require_login": False,
        "username": "admin",
        "password": "123456"
    },
    "startup": {
        "auto_start_with_windows": False,
        "startup_mode": "shortcut",
        "start_minimized": True
    },
    "system": {
        "log_file": "logs/webserver.log"
    }
}


def merge_config(default: dict, current: dict) -> dict:
    result = deepcopy(default)

    for key, value in current.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_config(result[key], value)
        else:
            result[key] = value

    return result


def load_config() -> dict:
    config_path = get_config_path()

    if not config_path.exists():
        cfg = deepcopy(DEFAULT_CONFIG)
        save_config(cfg)
        return cfg

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            current = json.load(f)

        return merge_config(DEFAULT_CONFIG, current)

    except Exception:
        cfg = deepcopy(DEFAULT_CONFIG)
        save_config(cfg)
        return cfg


def save_config(cfg: dict):
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
# core/config_manager.py
# -*- coding: utf-8 -*-

import base64
import hashlib
import json
import os
import platform
from copy import deepcopy
from datetime import datetime
from core.path_utils import get_config_path


ENCRYPTED_CONFIG_MARKER = "ATG_ENCRYPTED_CONFIG_V1"


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
        "storage_root": "",
        "storage_roots": [],
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
    except Exception as exc:
        _backup_unreadable_config(config_path, exc)
        cfg = deepcopy(DEFAULT_CONFIG)
        save_config(cfg)
        return cfg

    if is_encrypted_config(current):
        try:
            current = decrypt_config_payload(current)
        except Exception as exc:
            _backup_unreadable_config(config_path, exc)
            cfg = deepcopy(DEFAULT_CONFIG)
            save_config(cfg)
            return cfg
        return merge_config(DEFAULT_CONFIG, current)

    cfg = merge_config(DEFAULT_CONFIG, current)
    save_config(cfg)
    return cfg


def save_config(cfg: dict):
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(encrypt_config_payload(cfg), f, ensure_ascii=False, indent=2)


def is_encrypted_config(data):
    return isinstance(data, dict) and data.get("marker") == ENCRYPTED_CONFIG_MARKER


def encrypt_config_payload(cfg: dict) -> dict:
    plain = json.dumps(cfg, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    try:
        encrypted = _dpapi_encrypt(plain)
        return {
            "marker": ENCRYPTED_CONFIG_MARKER,
            "method": "dpapi-current-user",
            "data": base64.b64encode(encrypted).decode("ascii"),
        }
    except Exception:
        encrypted = _xor_crypt(plain)
        return {
            "marker": ENCRYPTED_CONFIG_MARKER,
            "method": "local-xor-fallback",
            "data": base64.b64encode(encrypted).decode("ascii"),
        }


def decrypt_config_payload(payload: dict) -> dict:
    method = payload.get("method", "")
    encrypted = base64.b64decode(payload.get("data", ""))

    if method == "dpapi-current-user":
        plain = _dpapi_decrypt(encrypted)
    elif method == "local-xor-fallback":
        plain = _xor_crypt(encrypted)
    else:
        raise ValueError(f"Unsupported config encryption method: {method}")

    return json.loads(plain.decode("utf-8"))


def _dpapi_encrypt(data: bytes) -> bytes:
    import win32crypt

    return win32crypt.CryptProtectData(
        data,
        "ATG_WEBSERVER_CONFIG",
        None,
        None,
        None,
        0,
    )


def _dpapi_decrypt(data: bytes) -> bytes:
    import win32crypt

    _description, plain = win32crypt.CryptUnprotectData(
        data,
        None,
        None,
        None,
        0,
    )
    return plain


def _local_key() -> bytes:
    raw = "|".join([
        "ATG_WEBSERVER_CONFIG",
        os.environ.get("COMPUTERNAME", ""),
        os.environ.get("USERNAME", ""),
        platform.node(),
    ])
    return hashlib.sha256(raw.encode("utf-8")).digest()


def _xor_crypt(data: bytes) -> bytes:
    key = _local_key()
    return bytes(byte ^ key[index % len(key)] for index, byte in enumerate(data))


def _backup_unreadable_config(config_path, exc):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = config_path.with_name(
            f"{config_path.stem}.unreadable_{timestamp}{config_path.suffix}"
        )
        config_path.replace(backup_path)
        print(f"CONFIG WARNING: backed up unreadable config to {backup_path}: {exc}")
    except Exception as backup_exc:
        print(f"CONFIG WARNING: could not backup unreadable config: {exc}; {backup_exc}")

# services/db_setup_service.py
# -*- coding: utf-8 -*-
"""
WEB-DB-FIRST-RUN-SETUP

Logic dung chung cho trang Setup Database (first-run) va muc DATABASE trong
trang Cai dat WebServer:
- doc thong tin DB tu form (khong render lai password ra HTML),
- test ket noi nhe (SELECT 1),
- luu vao webserver_config.json bang save_config() hien co (DPAPI).

Khong tao bang, khong doi schema.
"""

import hmac
import logging
import secrets

from flask import request, session

from core.config_manager import load_config, save_config
from db.mysql_client import (
    is_db_config_complete,
    mark_db_ready_unknown,
    test_db_connection,
)


logger = logging.getLogger(__name__)

CSRF_SESSION_KEY = "db_setup_csrf"
DB_EDITABLE_KEYS = ("host", "port", "user", "password", "database")
LOCAL_ADDRESSES = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}


def get_saved_db_config():
    return dict(load_config().get("database", {}) or {})


def db_config_for_display(db_cfg):
    """Ban sao an toan de render: KHONG chua password."""
    db_cfg = db_cfg or {}
    return {
        "host": db_cfg.get("host", "") or "",
        "port": db_cfg.get("port", 3306) or 3306,
        "user": db_cfg.get("user", "") or "",
        "database": db_cfg.get("database", "") or "",
        "has_password": bool(db_cfg.get("password")),
    }


def parse_db_form(form, saved_db_cfg=None):
    """
    Tra ve (db_cfg, errors). Password de trong = giu password da luu, nhung
    chi khi Host/Port/User khong doi (tranh gui password da luu toi host khac).
    """
    saved_db_cfg = saved_db_cfg or {}
    errors = []

    host = str(form.get("db_host", "") or "").strip()
    port_raw = str(form.get("db_port", "") or "").strip()
    user = str(form.get("db_user", "") or "").strip()
    database = str(form.get("db_name", "") or "").strip()
    password = form.get("db_password", "") or ""

    if not host:
        errors.append("Host không được để trống.")
    if not user:
        errors.append("User không được để trống.")
    if not database:
        errors.append("Database không được để trống.")

    port = None
    try:
        port = int(port_raw)
        if not (1 <= port <= 65535):
            raise ValueError
    except ValueError:
        errors.append("Port phải là số từ 1 đến 65535.")

    if password == "" and saved_db_cfg.get("password"):
        same_target = (
            host == str(saved_db_cfg.get("host", "")).strip()
            and str(port) == str(saved_db_cfg.get("port", "")).strip()
            and user == str(saved_db_cfg.get("user", "")).strip()
        )
        if same_target:
            password = saved_db_cfg.get("password", "")

    db_cfg = {
        "host": host,
        "port": port if port is not None else port_raw,
        "user": user,
        "password": password,
        "database": database,
        "charset": saved_db_cfg.get("charset", "utf8mb4") or "utf8mb4",
    }
    return db_cfg, errors


def run_db_test(db_cfg, errors=None):
    if errors:
        return False, " ".join(errors)
    return test_db_connection(db_cfg)


def save_db_config(db_cfg):
    """
    Chi cap nhat cac khoa DB trong config hien tai roi save_config() (DPAPI).
    Doc lai sau khi luu de xac nhan. Tra ve (ok, message).
    """
    if not is_db_config_complete(db_cfg):
        return False, "Thông tin Database chưa đầy đủ, chưa lưu."

    cfg = load_config()
    cfg.setdefault("database", {})
    for key in DB_EDITABLE_KEYS:
        cfg["database"][key] = db_cfg.get(key)
    cfg["database"]["port"] = int(db_cfg.get("port"))
    cfg["database"].setdefault("charset", "utf8mb4")

    save_config(cfg)
    mark_db_ready_unknown()

    reloaded = load_config().get("database", {})
    for key in DB_EDITABLE_KEYS:
        if str(reloaded.get(key)) != str(cfg["database"].get(key)):
            logger.error("DB config verify after save failed at key=%s", key)
            return False, "Đã ghi file cấu hình nhưng đọc lại không khớp. Vui lòng kiểm tra quyền ghi file."

    logger.info(
        "DB config saved host=%s port=%s user=%s database=%s",
        cfg["database"]["host"], cfg["database"]["port"],
        cfg["database"]["user"], cfg["database"]["database"],
    )
    return True, "Đã lưu cấu hình Database (mã hóa)."


def is_local_request():
    return (request.remote_addr or "") in LOCAL_ADDRESSES


def get_csrf_token():
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def check_csrf_token():
    expected = session.get(CSRF_SESSION_KEY) or ""
    provided = request.form.get("csrf_token", "") or request.headers.get("X-CSRF-Token", "")
    return bool(expected) and hmac.compare_digest(str(expected), str(provided))

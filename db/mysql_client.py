# db/mysql_client.py
# -*- coding: utf-8 -*-

import logging
import threading
import time

import pymysql
from core.config_manager import load_config


logger = logging.getLogger(__name__)

# WEB-DB-FIRST-RUN-SETUP: cac truong bat buoc de coi la "da co DB config".
REQUIRED_DB_FIELDS = ("host", "port", "user", "database")

# Timeout cho kiem tra nhe SELECT 1 (giay).
DB_TEST_TIMEOUT_SECONDS = 5

# Cache ket qua kiem tra DB de gate first-run khong ket noi moi request.
_DB_READY_TTL_OK = 60
_DB_READY_TTL_FAIL = 5
_db_ready_lock = threading.Lock()
_db_ready_cache = {"ok": None, "checked_at": 0.0, "message": ""}

# Ma loi pymysql/MySQL lien quan toi ket noi / cau hinh DB.
_CONNECTION_ERROR_CODES = {1044, 1045, 1049, 1130, 2002, 2003, 2005, 2006, 2013}


def get_connection():
    cfg = load_config()["database"]

    return pymysql.connect(
        host=cfg.get("host", "127.0.0.1"),
        port=int(cfg.get("port", 3306)),
        user=cfg.get("user", "atg_app"),
        password=cfg.get("password", ""),
        database=cfg.get("database", "atg_order_system"),
        charset=cfg.get("charset", "utf8mb4"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def fetch_all(sql, params=None):
    params = params or []

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def fetch_one(sql, params=None):
    params = params or []

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()


def execute(sql, params=None):
    params = params or []

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount


# ---------------------------------------------------------------------------
# WEB-DB-FIRST-RUN-SETUP helpers
# ---------------------------------------------------------------------------

def is_db_config_complete(db_cfg):
    db_cfg = db_cfg or {}
    for key in REQUIRED_DB_FIELDS:
        if not str(db_cfg.get(key, "") or "").strip():
            return False
    try:
        port = int(db_cfg.get("port"))
    except (TypeError, ValueError):
        return False
    return 1 <= port <= 65535


def test_db_connection(db_cfg, timeout=DB_TEST_TIMEOUT_SECONDS):
    """
    Kiem tra nhe: ket noi + SELECT 1. Khong tao bang, khong doc/ghi du lieu.
    Tra ve (ok: bool, message: str). Khong bao gio raise, khong lo password.
    """
    db_cfg = db_cfg or {}
    if not is_db_config_complete(db_cfg):
        return False, "Chưa nhập đủ Host, Port, User và Database."

    host = str(db_cfg.get("host", "")).strip()
    port = int(db_cfg.get("port"))
    database = str(db_cfg.get("database", "")).strip()

    conn = None
    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=str(db_cfg.get("user", "")).strip(),
            password=str(db_cfg.get("password", "") or ""),
            database=database,
            charset=db_cfg.get("charset", "utf8mb4") or "utf8mb4",
            connect_timeout=timeout,
            read_timeout=timeout,
            write_timeout=timeout,
            autocommit=True,
        )
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            row = cur.fetchone()
        if not row or row[0] != 1:
            return False, "MySQL phản hồi không đúng với SELECT 1."
        return True, f"Kết nối thành công tới {host}:{port} / {database}."
    except Exception as exc:
        message = describe_db_error(exc, host=host, port=port, database=database)
        logger.warning("DB test connection failed: %s", message)
        return False, message
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def db_error_code(exc):
    args = getattr(exc, "args", None) or ()
    if args and isinstance(args[0], int):
        return args[0]
    return None


def is_db_connection_error(exc):
    if not isinstance(exc, pymysql.err.Error):
        return False
    code = db_error_code(exc)
    if code in _CONNECTION_ERROR_CODES:
        return True
    return isinstance(exc, pymysql.err.OperationalError) and code is None


def describe_db_error(exc, host="", port="", database=""):
    code = db_error_code(exc)
    target = f"{host}:{port}" if host else "MySQL"

    if code == 1045:
        return "Sai User hoặc Password MySQL (1045)."
    if code == 1044:
        return f"User không có quyền truy cập database '{database}' (1044)."
    if code == 1049:
        return f"Database '{database}' không tồn tại trên MySQL (1049)."
    if code == 1130:
        return f"MySQL tại {target} không cho phép máy này kết nối (1130). Cần cấp quyền host cho user."
    if code == 2005:
        return f"Không phân giải được Host '{host}' (2005)."
    if code in (2002, 2003):
        return f"Không kết nối được tới MySQL tại {target} ({code}). Kiểm tra MySQL đã chạy, Host/Port, firewall."
    if code in (2006, 2013):
        return f"Mất kết nối tới MySQL tại {target} ({code})."

    if isinstance(exc, pymysql.err.Error):
        detail = ""
        args = getattr(exc, "args", None) or ()
        if len(args) >= 2:
            detail = str(args[1])
        elif args:
            detail = str(args[0])
        detail = detail.replace("\r", " ").replace("\n", " ")[:200]
        return f"Lỗi MySQL ({code if code is not None else 'n/a'}): {detail}"

    return f"Lỗi kết nối: {type(exc).__name__}: {str(exc)[:200]}"


def check_db_ready(force=False):
    """
    Dung cho gate first-run: config day du + SELECT 1 PASS.
    Ket qua duoc cache (OK 60s, FAIL 5s). Tra ve (ok, message).
    """
    now = time.monotonic()
    with _db_ready_lock:
        ok = _db_ready_cache["ok"]
        age = now - _db_ready_cache["checked_at"]
        ttl = _DB_READY_TTL_OK if ok else _DB_READY_TTL_FAIL
        if not force and ok is not None and age < ttl:
            return ok, _db_ready_cache["message"]

    try:
        db_cfg = load_config().get("database", {})
    except Exception as exc:
        db_cfg = {}
        logger.warning("Cannot load config for DB check: %s", exc)

    if not is_db_config_complete(db_cfg):
        ok, message = False, "Chưa có cấu hình Database."
    else:
        ok, message = test_db_connection(db_cfg)

    with _db_ready_lock:
        _db_ready_cache.update({"ok": ok, "checked_at": time.monotonic(), "message": message})
    return ok, message


def mark_db_ready_unknown():
    with _db_ready_lock:
        _db_ready_cache.update({"ok": None, "checked_at": 0.0, "message": ""})

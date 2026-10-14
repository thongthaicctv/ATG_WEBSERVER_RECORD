# routes/setup_routes.py
# -*- coding: utf-8 -*-
"""
WEB-DB-FIRST-RUN-SETUP: luong cau hinh Database khi chua co DB config hop le.

Quyen truy cap (chi khi DB chua san sang):
- tai khoan root dang dang nhap (session), hoac
- truy cap tu chinh may chay WebServer (127.0.0.1 / ::1).
Khi DB da san sang, trang nay chuyen ve Cai dat WebServer / Dang nhap.
"""

import logging

from flask import Blueprint, jsonify, redirect, render_template, request, url_for

from core.auth_manager import current_user, ensure_default_users
from core.config_manager import load_config
from db.mysql_client import check_db_ready
from services.db_setup_service import (
    check_csrf_token,
    db_config_for_display,
    get_csrf_token,
    get_saved_db_config,
    is_local_request,
    parse_db_form,
    run_db_test,
    save_db_config,
)


logger = logging.getLogger(__name__)

setup_bp = Blueprint("setup", __name__)


def _is_root():
    user = current_user()
    return bool(user and user.get("role") == "root")


def _can_edit():
    return _is_root() or is_local_request()


def _after_ready_url():
    if _is_root():
        return url_for("settings.database_settings")
    if current_user():
        return url_for("dashboard.index")
    return url_for("auth.login", setup="ok")


def _deny_json(message, status=403):
    return jsonify({"ok": False, "message": message}), status


@setup_bp.route("/database", methods=["GET"])
def database():
    ready, status_message = check_db_ready()
    if ready:
        return redirect(_after_ready_url())

    try:
        port = int(load_config().get("app", {}).get("port", 8088))
    except Exception:
        port = 8088

    return render_template(
        "setup/database.html",
        db=db_config_for_display(get_saved_db_config()),
        can_edit=_can_edit(),
        status_message=status_message,
        csrf_token=get_csrf_token(),
        local_url=f"http://127.0.0.1:{port}/setup/database",
    )


@setup_bp.route("/database/test", methods=["POST"])
def test_connection():
    ready, _msg = check_db_ready()
    if ready and not _is_root():
        return _deny_json("Database đã sẵn sàng. Hãy đăng nhập root để thay đổi.")
    if not _can_edit():
        return _deny_json("Chỉ cấu hình được từ máy chạy WebServer hoặc tài khoản root.")
    if not check_csrf_token():
        return _deny_json("Phiên làm việc hết hạn. Hãy tải lại trang.", 400)

    db_cfg, errors = parse_db_form(request.form, get_saved_db_config())
    ok, message = run_db_test(db_cfg, errors)
    return jsonify({"ok": ok, "message": message})


@setup_bp.route("/database/save", methods=["POST"])
def save():
    ready, _msg = check_db_ready()
    if ready and not _is_root():
        return _deny_json("Database đã sẵn sàng. Hãy đăng nhập root để thay đổi.")
    if not _can_edit():
        return _deny_json("Chỉ cấu hình được từ máy chạy WebServer hoặc tài khoản root.")
    if not check_csrf_token():
        return _deny_json("Phiên làm việc hết hạn. Hãy tải lại trang.", 400)

    db_cfg, errors = parse_db_form(request.form, get_saved_db_config())
    ok, message = run_db_test(db_cfg, errors)
    if not ok:
        return jsonify({"ok": False, "message": f"Chưa lưu. {message}"})

    saved, save_message = save_db_config(db_cfg)
    if not saved:
        return jsonify({"ok": False, "message": save_message})

    # Tao user mac dinh neu bang users da ton tai nhung chua co user (hanh vi
    # san co cua ensure_default_users). Khong tao bang.
    try:
        ensure_default_users()
    except Exception as exc:
        logger.warning("ensure_default_users after DB setup failed: %s", exc)

    check_db_ready(force=True)
    return jsonify({
        "ok": True,
        "message": f"{save_message} Đang chuyển trang...",
        "redirect": _after_ready_url(),
    })

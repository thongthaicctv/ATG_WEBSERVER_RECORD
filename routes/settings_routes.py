# routes/settings_routes.py
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, request, redirect, url_for

from core.config_manager import load_config, save_config
from db.mysql_client import get_connection
from services.windows_startup import (
    enable_startup,
    disable_startup,
    is_startup_enabled,
    exe_path,
    shortcut_path,
    startup_command,
)


settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/database", methods=["GET", "POST"])
def database_settings():
    cfg = load_config()
    message = ""

    if request.method == "POST":
        cfg["database"]["host"] = request.form.get("db_host", "127.0.0.1").strip()
        cfg["database"]["port"] = int(request.form.get("db_port", "3306").strip())
        cfg["database"]["user"] = request.form.get("db_user", "atg_app").strip()
        cfg["database"]["password"] = request.form.get("db_password", "").strip()
        cfg["database"]["database"] = request.form.get("db_name", "atg_order_system").strip()

        cfg["app"]["host"] = request.form.get("web_host", "0.0.0.0").strip()
        cfg["app"]["port"] = int(request.form.get("web_port", "8088").strip())
        cfg["app"]["public_host"] = request.form.get("public_host", "").strip()

        cfg.setdefault("video", {})
        cfg["video"]["storage_roots"] = _parse_storage_roots(request.form.get("storage_roots", ""))
        cfg["video"]["storage_root"] = cfg["video"]["storage_roots"][0] if cfg["video"]["storage_roots"] else ""
        cfg["video"]["allow_play"] = bool(request.form.get("allow_play"))
        cfg["video"]["allow_download"] = bool(request.form.get("allow_download"))

        cfg["security"]["require_login"] = bool(request.form.get("require_login"))
        cfg["security"]["username"] = request.form.get("username", "admin").strip()
        cfg["security"]["password"] = request.form.get("password", "").strip()

        save_config(cfg)

        return redirect(url_for("settings.database_settings", saved="1"))

    if request.args.get("saved") == "1":
        message = "Đã lưu cấu hình WebServer. Nếu đổi Host/Port, hãy khởi động lại WebServer."

    return render_template(
        "settings/database.html",
        cfg=cfg,
        message=message,
    )


def _parse_storage_roots(raw_value):
    roots = []
    for value in str(raw_value or "").replace(";", "\n").splitlines():
        value = value.strip().strip('"')
        if value:
            roots.append(value)
    return _dedupe_strings(roots)


def _dedupe_strings(values):
    result = []
    seen = set()
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


@settings_bp.route("/test-db")
def test_database():
    try:
        conn = get_connection()
        conn.close()
        return "Kết nối database thành công."
    except Exception as e:
        return f"Kết nối database lỗi: {e}", 500


@settings_bp.route("/startup", methods=["GET", "POST"])
def startup_settings():
    cfg = load_config()
    message = ""
    message_type = "success"

    if request.method == "POST":
        auto_start = bool(request.form.get("auto_start_with_windows"))

        cfg.setdefault("startup", {})
        cfg["startup"]["auto_start_with_windows"] = auto_start
        cfg["startup"]["startup_mode"] = "shortcut"
        cfg["startup"]["start_minimized"] = bool(request.form.get("start_minimized"))

        try:
            if auto_start:
                enable_startup()
                message = "Đã bật tự khởi động ATG_WEBSERVER cùng Windows."
            else:
                disable_startup()
                message = "Đã tắt tự khởi động ATG_WEBSERVER cùng Windows."

            save_config(cfg)

        except Exception as e:
            message = f"Lỗi cài đặt tự khởi động: {e}"
            message_type = "error"

    return render_template(
        "settings/startup.html",
        cfg=cfg,
        startup_enabled=is_startup_enabled(),
        exe_path=exe_path(),
        shortcut_path=shortcut_path(),
        startup_command=startup_command(),
        message=message,
        message_type=message_type,
    )

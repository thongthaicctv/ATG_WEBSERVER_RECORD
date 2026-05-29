# app.py
# -*- coding: utf-8 -*-

import logging
import sys
from pathlib import Path

from flask import Flask
from waitress import serve
from werkzeug.exceptions import HTTPException

from core.config_manager import load_config
from core.auth_manager import ensure_default_users, register_auth_guards
from core.path_utils import get_log_path

from routes.auth_routes import auth_bp
from routes.dashboard_routes import dashboard_bp
from routes.video_routes import video_bp
from routes.video_ecom_routes import video_ecom_bp
from routes.video_wholesale_routes import video_wholesale_bp
from routes.shipping_routes import shipping_bp
from routes.report_routes import report_bp
from routes.settings_routes import settings_bp

from routes.order_routes import order_bp
from services.single_instance import ensure_single_instance
from services.tray_service import start_tray_icon


def setup_logging(app=None):
    log_path = get_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    ))

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    if not any(
        isinstance(existing, logging.FileHandler)
        and getattr(existing, "baseFilename", "") == str(log_path)
        for existing in root_logger.handlers
    ):
        root_logger.addHandler(handler)

    if app is not None:
        app.logger.setLevel(logging.INFO)
        if not any(
            isinstance(existing, logging.FileHandler)
            and getattr(existing, "baseFilename", "") == str(log_path)
            for existing in app.logger.handlers
        ):
            app.logger.addHandler(handler)


def create_app():
    if getattr(sys, "frozen", False):
        resource_root = Path(sys._MEIPASS)
    else:
        resource_root = Path(__file__).resolve().parent

    app = Flask(
        __name__,
        template_folder=str(resource_root / "templates"),
        static_folder=str(resource_root / "static"),
    )
    app.secret_key = "ATG_WEBSERVER_SECRET_KEY"

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(video_bp, url_prefix="/video")
    app.register_blueprint(video_ecom_bp, url_prefix="/video/ecom")
    app.register_blueprint(video_wholesale_bp, url_prefix="/video/wholesale")
    app.register_blueprint(shipping_bp, url_prefix="/shipping")
    app.register_blueprint(report_bp, url_prefix="/reports")
    app.register_blueprint(settings_bp, url_prefix="/settings")

    try:
        ensure_default_users()
    except Exception as e:
        print(f"AUTH INIT WARNING: {e}")

    register_auth_guards(app)
    setup_logging(app)

    @app.errorhandler(Exception)
    def handle_unhandled_exception(exc):
        if isinstance(exc, HTTPException):
            return exc

        app.logger.exception("Unhandled server error", exc_info=exc)
        return f"Lỗi server: {exc}", 500

    return app

if __name__ == "__main__":
    if not ensure_single_instance():
        sys.exit(0)

    setup_logging()
    cfg = load_config()
    app_cfg = cfg.get("app", {})

    host = app_cfg.get("host", "0.0.0.0")
    port = int(app_cfg.get("port", 8088))
    debug = bool(app_cfg.get("debug", False))

    app = create_app()

    print("=" * 60)
    print("ATG_WEBSERVER STARTED")
    print(f"Local:  http://127.0.0.1:{port}")
    print(f"LAN:    http://<IP_MAY_CHAY_WEBSERVER>:{port}")
    print("=" * 60)

    start_tray_icon(
        host=host,
        port=port,
        public_host=app_cfg.get("public_host", "").strip(),
    )

    if debug:
        app.run(host=host, port=port, debug=True)
    else:
        serve(app, host=host, port=port, threads=8)

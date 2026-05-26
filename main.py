# app.py
# -*- coding: utf-8 -*-

from flask import Flask
from waitress import serve

from core.config_manager import load_config

from routes.dashboard_routes import dashboard_bp
from routes.video_routes import video_bp
from routes.video_ecom_routes import video_ecom_bp
from routes.video_wholesale_routes import video_wholesale_bp
from routes.shipping_routes import shipping_bp
from routes.report_routes import report_bp
from routes.settings_routes import settings_bp

from routes.order_routes import order_bp


def create_app():
    app = Flask(__name__)
    app.secret_key = "ATG_WEBSERVER_SECRET_KEY"

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(video_bp, url_prefix="/video")
    app.register_blueprint(video_ecom_bp, url_prefix="/video/ecom")
    app.register_blueprint(video_wholesale_bp, url_prefix="/video/wholesale")
    app.register_blueprint(shipping_bp, url_prefix="/shipping")
    app.register_blueprint(report_bp, url_prefix="/reports")
    app.register_blueprint(settings_bp, url_prefix="/settings")

    return app

if __name__ == "__main__":
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

    if debug:
        app.run(host=host, port=port, debug=True)
    else:
        serve(app, host=host, port=port, threads=8)
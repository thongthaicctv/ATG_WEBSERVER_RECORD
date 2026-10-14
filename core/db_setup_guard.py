# core/db_setup_guard.py
# -*- coding: utf-8 -*-
"""
WEB-DB-FIRST-RUN-SETUP: neu chua co DB config hop le / DB khong ket noi duoc,
chuyen nguoi dung sang trang Setup Database thay vi de WebServer bao loi.
Phai dang ky TRUOC register_auth_guards().
"""

import logging

from flask import redirect, request, url_for

from db.mysql_client import (
    check_db_ready,
    describe_db_error,
    is_db_connection_error,
    mark_db_ready_unknown,
)


logger = logging.getLogger(__name__)

SETUP_EXEMPT_ENDPOINTS = {
    "static",
    "auth.logout",
    "setup.database",
    "setup.test_connection",
    "setup.save",
}

# Link public (share-token) khong chuyen sang trang setup, chi bao 503.
NO_REDIRECT_ENDPOINTS = {
    "video.public_download",
}

DB_UNAVAILABLE_TEXT = "Hệ thống tạm thời không kết nối được Database. Vui lòng thử lại sau."


def register_db_setup_gate(app):
    @app.before_request
    def enforce_db_setup():
        endpoint = request.endpoint
        if not endpoint or endpoint in SETUP_EXEMPT_ENDPOINTS:
            return None

        ready, _message = check_db_ready()
        if ready:
            return None

        if endpoint in NO_REDIRECT_ENDPOINTS:
            return DB_UNAVAILABLE_TEXT, 503

        return redirect(url_for("setup.database"))


def handle_db_connection_error(exc):
    """
    Dung trong errorhandler chung. Tra ve response neu exc la loi ket noi DB,
    nguoc lai tra ve None.
    """
    if not is_db_connection_error(exc):
        return None

    mark_db_ready_unknown()
    logger.warning("DB connection error on %s: %s", request.endpoint, describe_db_error(exc))

    if request.endpoint in NO_REDIRECT_ENDPOINTS:
        return DB_UNAVAILABLE_TEXT, 503
    return redirect(url_for("setup.database"))

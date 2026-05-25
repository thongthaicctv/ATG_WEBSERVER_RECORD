# routes/shipping_routes.py
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, request, redirect, url_for
from db.mysql_client import fetch_all, execute


shipping_bp = Blueprint("shipping", __name__)


@shipping_bp.route("/")
def index():
    keyword = request.args.get("keyword", "").strip()
    status = request.args.get("status", "").strip()

    sql = """
        SELECT
            order_code,
            carrier_code,
            carrier_name,
            tracking_code,
            shipping_status,
            raw_last_status,
            last_shipping_event_at,
            last_handover_at,
            updated_at
        FROM web_index_orders
        WHERE 1=1
    """

    params = []

    if keyword:
        sql += """
            AND (
                order_code LIKE %s
                OR tracking_code LIKE %s
                OR customer_name LIKE %s
                OR customer_phone LIKE %s
            )
        """
        like = f"%{keyword}%"
        params.extend([like, like, like, like])

    if status:
        sql += " AND shipping_status = %s"
        params.append(status)

    sql += " ORDER BY updated_at DESC LIMIT 500"

    try:
        rows = fetch_all(sql, params)
        db_error = ""
    except Exception as e:
        rows = []
        db_error = str(e)

    return render_template(
        "shipping/index.html",
        rows=rows,
        keyword=keyword,
        status=status,
        db_error=db_error,
    )


@shipping_bp.route("/update", methods=["POST"])
def update_shipping():
    order_code = request.form.get("order_code", "").strip()
    carrier_code = request.form.get("carrier_code", "").strip()
    carrier_name = request.form.get("carrier_name", "").strip()
    tracking_code = request.form.get("tracking_code", "").strip()
    shipping_status = request.form.get("shipping_status", "").strip()

    if not order_code:
        return redirect(url_for("shipping.index"))

    try:
        execute(
            """
            INSERT INTO shipments (
                order_code,
                carrier_code,
                carrier_name,
                tracking_code,
                shipping_status,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
                carrier_code = VALUES(carrier_code),
                carrier_name = VALUES(carrier_name),
                tracking_code = VALUES(tracking_code),
                shipping_status = VALUES(shipping_status),
                updated_at = NOW()
            """,
            [
                order_code,
                carrier_code,
                carrier_name,
                tracking_code,
                shipping_status,
            ],
        )
    except Exception:
        pass

    return redirect(url_for("shipping.index", keyword=order_code))
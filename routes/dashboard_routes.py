# routes/dashboard_routes.py
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template
from db.mysql_client import fetch_one


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    stats = {
        "today_orders": 0,
        "today_videos": 0,
        "missing_videos": 0,
        "total_orders": 0
    }

    try:
        row = fetch_one("""
            SELECT COUNT(DISTINCT order_code) AS total
            FROM packing_videos
            WHERE DATE(created_at) = CURDATE()
        """)
        stats["today_orders"] = row["total"] if row else 0

        row = fetch_one("""
            SELECT COUNT(*) AS total
            FROM packing_videos
            WHERE DATE(created_at) = CURDATE()
        """)
        stats["today_videos"] = row["total"] if row else 0

        row = fetch_one("""
            SELECT COUNT(*) AS total
            FROM packing_videos
            WHERE file_path IS NULL
               OR file_path = ''
               OR file_size IS NULL
               OR file_size = 0
        """)
        stats["missing_videos"] = row["total"] if row else 0

        row = fetch_one("""
            SELECT COUNT(*) AS total
            FROM web_index_orders
        """)
        stats["total_orders"] = row["total"] if row else 0

        db_error = ""

    except Exception as e:
        db_error = str(e)

    return render_template(
        "dashboard.html",
        stats=stats,
        db_error=db_error
    )
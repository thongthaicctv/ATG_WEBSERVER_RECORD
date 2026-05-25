# routes/report_routes.py
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, request
from db.mysql_client import fetch_all


report_bp = Blueprint("reports", __name__)


@report_bp.route("/")
def index():
    report_type = request.args.get("type", "employee").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    rows = []
    db_error = ""

    try:
        if report_type == "missing_video":
            sql = """
                SELECT
                    id,
                    order_code,
                    camera_id,
                    camera_name,
                    file_path,
                    file_size,
                    duration_seconds,
                    created_at
                FROM packing_videos
                WHERE file_path IS NULL
                   OR file_path = ''
                   OR file_size IS NULL
                   OR file_size = 0
                ORDER BY created_at DESC
                LIMIT 1000
            """
            rows = fetch_all(sql)

        else:
            sql = """
                SELECT
                    employee_code,
                    employee_name,
                    DATE(start_time) AS work_date,
                    COUNT(DISTINCT order_code) AS total_orders,
                    COUNT(*) AS total_videos,
                    SUM(duration_seconds) AS total_duration_seconds
                FROM packing_videos
                WHERE start_time IS NOT NULL
            """

            params = []

            if date_from:
                sql += " AND DATE(start_time) >= %s"
                params.append(date_from)

            if date_to:
                sql += " AND DATE(start_time) <= %s"
                params.append(date_to)

            sql += """
                GROUP BY employee_code, employee_name, DATE(start_time)
                ORDER BY work_date DESC, total_orders DESC
                LIMIT 1000
            """

            rows = fetch_all(sql, params)

    except Exception as e:
        db_error = str(e)

    return render_template(
        "reports/index.html",
        rows=rows,
        report_type=report_type,
        date_from=date_from,
        date_to=date_to,
        db_error=db_error,
    )
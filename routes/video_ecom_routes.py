# routes/video_ecom_routes.py
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, request
from db.mysql_client import fetch_all


video_ecom_bp = Blueprint("video_ecom", __name__)


@video_ecom_bp.route("/")
def index():
    keyword = request.args.get("keyword", "").strip()
    employee = request.args.get("employee", "").strip()
    camera_id = request.args.get("camera_id", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    sql = """
        SELECT
            id,
            order_code,
            box_code,
            scanner_id,
            camera_id,
            camera_name,
            file_path,
            file_size,
            duration_seconds,
            start_time,
            end_time,
            employee_code,
            employee_name,
            result,
            created_at
        FROM ecom_packing_videos
        WHERE 1=1
    """

    params = []

    if keyword:
        sql += " AND order_code LIKE %s"
        params.append(f"%{keyword}%")

    if employee:
        sql += " AND (employee_code LIKE %s OR employee_name LIKE %s)"
        params.extend([f"%{employee}%", f"%{employee}%"])

    if camera_id:
        sql += " AND camera_id = %s"
        params.append(camera_id)

    if date_from:
        sql += " AND DATE(start_time) >= %s"
        params.append(date_from)

    if date_to:
        sql += " AND DATE(start_time) <= %s"
        params.append(date_to)

    sql += " ORDER BY created_at DESC LIMIT 500"

    try:
        videos = fetch_all(sql, params)
        db_error = ""
    except Exception as e:
        videos = []
        db_error = str(e)

    return render_template(
        "video/ecom.html",
        videos=videos,
        keyword=keyword,
        employee=employee,
        camera_id=camera_id,
        date_from=date_from,
        date_to=date_to,
        db_error=db_error,
    )

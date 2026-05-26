# routes/report_routes.py
# -*- coding: utf-8 -*-

from pathlib import Path
from datetime import datetime

from flask import Blueprint, render_template, request, send_file

from db.mysql_client import fetch_all
from services.export_excel_service import (
    export_employee_report,
    export_video_report,
    export_missing_video_report,
    export_order_status_report,
)


report_bp = Blueprint("reports", __name__)


def get_employee_report(date_from="", date_to=""):
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
        LIMIT 5000
    """

    return fetch_all(sql, params)


def get_video_report(date_from="", date_to="", session_type=""):
    sql = """
        SELECT
            id,
            order_code,
            box_code,
            session_type,
            video_type,
            scanner_id,
            camera_id,
            camera_name,
            file_path,
            file_name,
            file_size,
            duration_seconds,
            start_time,
            end_time,
            employee_code,
            employee_name,
            result,
            created_at
        FROM packing_videos
        WHERE 1=1
    """

    params = []

    if date_from:
        sql += " AND DATE(start_time) >= %s"
        params.append(date_from)

    if date_to:
        sql += " AND DATE(start_time) <= %s"
        params.append(date_to)

    if session_type:
        sql += " AND session_type = %s"
        params.append(session_type)

    sql += " ORDER BY start_time DESC, created_at DESC LIMIT 10000"

    return fetch_all(sql, params)


def get_missing_video_report():
    sql = """
        SELECT
            id,
            order_code,
            camera_id,
            camera_name,
            file_path,
            file_name,
            file_size,
            duration_seconds,
            created_at
        FROM packing_videos
        WHERE file_path IS NULL
           OR file_path = ''
           OR file_size IS NULL
           OR file_size = 0
        ORDER BY created_at DESC
        LIMIT 5000
    """

    return fetch_all(sql)


def get_order_status_report(date_from="", date_to="", packing_status="", shipping_status=""):
    sql = """
        SELECT
            order_code,
            order_type,
            customer_name,
            customer_phone,
            video_count,
            packing_status,
            conveyor_status,
            shipping_status,
            tracking_code,
            updated_at
        FROM web_index_orders
        WHERE 1=1
    """

    params = []

    if date_from:
        sql += " AND DATE(updated_at) >= %s"
        params.append(date_from)

    if date_to:
        sql += " AND DATE(updated_at) <= %s"
        params.append(date_to)

    if packing_status:
        sql += " AND packing_status = %s"
        params.append(packing_status)

    if shipping_status:
        sql += " AND shipping_status = %s"
        params.append(shipping_status)

    sql += " ORDER BY updated_at DESC LIMIT 5000"

    return fetch_all(sql, params)


@report_bp.route("/")
def index():
    report_type = request.args.get("type", "employee").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    session_type = request.args.get("session_type", "").strip()
    packing_status = request.args.get("packing_status", "").strip()
    shipping_status = request.args.get("shipping_status", "").strip()

    rows = []
    db_error = ""

    try:
        if report_type == "missing_video":
            rows = get_missing_video_report()

        elif report_type == "video":
            rows = get_video_report(date_from, date_to, session_type)

        elif report_type == "order_status":
            rows = get_order_status_report(date_from, date_to, packing_status, shipping_status)

        else:
            rows = get_employee_report(date_from, date_to)

    except Exception as e:
        db_error = str(e)

    return render_template(
        "reports/index.html",
        rows=rows,
        report_type=report_type,
        date_from=date_from,
        date_to=date_to,
        session_type=session_type,
        packing_status=packing_status,
        shipping_status=shipping_status,
        db_error=db_error,
    )


@report_bp.route("/export")
def export_report():
    report_type = request.args.get("type", "employee").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    session_type = request.args.get("session_type", "").strip()
    packing_status = request.args.get("packing_status", "").strip()
    shipping_status = request.args.get("shipping_status", "").strip()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if report_type == "missing_video":
        rows = get_missing_video_report()
        output = export_missing_video_report(rows)
        filename = f"ATG_video_loi_thieu_file_{timestamp}.xlsx"

    elif report_type == "video":
        rows = get_video_report(date_from, date_to, session_type)
        output = export_video_report(rows, date_from, date_to)
        filename = f"ATG_bao_cao_video_{timestamp}.xlsx"

    elif report_type == "order_status":
        rows = get_order_status_report(date_from, date_to, packing_status, shipping_status)
        output = export_order_status_report(rows, date_from, date_to)
        filename = f"ATG_bao_cao_trang_thai_don_{timestamp}.xlsx"

    else:
        rows = get_employee_report(date_from, date_to)
        output = export_employee_report(rows, date_from, date_to)
        filename = f"ATG_bao_cao_nhan_vien_{timestamp}.xlsx"

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@report_bp.route("/missing-files")
def missing_files():
    rows = []
    db_error = ""

    try:
        videos = fetch_all(
            """
            SELECT
                id,
                order_code,
                camera_id,
                camera_name,
                file_path,
                file_name,
                file_size,
                duration_seconds,
                created_at
            FROM packing_videos
            WHERE file_path IS NOT NULL
              AND file_path <> ''
            ORDER BY created_at DESC
            LIMIT 2000
            """
        )

        for v in videos:
            path = Path(v.get("file_path") or "")
            if not path.exists():
                rows.append(v)

    except Exception as e:
        db_error = str(e)

    return render_template(
        "reports/missing_files.html",
        rows=rows,
        db_error=db_error,
    )


@report_bp.route("/missing-files/export")
def export_missing_files():
    rows = []

    videos = fetch_all(
        """
        SELECT
            id,
            order_code,
            camera_id,
            camera_name,
            file_path,
            file_name,
            file_size,
            duration_seconds,
            created_at
        FROM packing_videos
        WHERE file_path IS NOT NULL
          AND file_path <> ''
        ORDER BY created_at DESC
        LIMIT 5000
        """
    )

    for v in videos:
        path = Path(v.get("file_path") or "")
        if not path.exists():
            rows.append(v)

    output = export_missing_video_report(rows)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ATG_video_mat_file_that_{timestamp}.xlsx"

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
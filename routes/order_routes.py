# routes/order_routes.py
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, abort

from core.video_path_resolver import video_file_exists
from db.mysql_client import fetch_one, fetch_all


order_bp = Blueprint("orders", __name__)


def file_exists(video):
    file_path = video.get("file_path") if isinstance(video, dict) else video
    if not file_path:
        return False

    try:
        return video_file_exists(
            file_path,
            storage_code=video.get("storage_code") if isinstance(video, dict) else None,
            relative_path=video.get("relative_path") if isinstance(video, dict) else None,
        )
    except Exception:
        return False


@order_bp.route("/order/<path:order_code>")
def order_detail(order_code):
    order = None
    sessions = []
    videos = []
    db_error = ""

    try:
        order = fetch_one(
            """
            SELECT *
            FROM orders
            WHERE order_code = %s
            LIMIT 1
            """,
            [order_code],
        )

        sessions = fetch_all(
            """
            SELECT *
            FROM packing_sessions
            WHERE order_code = %s
            ORDER BY start_time DESC
            """,
            [order_code],
        )

        videos = fetch_all(
            """
            SELECT
                id,
                order_code,
                packing_session_id,
                box_code,
                session_type,
                video_type,
                scanner_id,
                camera_id,
                camera_name,
                storage_code,
                file_path,
                relative_path,
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
            WHERE order_code = %s
            ORDER BY start_time DESC, camera_id ASC
            """,
            [order_code],
        )

        for v in videos:
            v["file_exists"] = file_exists(v)

    except Exception as e:
        db_error = str(e)

    if not order and not videos and not db_error:
        abort(404, "Không tìm thấy đơn hàng.")

    return render_template(
        "orders/detail.html",
        order_code=order_code,
        order=order,
        sessions=sessions,
        videos=videos,
        db_error=db_error,
    )

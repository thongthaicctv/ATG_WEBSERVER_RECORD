# routes/video_routes.py
# -*- coding: utf-8 -*-

import mimetypes
from pathlib import Path



from core.config_manager import load_config
from db.mysql_client import fetch_one

from flask import Blueprint, send_file, abort, jsonify, request


video_bp = Blueprint("video", __name__)


@video_bp.route("/play/<int:video_id>")
def play_video(video_id):
    cfg = load_config()

    if not cfg.get("video", {}).get("allow_play", True):
        abort(403, "Chức năng xem video đang bị tắt.")

    video = fetch_one(
        """
        SELECT id, file_path, file_name
        FROM packing_videos
        WHERE id = %s
        LIMIT 1
        """,
        [video_id],
    )

    if not video:
        abort(404, "Không tìm thấy video trong database.")

    file_path = video.get("file_path")
    if not file_path:
        abort(404, "Video chưa có file_path.")

    path = Path(file_path)

    if not path.exists():
        abort(404, f"File video không tồn tại: {file_path}")

    mime_type = mimetypes.guess_type(path.name)[0] or "video/x-matroska"

    return send_file(
        path,
        mimetype=mime_type,
        as_attachment=False,
        conditional=True,
    )


@video_bp.route("/download/<int:video_id>")
def download_video(video_id):
    cfg = load_config()

    if not cfg.get("video", {}).get("allow_download", True):
        abort(403, "Chức năng tải video đang bị tắt.")

    video = fetch_one(
        """
        SELECT id, file_path, file_name
        FROM packing_videos
        WHERE id = %s
        LIMIT 1
        """,
        [video_id],
    )

    if not video:
        abort(404, "Không tìm thấy video trong database.")

    file_path = video.get("file_path")
    if not file_path:
        abort(404, "Video chưa có file_path.")

    path = Path(file_path)

    if not path.exists():
        abort(404, f"File video không tồn tại: {file_path}")

    return send_file(
        path,
        as_attachment=True,
        download_name=video.get("file_name") or path.name,
    )

@video_bp.route("/link/<int:video_id>")
def get_video_link(video_id):
    cfg = load_config()
    app_cfg = cfg.get("app", {})

    public_host = app_cfg.get("public_host", "").strip()
    port = int(app_cfg.get("port", 8088))

    if public_host:
        public_host = public_host.replace("http://", "").replace("https://", "").strip("/")
        link = f"http://{public_host}:{port}/video/play/{video_id}"
    else:
        link = request.host_url.rstrip("/") + f"/video/play/{video_id}"

    return jsonify({
        "ok": True,
        "video_id": video_id,
        "link": link
    })
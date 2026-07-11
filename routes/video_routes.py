# routes/video_routes.py
# -*- coding: utf-8 -*-

import hashlib
import hmac
import mimetypes
from urllib.parse import urlparse

from flask import Blueprint, Response, abort, jsonify, render_template, request, send_file, stream_with_context, url_for

from core.config_manager import load_config
from core.video_path_resolver import resolve_video_path, video_path_candidates
from db.mysql_client import fetch_one
from services.video_stream_service import (
    is_browser_native_video,
    is_ffmpeg_view_video,
    iter_ffmpeg_mp4,
    locate_ffmpeg,
    normalize_stream_mode,
)


video_bp = Blueprint("video", __name__)
SHARE_TOKEN_VERSION = "v1"


def _get_video_or_404(video_id):
    video = fetch_one(
        """
        SELECT *
        FROM packing_videos
        WHERE id = %s
        LIMIT 1
        """,
        [video_id],
    )

    if not video:
        abort(404, "Không tìm thấy video trong database.")

    if not video.get("file_path"):
        abort(404, "Video chưa có file_path.")

    return video


def _resolve_existing_path_or_404(video, cfg):
    file_path = video.get("file_path")
    path = resolve_video_path(
        file_path,
        cfg,
        storage_code=video.get("storage_code"),
        relative_path=video.get("relative_path"),
    )
    if path.exists():
        return path

    checked = "; ".join(
        str(candidate)
        for candidate in video_path_candidates(
            file_path,
            cfg,
            storage_code=video.get("storage_code"),
            relative_path=video.get("relative_path"),
        )
    )
    abort(404, f"File video không tồn tại: {file_path}. Đã kiểm tra: {checked}")


def _download_name(video, path):
    return video.get("file_name") or path.name


def _share_secret(cfg):
    security_cfg = cfg.get("security", {}) if isinstance(cfg, dict) else {}
    database_cfg = cfg.get("database", {}) if isinstance(cfg, dict) else {}
    raw = "|".join(
        [
            "ATG_WEBSERVER_PUBLIC_DOWNLOAD",
            str(security_cfg.get("password") or ""),
            str(database_cfg.get("password") or ""),
            str(database_cfg.get("database") or ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).digest()


def _share_payload(video, path):
    return "|".join(
        [
            SHARE_TOKEN_VERSION,
            str(video.get("id") or ""),
            str(video.get("file_path") or ""),
            str(video.get("relative_path") or ""),
            str(video.get("storage_code") or ""),
            str(video.get("file_size") or ""),
            path.name,
        ]
    )


def _share_token(video, path, cfg):
    digest = hmac.new(
        _share_secret(cfg),
        _share_payload(video, path).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{SHARE_TOKEN_VERSION}-{digest[:32]}"


def _is_valid_share_token(token, video, path, cfg):
    expected = _share_token(video, path, cfg)
    return hmac.compare_digest(str(token or ""), expected)


def _public_base_url(cfg):
    app_cfg = cfg.get("app", {}) if isinstance(cfg, dict) else {}
    public_host = str(app_cfg.get("public_host") or "").strip()
    port = int(app_cfg.get("port", 8088))

    if not public_host:
        return request.host_url.rstrip("/")

    if "://" not in public_host:
        public_host = f"http://{public_host}"

    parsed = urlparse(public_host)
    scheme = parsed.scheme or "http"
    host = parsed.netloc or parsed.path
    host = host.strip("/")

    if ":" not in host:
        host = f"{host}:{port}"

    return f"{scheme}://{host}"


@video_bp.route("/play/<int:video_id>")
def play_video(video_id):
    cfg = load_config()

    if not cfg.get("video", {}).get("allow_play", True):
        abort(403, "Chức năng xem video đang bị tắt.")

    video = _get_video_or_404(video_id)
    path = _resolve_existing_path_or_404(video, cfg)
    native_play = is_browser_native_video(path)
    ffmpeg_path = locate_ffmpeg(cfg)
    can_ffmpeg = bool(ffmpeg_path)
    requested_mode = str(request.args.get("mode") or "").strip().lower()

    if requested_mode in {"remux", "transcode"} and can_ffmpeg:
        primary_mode = normalize_stream_mode(requested_mode)
        primary_url = url_for("video.stream_video", video_id=video_id, mode=primary_mode)
    elif requested_mode == "raw" or native_play:
        primary_url = url_for("video.raw_video", video_id=video_id)
        primary_mode = "raw"
    else:
        primary_mode = normalize_stream_mode(requested_mode)
        primary_url = (
            url_for("video.stream_video", video_id=video_id, mode=primary_mode)
            if can_ffmpeg
            else url_for("video.raw_video", video_id=video_id)
        )

    return render_template(
        "video/player.html",
        video=video,
        path=path,
        file_name=video.get("file_name") or path.name,
        native_play=native_play,
        ffmpeg_view=is_ffmpeg_view_video(path),
        can_ffmpeg=can_ffmpeg,
        primary_url=primary_url,
        primary_mode=primary_mode,
        raw_url=url_for("video.raw_video", video_id=video_id),
        remux_url=url_for("video.play_video", video_id=video_id, mode="remux"),
        transcode_url=url_for("video.play_video", video_id=video_id, mode="transcode"),
        download_url=url_for("video.download_video", video_id=video_id),
        share_link_url=url_for("video.share_download_link", video_id=video_id),
        ffmpeg_path=ffmpeg_path,
    )


@video_bp.route("/raw/<int:video_id>")
def raw_video(video_id):
    cfg = load_config()

    if not cfg.get("video", {}).get("allow_play", True):
        abort(403, "Chức năng xem video đang bị tắt.")

    video = _get_video_or_404(video_id)
    path = _resolve_existing_path_or_404(video, cfg)
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    return send_file(
        path,
        mimetype=mime_type,
        as_attachment=False,
        conditional=True,
    )


@video_bp.route("/stream/<int:video_id>")
def stream_video(video_id):
    cfg = load_config()

    if not cfg.get("video", {}).get("allow_play", True):
        abort(403, "Chức năng xem video đang bị tắt.")

    video = _get_video_or_404(video_id)
    path = _resolve_existing_path_or_404(video, cfg)
    ffmpeg_path = locate_ffmpeg(cfg)
    if not ffmpeg_path:
        abort(500, "Chưa tìm thấy ffmpeg.exe để xem trực tiếp định dạng này.")

    mode = normalize_stream_mode(request.args.get("mode", "remux"))
    headers = {
        "Cache-Control": "no-store",
        "X-Accel-Buffering": "no",
    }

    return Response(
        stream_with_context(iter_ffmpeg_mp4(ffmpeg_path, path, mode=mode)),
        mimetype="video/mp4",
        headers=headers,
        direct_passthrough=True,
    )


@video_bp.route("/download/<int:video_id>")
def download_video(video_id):
    cfg = load_config()

    if not cfg.get("video", {}).get("allow_download", True):
        abort(403, "Chức năng tải video đang bị tắt.")

    video = _get_video_or_404(video_id)
    path = _resolve_existing_path_or_404(video, cfg)

    return send_file(
        path,
        as_attachment=True,
        download_name=_download_name(video, path),
    )


@video_bp.route("/share-link/<int:video_id>")
def share_download_link(video_id):
    cfg = load_config()
    video = _get_video_or_404(video_id)
    path = _resolve_existing_path_or_404(video, cfg)
    token = _share_token(video, path, cfg)
    link = f"{_public_base_url(cfg)}{url_for('video.public_download', video_id=video_id, token=token)}"

    return jsonify(
        {
            "ok": True,
            "video_id": video_id,
            "link": link,
            "download_name": _download_name(video, path),
        }
    )


@video_bp.route("/public-download/<int:video_id>/<token>")
def public_download(video_id, token):
    cfg = load_config()

    if not cfg.get("video", {}).get("allow_download", True):
        abort(403, "Chức năng tải video đang bị tắt.")

    video = _get_video_or_404(video_id)
    path = _resolve_existing_path_or_404(video, cfg)
    if not _is_valid_share_token(token, video, path, cfg):
        abort(403, "Link tải không hợp lệ hoặc đã hết hiệu lực.")

    return send_file(
        path,
        as_attachment=True,
        download_name=_download_name(video, path),
        conditional=True,
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
        "link": link,
    })

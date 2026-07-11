# services/video_stream_service.py
# -*- coding: utf-8 -*-

import os
import logging
import shutil
import subprocess
from pathlib import Path

from core.path_utils import app_root


BROWSER_NATIVE_EXTENSIONS = {
    ".mp4",
    ".m4v",
    ".mov",
    ".webm",
    ".ogv",
    ".ogg",
}

FFMPEG_VIEW_EXTENSIONS = {
    ".mkv",
    ".ts",
    ".mts",
    ".m2ts",
    ".avi",
    ".flv",
    ".wmv",
    ".mpg",
    ".mpeg",
    ".3gp",
    ".dav",
}

STREAM_MODES = {"remux", "transcode"}


def is_browser_native_video(path):
    return Path(path).suffix.lower() in BROWSER_NATIVE_EXTENSIONS


def is_ffmpeg_view_video(path):
    return Path(path).suffix.lower() in FFMPEG_VIEW_EXTENSIONS


def normalize_stream_mode(value):
    value = str(value or "").strip().lower()
    if value in STREAM_MODES:
        return value
    return "remux"


def locate_ffmpeg(cfg=None):
    video_cfg = cfg.get("video", {}) if isinstance(cfg, dict) else {}
    configured = str(video_cfg.get("ffmpeg_path") or "").strip().strip('"')
    env_path = os.environ.get("FFMPEG_PATH", "").strip().strip('"')
    path_ffmpeg = shutil.which("ffmpeg")

    candidates = [
        configured,
        env_path,
        app_root() / "bin" / "ffmpeg.exe",
        app_root() / "ffmpeg" / "bin" / "ffmpeg.exe",
        Path.cwd() / "bin" / "ffmpeg.exe",
        Path(r"D:\PYTHON-TCR\bin\ffmpeg.exe"),
        Path(r"D:\PYTHON-TCR\1. EXE\ATG_AI_SYSTEM_RECORD\bin\ffmpeg.exe"),
        Path(r"D:\PYTHON-TCR\1. EXE\ATG_AI_SYSTEM_RECORD\ffmpeg\bin\ffmpeg.exe"),
        path_ffmpeg or "",
    ]

    for candidate in _dedupe_paths(candidates):
        if candidate and candidate.exists():
            return str(candidate)

    return ""


def ffmpeg_stream_command(ffmpeg_path, input_path, mode="remux"):
    mode = normalize_stream_mode(mode)
    base = [
        ffmpeg_path,
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-fflags",
        "+genpts",
        "-probesize",
        "32M",
        "-analyzeduration",
        "10M",
        "-i",
        str(input_path),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
    ]

    if mode == "transcode":
        base.extend(
            [
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-tune",
                "zerolatency",
                "-crf",
                "28",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
            ]
        )
    else:
        base.extend(
            [
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
            ]
        )

    base.extend(
        [
            "-movflags",
            "frag_keyframe+empty_moov+default_base_moof",
            "-f",
            "mp4",
            "pipe:1",
        ]
    )
    return base


def iter_ffmpeg_mp4(ffmpeg_path, input_path, mode="remux", chunk_size=1024 * 256):
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    process = subprocess.Popen(
        ffmpeg_stream_command(ffmpeg_path, input_path, mode=mode),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
    )

    total_bytes = 0
    try:
        while True:
            chunk = process.stdout.read(chunk_size)
            if not chunk:
                break
            total_bytes += len(chunk)
            yield chunk
    finally:
        try:
            if process.poll() is None:
                process.terminate()
        except Exception:
            pass

        try:
            process.wait(timeout=2)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass

        try:
            stderr = process.stderr.read() if process.stderr else b""
            if stderr and total_bytes == 0:
                logging.getLogger(__name__).error(
                    "ffmpeg video stream failed mode=%s file=%s error=%s",
                    mode,
                    input_path,
                    stderr.decode("utf-8", errors="replace").strip(),
                )
        except Exception:
            pass


def _dedupe_paths(values):
    result = []
    seen = set()
    for value in values:
        if not value:
            continue

        path = Path(value)
        key = str(path).lower()
        if key in seen:
            continue

        seen.add(key)
        result.append(path)

    return result

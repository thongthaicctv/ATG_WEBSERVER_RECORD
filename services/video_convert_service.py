# services/video_convert_service.py
# -*- coding: utf-8 -*-

import hashlib
import os
import subprocess
from pathlib import Path

from core.path_utils import app_root
from services.video_stream_service import locate_ffmpeg


def get_cache_dir(cfg) -> Path:
    download_cfg = cfg.get("download", {}) if isinstance(cfg, dict) else {}
    cache_dir = download_cfg.get("mp4_cache_dir", "web_cache/mp4")

    path = Path(cache_dir)

    if not path.is_absolute():
        path = app_root() / path

    path.mkdir(parents=True, exist_ok=True)
    return path


def make_safe_mp4_name(source_path: str, video_id: int) -> str:
    source_text = str(source_path)
    digest = hashlib.md5(source_text.encode("utf-8")).hexdigest()[:10]
    stem = Path(source_text).stem

    safe_stem = "".join(
        c if c.isalnum() or c in ("-", "_") else "_"
        for c in stem
    )

    return f"{video_id}_{safe_stem}_{digest}.mp4"


def get_mp4_cache_path(source_path: str, video_id: int, cfg) -> Path:
    return get_cache_dir(cfg) / make_safe_mp4_name(source_path, video_id)


def convert_to_mp4(source_path: str, video_id: int, cfg) -> Path:
    source = Path(source_path)

    if not source.exists():
        raise FileNotFoundError(f"Không tìm thấy file gốc: {source_path}")

    target = get_mp4_cache_path(source_path, video_id, cfg)

    if target.exists() and target.stat().st_size > 0:
        return target

    ffmpeg_path = locate_ffmpeg(cfg)
    if not ffmpeg_path:
        raise RuntimeError("Chưa tìm thấy ffmpeg.exe để chuyển MP4.")

    download_cfg = cfg.get("download", {}) if isinstance(cfg, dict) else {}
    timeout = int(download_cfg.get("convert_timeout_seconds", 600))
    mode = str(download_cfg.get("mp4_mode", "copy_first")).strip().lower()

    temp_target = target.with_suffix(".tmp.mp4")

    if temp_target.exists():
        try:
            temp_target.unlink()
        except Exception:
            pass

    if mode == "copy_first":
        ok = _try_remux_copy(ffmpeg_path, source, temp_target, timeout)
        if ok:
            temp_target.replace(target)
            return target

    _encode_h264(ffmpeg_path, source, temp_target, timeout)

    temp_target.replace(target)
    return target


def _try_remux_copy(ffmpeg_path, source: Path, target: Path, timeout: int) -> bool:
    cmd = [
        ffmpeg_path,
        "-y",
        "-i", str(source),
        "-c", "copy",
        "-movflags", "+faststart",
        str(target),
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            creationflags=_creation_flags(),
        )

        return result.returncode == 0 and target.exists() and target.stat().st_size > 0

    except Exception:
        return False


def _encode_h264(ffmpeg_path, source: Path, target: Path, timeout: int):
    cmd = [
        ffmpeg_path,
        "-y",
        "-i", str(source),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-c:a", "aac",
        "-movflags", "+faststart",
        str(target),
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        creationflags=_creation_flags(),
    )

    if result.returncode != 0:
        err = result.stderr.decode("utf-8", errors="ignore")
        raise RuntimeError(f"Convert MP4 lỗi: {err}")

    if not target.exists() or target.stat().st_size <= 0:
        raise RuntimeError("Convert MP4 lỗi: file output rỗng.")


def _creation_flags():
    if os.name == "nt":
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0
# core/video_path_resolver.py
# -*- coding: utf-8 -*-

import string
from functools import lru_cache
from pathlib import Path


COMMON_VIDEO_ROOT_NAMES = (
    "VIDEO",
    "DEBUG",
    "ATG_DataBackup",
    "ATG_Recorder",
    "ATG_RECORD",
    "ATG_VIDEO",
)


def video_path_candidates(file_path, cfg=None, storage_code=None, relative_path=None):
    lookup_paths = _lookup_paths(file_path, relative_path)
    if not lookup_paths:
        return []

    if cfg is None:
        from core.config_manager import load_config

        cfg = load_config()

    candidates = []
    absolute_paths = [path for path in lookup_paths if path.is_absolute()]
    relative_paths = [path for path in lookup_paths if not path.is_absolute()]

    candidates.extend(absolute_paths)

    roots = _configured_roots(cfg, storage_code)
    for root in roots:
        for path in relative_paths:
            candidates.append(root / path)

        for path in absolute_paths:
            guessed = _portable_relative_parts(path)
            for rel_path in guessed:
                candidates.append(root / rel_path)

    for path in relative_paths:
        candidates.append(Path.cwd() / path)

        from core.path_utils import app_root

        candidates.append(app_root() / path)

    return _dedupe_paths(candidates)


def resolve_video_path(file_path, cfg=None, storage_code=None, relative_path=None):
    candidates = video_path_candidates(file_path, cfg, storage_code, relative_path)
    for path in candidates:
        try:
            if path.exists():
                return path
        except OSError:
            continue

    return candidates[0] if candidates else Path(str(file_path or relative_path or ""))


def video_file_exists(file_path, cfg=None, storage_code=None, relative_path=None):
    candidates = video_path_candidates(file_path, cfg, storage_code, relative_path)
    for path in candidates:
        try:
            if path.exists():
                return True
        except OSError:
            continue
    return False


def _lookup_paths(file_path, relative_path=None):
    paths = []
    for value in (relative_path, file_path):
        value = str(value or "").strip()
        if value:
            paths.append(Path(value))
    return _dedupe_paths(paths)


def _configured_roots(cfg, storage_code=None):
    roots = []
    video_cfg = cfg.get("video", {}) if isinstance(cfg, dict) else {}
    storage_root = str(video_cfg.get("storage_root") or "").strip()

    if storage_root:
        roots.append(Path(storage_root))

    storage_rows = _storage_location_rows()
    if storage_code:
        for row_code, base_path in storage_rows:
            if row_code == storage_code and base_path:
                roots.append(Path(base_path))

    for _row_code, base_path in storage_rows:
        if base_path:
            roots.append(Path(base_path))

    roots.extend(_common_windows_video_roots())
    return _dedupe_paths(roots)


@lru_cache(maxsize=1)
def _storage_location_rows():
    try:
        from db.mysql_client import fetch_all

        rows = fetch_all(
            """
            SELECT storage_code, base_path
            FROM storage_locations
            WHERE base_path IS NOT NULL
              AND base_path <> ''
            ORDER BY storage_code ASC
            """
        )
    except Exception:
        return []

    return [
        (str(row.get("storage_code") or "").strip(), str(row.get("base_path") or "").strip())
        for row in rows
    ]


def _common_windows_video_roots():
    roots = []
    for letter in string.ascii_uppercase:
        drive = Path(f"{letter}:\\")
        if not drive.exists():
            continue

        for folder_name in COMMON_VIDEO_ROOT_NAMES:
            roots.append(drive / folder_name)

    return roots


def _portable_relative_parts(path):
    parts = path.parts
    guessed = []

    if len(parts) >= 2:
        guessed.append(Path(*parts[-2:]))
    if len(parts) >= 3:
        guessed.append(Path(*parts[-3:]))
    if path.name:
        guessed.append(Path(path.name))

    return _dedupe_paths(guessed)


def _dedupe_paths(paths):
    result = []
    seen = set()
    for path in paths:
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result

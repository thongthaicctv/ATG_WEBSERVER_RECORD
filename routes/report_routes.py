# routes/report_routes.py
# -*- coding: utf-8 -*-

import re
from collections import defaultdict
from datetime import datetime

from flask import Blueprint, render_template, request, send_file

from db.mysql_client import fetch_all
from core.video_path_resolver import video_file_exists
from services.export_excel_service import (
    export_employee_report,
    export_missing_video_report,
    export_order_status_report,
    export_order_status_split_report,
    export_video_report,
)


report_bp = Blueprint("reports", __name__)


def _date_filter_sql(column_expr, date_from="", date_to=""):
    sql = ""
    params = []

    if date_from:
        sql += f" AND DATE({column_expr}) >= %s"
        params.append(date_from)

    if date_to:
        sql += f" AND DATE({column_expr}) <= %s"
        params.append(date_to)

    return sql, params


def _get_employee_name_map():
    employee_names = {}

    for table in ("employees", "users"):
        try:
            rows = fetch_all(
                f"""
                SELECT employee_code, employee_name
                FROM {table}
                WHERE employee_code IS NOT NULL
                  AND employee_code <> ''
                  AND employee_name IS NOT NULL
                  AND employee_name <> ''
                """
            )
        except Exception:
            continue

        for row in rows:
            employee_names.setdefault(row.get("employee_code"), row.get("employee_name"))

    for table in (
        "packing_videos",
        "packing_sessions",
        "wholesale_box_items",
        "packing_small_packages",
        "wholesale_handover_checks",
    ):
        try:
            rows = fetch_all(
                f"""
                SELECT employee_code, employee_name
                FROM {table}
                WHERE employee_code IS NOT NULL
                  AND employee_code <> ''
                  AND employee_name IS NOT NULL
                  AND employee_name <> ''
                """
            )
        except Exception:
            continue

        for row in rows:
            employee_names.setdefault(row.get("employee_code"), row.get("employee_name"))

    return employee_names


def _extract_employee_code_from_filename(file_name):
    if not file_name:
        return ""

    match = re.search(r"_([^_]+)_\d{8}_\d{6}(?:\.[^.]+)?$", file_name)
    if not match:
        return ""

    return (match.group(1) or "").strip()


def _employee_code_from_row(row):
    return (
        (row.get("employee_code") or "").strip()
        or _extract_employee_code_from_filename(row.get("file_name"))
    )


def _format_employee(employee_code="", employee_name="", employee_names=None, na_name=True):
    employee_code = (employee_code or "").strip()
    employee_name = (employee_name or "").strip()

    if employee_code and not employee_name and employee_names:
        employee_name = employee_names.get(employee_code, "")

    if employee_code.upper() == "NA":
        return "N/A" if na_name else "NA"

    if employee_code and employee_name:
        return f"{employee_code}: {employee_name}"

    return employee_name or employee_code


def _append_unique(target, key, value):
    if not key or not value:
        return

    values = target.setdefault(key, [])
    value = str(value).strip()
    if value.upper() in {"NA", "N/A"}:
        if not values:
            values.append(value)
        return

    values[:] = [
        existing
        for existing in values
        if str(existing).strip().upper() not in {"NA", "N/A"}
    ]

    value_key = value.split(":", 1)[0].strip()

    for index, existing in enumerate(values):
        existing_key = str(existing).split(":", 1)[0].strip()
        if existing_key == value_key:
            if ":" in value and ":" not in str(existing):
                values[index] = value
            return

    values.append(value)


def _packing_status_label(row, order_type):
    status = (row.get("packing_status") or "").upper()
    has_video = (row.get("video_count") or 0) > 0

    if order_type == "ecom" and (has_video or status in {"COMPLETED", "PACKED", "DONE"}):
        return "Hoàn Thành"

    if order_type == "wholesale" and (has_video or status in {"COMPLETED", "PACKED", "DONE"}):
        return "Hoàn thành"

    return row.get("packing_status")


def _order_type_label(order_type):
    if order_type == "wholesale":
        return "Bán sỉ"
    return "ECOM"


def _is_wholesale_text(value):
    text = (value or "").upper()
    return any(token in text for token in ("WHOLESALE", "WHOLES", "BAN SI", "BÁN SỈ", "SI", "SỈ"))


def _is_ecom_text(value):
    return "ECOM" in (value or "").upper()


def _strip_workflow_prefix(order_code):
    code = (order_code or "").strip()
    for prefix in ("GIAO_", "DONG_"):
        if code.upper().startswith(prefix):
            return code[len(prefix):]
    return code


def _order_code_candidates(order_code):
    raw = (order_code or "").strip()
    if not raw:
        return []

    candidates = []

    def add(value):
        value = (value or "").strip()
        if value and value not in candidates:
            candidates.append(value)

    add(raw)
    stripped = _strip_workflow_prefix(raw)
    add(stripped)

    expanded = list(candidates)
    for code in expanded:
        add(re.sub(r"^s\d+", "", code, flags=re.IGNORECASE))

    expanded = list(candidates)
    for code in expanded:
        suffix_removed = re.sub(r"-\d+$", "", code)
        add(suffix_removed)
        add(re.sub(r"^s\d+", "", suffix_removed, flags=re.IGNORECASE))

    return candidates


def _get_wholesale_base_codes():
    base_codes = set()
    queries = [
        """
        SELECT order_code
        FROM packing_sessions
        WHERE order_code IS NOT NULL
          AND order_code <> ''
          AND (
              UPPER(COALESCE(packing_type, '')) LIKE '%%WHOLESALE%%'
              OR UPPER(COALESCE(packing_type, '')) LIKE '%%WHOLES%%'
              OR UPPER(COALESCE(packing_type, '')) LIKE '%%SI%%'
              OR UPPER(COALESCE(packing_type, '')) LIKE '%%SỈ%%'
          )
        """,
        """
        SELECT master_order_code AS order_code
        FROM wholesale_box_items
        WHERE master_order_code IS NOT NULL
          AND master_order_code <> ''
        """,
        """
        SELECT order_code
        FROM packing_small_packages
        WHERE order_code IS NOT NULL
          AND order_code <> ''
        """,
    ]

    for sql in queries:
        try:
            rows = fetch_all(sql)
        except Exception:
            continue
        for row in rows:
            code = (row.get("order_code") or "").strip()
            if code:
                base_codes.add(code)

    return base_codes


def _canonical_wholesale_code(order_code, base_codes=None):
    base_codes = base_codes if base_codes is not None else _get_wholesale_base_codes()
    for candidate in _order_code_candidates(order_code):
        if candidate in base_codes:
            return candidate
    return ""


def _date_value_in_range(value, date_from="", date_to=""):
    if not value:
        return True

    current = value.date() if hasattr(value, "date") else value
    current_text = str(current)

    if date_from and current_text < date_from:
        return False
    if date_to and current_text > date_to:
        return False
    return True


def _get_wholesale_session_map():
    rows = fetch_all(
        """
        SELECT *
        FROM packing_sessions
        WHERE order_code IS NOT NULL
          AND order_code <> ''
          AND (
              UPPER(COALESCE(packing_type, '')) LIKE '%%WHOLESALE%%'
              OR UPPER(COALESCE(packing_type, '')) LIKE '%%WHOLES%%'
              OR UPPER(COALESCE(packing_type, '')) LIKE '%%SI%%'
              OR UPPER(COALESCE(packing_type, '')) LIKE '%%SỈ%%'
          )
        ORDER BY COALESCE(end_time, start_time) DESC, id DESC
        """
    )

    session_map = {}
    for row in rows:
        session_map.setdefault(row.get("order_code"), row)
    return session_map


def _get_wholesale_video_counts():
    rows = fetch_all(
        """
        SELECT order_code, file_name
        FROM packing_videos
        WHERE order_code IS NOT NULL
          AND order_code <> ''
          AND order_code NOT LIKE 'GIAO_%%'
          AND (
              UPPER(COALESCE(video_type, '')) LIKE '%%WHOLESALE%%'
              OR UPPER(COALESCE(session_type, '')) = 'PACKING'
              OR order_code LIKE 'DONG_%%'
          )
        """
    )

    base_codes = _get_wholesale_base_codes()
    counts = defaultdict(set)
    for row in rows:
        canonical = _canonical_wholesale_code(row.get("order_code"), base_codes)
        if canonical and row.get("file_name"):
            counts[canonical].add(row.get("file_name"))
    return {order_code: len(values) for order_code, values in counts.items()}


def get_employee_report(date_from="", date_to=""):
    sql = """
        SELECT
            order_code,
            employee_code,
            employee_name,
            file_name,
            camera_id,
            result,
            duration_seconds,
            COALESCE(start_time, created_at) AS report_time
        FROM packing_videos
        WHERE COALESCE(start_time, created_at) IS NOT NULL
    """

    filter_sql, params = _date_filter_sql("COALESCE(start_time, created_at)", date_from, date_to)
    sql += filter_sql
    sql += " ORDER BY report_time DESC LIMIT 50000"

    employee_names = _get_employee_name_map()
    grouped = {}

    video_rows = fetch_all(sql, params)
    done_keys = {
        (row.get("order_code"), row.get("file_name"), row.get("camera_id"))
        for row in video_rows
        if (row.get("result") or "").lower() == "done"
    }

    for row in video_rows:
        key = (row.get("order_code"), row.get("file_name"), row.get("camera_id"))
        if (row.get("result") or "").lower() != "done" and key in done_keys:
            continue

        employee_code = _employee_code_from_row(row) or ""
        if not employee_code:
            continue

        employee_name = row.get("employee_name") or employee_names.get(employee_code) or ""
        if employee_code.upper() == "NA":
            employee_name = employee_name or "N/A"

        work_date = row.get("report_time").date()
        key = (employee_code, employee_name, work_date)

        item = grouped.setdefault(
            key,
            {
                "employee_code": employee_code,
                "employee_name": employee_name,
                "work_date": work_date,
                "orders": set(),
                "total_videos": 0,
                "total_duration_seconds": 0,
            },
        )

        if row.get("order_code"):
            item["orders"].add(row.get("order_code"))
        item["total_videos"] += 1
        item["total_duration_seconds"] += int(row.get("duration_seconds") or 0)

    rows = []
    for item in grouped.values():
        rows.append({
            "employee_code": item["employee_code"],
            "employee_name": item["employee_name"],
            "work_date": item["work_date"],
            "total_orders": len(item["orders"]),
            "total_videos": item["total_videos"],
            "total_duration_seconds": item["total_duration_seconds"],
        })

    rows.sort(key=lambda r: (r["work_date"], r["total_orders"]), reverse=True)
    return rows[:5000]


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

    filter_sql, params = _date_filter_sql("COALESCE(start_time, created_at)", date_from, date_to)
    sql += filter_sql

    if session_type:
        sql += " AND session_type = %s"
        params.append(session_type)

    sql += " ORDER BY COALESCE(start_time, created_at) DESC, id ASC LIMIT 10000"
    return fetch_all(sql, params)


def get_missing_video_report():
    return fetch_all(
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
        WHERE file_path IS NULL
           OR file_path = ''
           OR file_size IS NULL
           OR file_size = 0
        ORDER BY created_at DESC
        LIMIT 5000
        """
    )


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
            last_shipping_event_at AS shipping_updated_at,
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


def get_order_status_report_by_type(order_type, date_from="", date_to="", packing_status="", shipping_status=""):
    sql = """
        SELECT
            order_code,
            order_type,
            customer_name,
            customer_phone,
            total_boxes,
            packed_boxes,
            packed_children,
            video_count,
            packing_status,
            conveyor_status,
            shipping_status,
            tracking_code,
            last_packed_at,
            last_shipping_event_at,
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

    sql += " ORDER BY COALESCE(last_packed_at, updated_at) DESC LIMIT 10000"

    base_codes = _get_wholesale_base_codes()
    session_map = _get_wholesale_session_map()
    video_counts = _get_wholesale_video_counts()
    rows = []
    wholesale_seen = set()

    for row in fetch_all(sql, params):
        code = (row.get("order_code") or "").strip()
        if not code or code.upper().startswith(("GIAO_", "DONG_")):
            continue

        canonical = _canonical_wholesale_code(code, base_codes)
        is_wholesale = bool(canonical) or _is_wholesale_text(row.get("order_type"))

        if order_type == "ecom":
            if is_wholesale or not _is_ecom_text(row.get("order_type")):
                continue
            row["order_type"] = _order_type_label("ecom")
            row["packing_status"] = _packing_status_label(row, "ecom")
            row["packed_at"] = row.get("last_packed_at") or row.get("updated_at")
            row["shipping_updated_at"] = row.get("last_shipping_event_at")
            rows.append(row)
            continue

        if order_type != "wholesale" or not is_wholesale:
            continue

        canonical = canonical or code
        session = session_map.get(canonical, {})
        report_time = (
            session.get("end_time")
            or session.get("start_time")
            or row.get("last_packed_at")
            or row.get("updated_at")
        )

        if not _date_value_in_range(report_time, date_from, date_to):
            continue

        item = dict(row)
        item["source_order_code"] = code
        item["canonical_order_code"] = canonical
        item["order_code"] = canonical
        item["order_type"] = _order_type_label("wholesale")
        item["video_count"] = video_counts.get(canonical, row.get("video_count") or 0)
        item["packing_status"] = _packing_status_label(item, "wholesale")
        item["packed_at"] = report_time
        item["shipping_updated_at"] = row.get("last_shipping_event_at")
        item["total_boxes"] = session.get("total_boxes", row.get("total_boxes"))
        item["packed_boxes"] = session.get("total_boxes", row.get("packed_boxes"))
        item["packed_children"] = session.get("total_items", row.get("packed_children"))

        current = wholesale_seen
        if canonical not in current:
            rows.append(item)
            current.add(canonical)

    if order_type == "wholesale":
        for canonical, session in session_map.items():
            if canonical in wholesale_seen:
                continue

            report_time = session.get("end_time") or session.get("start_time")
            if not _date_value_in_range(report_time, date_from, date_to):
                continue

            item = {
                "order_code": canonical,
                "source_order_code": canonical,
                "canonical_order_code": canonical,
                "order_type": _order_type_label("wholesale"),
                "customer_name": "",
                "customer_phone": "",
                "total_boxes": session.get("total_boxes"),
                "packed_boxes": session.get("total_boxes"),
                "packed_children": session.get("total_items"),
                "video_count": video_counts.get(canonical, 0),
                "packing_status": "Hoàn thành" if (session.get("status") or "").upper() == "COMPLETED" else session.get("status"),
                "conveyor_status": "WAITING",
                "shipping_status": "WAITING",
                "tracking_code": "",
                "packed_at": report_time,
                "shipping_updated_at": "",
                "updated_at": report_time,
            }
            rows.append(item)

    rows.sort(key=lambda r: r.get("packed_at") or r.get("updated_at") or datetime.min, reverse=True)
    return rows[:5000]


def get_wholesale_package_report_maps():
    employee_names = _get_employee_name_map()
    base_codes = _get_wholesale_base_codes()
    detail_map = {}
    packer_map = {}
    delivery_map = {}

    rows = fetch_all(
        """
        SELECT
            w.master_order_code AS order_code,
            w.box_code,
            w.child_order_code,
            w.scan_index,
            COALESCE(NULLIF(w.employee_code, ''), NULLIF(ps.employee_code, '')) AS employee_code,
            COALESCE(NULLIF(w.employee_name, ''), NULLIF(ps.employee_name, '')) AS employee_name
        FROM wholesale_box_items w
        LEFT JOIN packing_sessions ps
            ON ps.id = w.packing_session_id
        WHERE w.master_order_code IS NOT NULL
          AND w.master_order_code <> ''
          AND COALESCE(w.is_deleted, 0) = 0
        ORDER BY w.master_order_code ASC, w.packing_session_id ASC, w.scan_index ASC, w.id ASC
        """
    )

    for row in rows:
        order_code = _canonical_wholesale_code(row.get("order_code"), base_codes) or row.get("order_code")
        item_code = row.get("child_order_code") or row.get("box_code")
        if item_code:
            detail_map.setdefault(order_code, []).append(f"Item/kiện: {item_code}")

        employee = _format_employee(row.get("employee_code"), row.get("employee_name"), employee_names)
        _append_unique(packer_map, order_code, employee)

    small_package_rows = fetch_all(
        """
        SELECT
            p.order_code,
            p.small_package_code,
            p.scan_index,
            COALESCE(NULLIF(p.employee_code, ''), NULLIF(ps.employee_code, '')) AS employee_code,
            COALESCE(NULLIF(p.employee_name, ''), NULLIF(ps.employee_name, '')) AS employee_name
        FROM packing_small_packages p
        LEFT JOIN packing_sessions ps
            ON ps.id = p.packing_session_id
        WHERE p.order_code IS NOT NULL
          AND p.order_code <> ''
          AND COALESCE(p.is_deleted, 0) = 0
        ORDER BY p.order_code ASC, p.packing_session_id ASC, p.scan_index ASC, p.id ASC
        """
    )

    for row in small_package_rows:
        order_code = _canonical_wholesale_code(row.get("order_code"), base_codes) or row.get("order_code")
        if not order_code or order_code in detail_map:
            continue

        item_code = row.get("small_package_code")
        if item_code:
            detail_map.setdefault(order_code, []).append(f"Item/kiện: {item_code}")

        employee = _format_employee(row.get("employee_code"), row.get("employee_name"), employee_names)
        _append_unique(packer_map, order_code, employee)

    session_rows = fetch_all(
        """
        SELECT order_code, employee_code, employee_name, total_boxes, total_items
        FROM packing_sessions
        WHERE order_code IS NOT NULL
          AND order_code <> ''
          AND (
              UPPER(COALESCE(packing_type, '')) LIKE '%%WHOLESALE%%'
              OR UPPER(COALESCE(packing_type, '')) LIKE '%%WHOLES%%'
              OR UPPER(COALESCE(packing_type, '')) LIKE '%%SI%%'
              OR UPPER(COALESCE(packing_type, '')) LIKE '%%SỈ%%'
          )
        ORDER BY order_code ASC, id ASC
        """
    )

    for row in session_rows:
        order_code = _canonical_wholesale_code(row.get("order_code"), base_codes) or row.get("order_code")
        if not order_code:
            continue

        if order_code not in detail_map:
            parts = []
            if row.get("total_items") not in (None, ""):
                parts.append(f"Tổng sản phẩm: {row.get('total_items')}")
            if row.get("total_boxes") not in (None, ""):
                parts.append(f"Tổng kiện/thùng: {row.get('total_boxes')}")
            if parts:
                detail_map[order_code] = parts

        employee = _format_employee(row.get("employee_code"), row.get("employee_name"), employee_names)
        _append_unique(packer_map, order_code, employee)

    handover_rows = fetch_all(
        """
        SELECT master_order_code AS order_code, employee_code, employee_name, result
        FROM wholesale_handover_checks
        WHERE master_order_code IS NOT NULL
          AND master_order_code <> ''
        ORDER BY master_order_code ASC, checked_at ASC, id ASC
        """
    )

    for row in handover_rows:
        if (row.get("result") or "").upper() != "OK":
            continue
        order_code = _canonical_wholesale_code(row.get("order_code"), base_codes) or row.get("order_code")
        employee = _format_employee(row.get("employee_code"), row.get("employee_name"), employee_names)
        _append_unique(delivery_map, order_code, employee)

    delivery_rows = fetch_all(
        """
        SELECT
            order_code,
            assigned_to_code AS employee_code,
            assigned_to_name AS employee_name
        FROM delivery_assignments
        WHERE order_code IS NOT NULL
          AND order_code <> ''
        ORDER BY order_code ASC, assigned_at ASC, id ASC
        """
    )

    for row in delivery_rows:
        order_code = _canonical_wholesale_code(row.get("order_code"), base_codes) or row.get("order_code")
        employee = _format_employee(row.get("employee_code"), row.get("employee_name"), employee_names)
        _append_unique(delivery_map, order_code, employee)

    video_rows = fetch_all(
        """
        SELECT order_code, file_name, employee_code, employee_name
        FROM packing_videos
        WHERE order_code IS NOT NULL
          AND order_code LIKE 'GIAO_%%'
        ORDER BY order_code ASC, COALESCE(start_time, created_at) ASC, id ASC
        """
    )

    for row in video_rows:
        order_code = (row.get("order_code") or "").strip()
        if not order_code.startswith("GIAO_"):
            continue

        master_order_code = _canonical_wholesale_code(order_code, base_codes) or order_code[5:]
        employee_code = _employee_code_from_row(row)
        employee = _format_employee(employee_code, row.get("employee_name"), employee_names)
        _append_unique(delivery_map, master_order_code, employee)

    packing_video_rows = fetch_all(
        """
        SELECT order_code, file_name, employee_code, employee_name
        FROM packing_videos
        WHERE order_code IS NOT NULL
          AND order_code NOT LIKE 'GIAO_%%'
          AND (
              UPPER(COALESCE(video_type, '')) LIKE '%%WHOLESALE%%'
              OR UPPER(COALESCE(session_type, '')) = 'PACKING'
              OR order_code LIKE 'DONG_%%'
          )
        ORDER BY order_code ASC, COALESCE(start_time, created_at) ASC, id ASC
        """
    )

    for row in packing_video_rows:
        order_code = _canonical_wholesale_code(row.get("order_code"), base_codes) or row.get("order_code")
        employee_code = _employee_code_from_row(row)
        employee = _format_employee(employee_code, row.get("employee_name"), employee_names)
        _append_unique(packer_map, order_code, employee)

    detail_output = {
        order_code: "\n".join(
            f"{idx}. {item}" for idx, item in enumerate(items, start=1)
        )
        for order_code, items in detail_map.items()
    }

    return (
        detail_output,
        {order_code: "\n".join(values) for order_code, values in packer_map.items()},
        {order_code: "\n".join(values) for order_code, values in delivery_map.items()},
    )


def attach_small_package_detail(rows):
    detail_map, packer_map, delivery_map = get_wholesale_package_report_maps()
    base_codes = _get_wholesale_base_codes()

    for row in rows:
        order_code = (
            row.get("canonical_order_code")
            or _canonical_wholesale_code(row.get("order_code"), base_codes)
            or row.get("order_code")
        )
        detail = detail_map.get(order_code, "")

        row["small_package_detail"] = detail or "Chưa có mã quét Item/kiện"
        row["packing_employee"] = packer_map.get(order_code, "N/A")
        row["delivery_employee"] = delivery_map.get(order_code, "N/A")

    return rows


def attach_packing_employee(rows):
    employee_names = _get_employee_name_map()
    order_codes = [row.get("order_code") for row in rows if row.get("order_code")]

    if not order_codes:
        return rows

    placeholders = ", ".join(["%s"] * len(order_codes))
    video_rows = fetch_all(
        f"""
        SELECT order_code, file_name, employee_code, employee_name
        FROM packing_videos
        WHERE order_code IN ({placeholders})
          AND order_code NOT LIKE 'GIAO_%%'
        ORDER BY order_code ASC, COALESCE(start_time, created_at) ASC, id ASC
        """,
        order_codes,
    )

    employee_map = defaultdict(list)
    for row in video_rows:
        employee_code = _employee_code_from_row(row)
        employee = _format_employee(employee_code, row.get("employee_name"), employee_names, na_name=False)
        _append_unique(employee_map, row.get("order_code"), employee)

    for row in rows:
        employees = employee_map.get(row.get("order_code"))
        if employees:
            row["packing_employee"] = "\n".join(employees)

    return rows


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
    except Exception as exc:
        db_error = str(exc)

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
        ecom_rows = get_order_status_report_by_type(
            order_type="ecom",
            date_from=date_from,
            date_to=date_to,
            packing_status=packing_status,
            shipping_status=shipping_status,
        )
        ecom_rows = attach_packing_employee(ecom_rows)

        wholesale_rows = get_order_status_report_by_type(
            order_type="wholesale",
            date_from=date_from,
            date_to=date_to,
            packing_status=packing_status,
            shipping_status=shipping_status,
        )
        wholesale_rows = attach_small_package_detail(wholesale_rows)

        output = export_order_status_split_report(
            ecom_rows=ecom_rows,
            wholesale_rows=wholesale_rows,
            date_from=date_from,
            date_to=date_to,
        )
        filename = f"ATG_bao_cao_chi_tiet_don_hang_{timestamp}.xlsx"
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
                *
            FROM packing_videos
            WHERE file_path IS NOT NULL
              AND file_path <> ''
            ORDER BY created_at DESC
            LIMIT 2000
            """
        )

        for video in videos:
            if not video_file_exists(
                video.get("file_path"),
                storage_code=video.get("storage_code"),
                relative_path=video.get("relative_path"),
            ):
                rows.append(video)
    except Exception as exc:
        db_error = str(exc)

    return render_template("reports/missing_files.html", rows=rows, db_error=db_error)


@report_bp.route("/missing-files/export")
def export_missing_files():
    rows = []

    videos = fetch_all(
        """
        SELECT
            *
        FROM packing_videos
        WHERE file_path IS NOT NULL
          AND file_path <> ''
        ORDER BY created_at DESC
        LIMIT 5000
        """
    )

    for video in videos:
        if not video_file_exists(
            video.get("file_path"),
            storage_code=video.get("storage_code"),
            relative_path=video.get("relative_path"),
        ):
            rows.append(video)

    output = export_missing_video_report(rows)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ATG_video_mat_file_that_{timestamp}.xlsx"

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

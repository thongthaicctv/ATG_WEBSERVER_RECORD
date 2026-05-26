# services/export_excel_service.py
# -*- coding: utf-8 -*-

from io import BytesIO
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter


HEADER_FILL = PatternFill("solid", fgColor="0B5ED7")
HEADER_FONT = Font(name="Times New Roman", size=13, bold=True, color="FFFFFF")
NORMAL_FONT = Font(name="Times New Roman", size=13)
TITLE_FONT = Font(name="Times New Roman", size=16, bold=True, color="0B2545")
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)
THIN_BORDER = Border(
    left=Side(style="thin", color="CCCCCC"),
    right=Side(style="thin", color="CCCCCC"),
    top=Side(style="thin", color="CCCCCC"),
    bottom=Side(style="thin", color="CCCCCC"),
)


def _format_sheet(ws):
    ws.freeze_panes = "A4"

    for row in ws.iter_rows():
        for cell in row:
            cell.font = NORMAL_FONT
            cell.alignment = CENTER
            cell.border = THIN_BORDER

    for cell in ws[3]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER

    for col in ws.columns:
        max_length = 0
        col_letter = get_column_letter(col[0].column)

        for cell in col:
            value = str(cell.value) if cell.value is not None else ""
            max_length = max(max_length, len(value))

        ws.column_dimensions[col_letter].width = min(max(max_length + 3, 12), 45)


def _write_title(ws, title, subtitle=""):
    ws.merge_cells("A1:H1")
    ws["A1"] = title
    ws["A1"].font = TITLE_FONT
    ws["A1"].alignment = CENTER

    ws.merge_cells("A2:H2")
    ws["A2"] = subtitle
    ws["A2"].font = NORMAL_FONT
    ws["A2"].alignment = CENTER


def export_employee_report(rows, date_from="", date_to=""):
    wb = Workbook()
    ws = wb.active
    ws.title = "Bao cao nhan vien"

    subtitle = f"Từ ngày: {date_from or '...'}  đến ngày: {date_to or '...'}"
    _write_title(ws, "BÁO CÁO NĂNG SUẤT NHÂN VIÊN", subtitle)

    headers = [
        "STT",
        "Ngày",
        "Mã NV",
        "Tên nhân viên",
        "Tổng đơn",
        "Tổng video",
        "Tổng thời lượng giây",
        "Tổng thời lượng phút",
    ]

    ws.append([])
    ws.append(headers)

    for idx, r in enumerate(rows, start=1):
        total_seconds = int(r.get("total_duration_seconds") or 0)
        total_minutes = round(total_seconds / 60, 2)

        ws.append([
            idx,
            r.get("work_date"),
            r.get("employee_code") or "",
            r.get("employee_name") or "",
            r.get("total_orders") or 0,
            r.get("total_videos") or 0,
            total_seconds,
            total_minutes,
        ])

    _format_sheet(ws)

    return _save_to_memory(wb)


def export_video_report(rows, date_from="", date_to=""):
    wb = Workbook()
    ws = wb.active
    ws.title = "Bao cao video"

    subtitle = f"Từ ngày: {date_from or '...'}  đến ngày: {date_to or '...'}"
    _write_title(ws, "BÁO CÁO VIDEO THEO NGÀY", subtitle)

    headers = [
        "STT",
        "Thời gian",
        "Mã đơn",
        "Loại",
        "Scanner",
        "Camera",
        "Nhân viên",
        "File",
        "Dung lượng MB",
        "Thời lượng giây",
        "Kết quả",
    ]

    ws.append([])
    ws.append(headers)

    for idx, r in enumerate(rows, start=1):
        file_size_mb = round((r.get("file_size") or 0) / 1024 / 1024, 2)

        ws.append([
            idx,
            r.get("start_time") or r.get("created_at") or "",
            r.get("order_code") or "",
            r.get("session_type") or r.get("video_type") or "",
            r.get("scanner_id") or "",
            f"{r.get('camera_id') or ''} - {r.get('camera_name') or ''}",
            r.get("employee_name") or r.get("employee_code") or "",
            r.get("file_name") or "",
            file_size_mb,
            r.get("duration_seconds") or 0,
            r.get("result") or "",
        ])

    _format_sheet(ws)

    return _save_to_memory(wb)


def export_missing_video_report(rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "Video loi thieu file"

    _write_title(ws, "BÁO CÁO VIDEO LỖI / THIẾU FILE", f"Xuất lúc: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    headers = [
        "STT",
        "ID",
        "Mã đơn",
        "Camera",
        "File name",
        "File path",
        "Dung lượng DB",
        "Thời lượng",
        "Ngày tạo",
    ]

    ws.append([])
    ws.append(headers)

    for idx, r in enumerate(rows, start=1):
        ws.append([
            idx,
            r.get("id"),
            r.get("order_code") or "",
            f"{r.get('camera_id') or ''} - {r.get('camera_name') or ''}",
            r.get("file_name") or "",
            r.get("file_path") or "",
            r.get("file_size") or 0,
            r.get("duration_seconds") or 0,
            r.get("created_at") or "",
        ])

    _format_sheet(ws)
    ws.column_dimensions["F"].width = 70

    return _save_to_memory(wb)


def export_order_status_report(rows, date_from="", date_to=""):
    wb = Workbook()
    ws = wb.active
    ws.title = "Trang thai don hang"

    subtitle = f"Từ ngày: {date_from or '...'}  đến ngày: {date_to or '...'}"
    _write_title(ws, "BÁO CÁO TRẠNG THÁI ĐƠN HÀNG", subtitle)

    headers = [
        "STT",
        "Mã đơn",
        "Loại đơn",
        "Khách hàng",
        "SĐT",
        "Số video",
        "Đóng hàng",
        "Băng truyền",
        "Vận chuyển",
        "Mã vận đơn",
        "Cập nhật",
    ]

    ws.append([])
    ws.append(headers)

    for idx, r in enumerate(rows, start=1):
        ws.append([
            idx,
            r.get("order_code") or "",
            r.get("order_type") or "",
            r.get("customer_name") or "",
            r.get("customer_phone") or "",
            r.get("video_count") or 0,
            r.get("packing_status") or "",
            r.get("conveyor_status") or "",
            r.get("shipping_status") or "",
            r.get("tracking_code") or "",
            r.get("updated_at") or "",
        ])

    _format_sheet(ws)

    return _save_to_memory(wb)


def _save_to_memory(wb):
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output
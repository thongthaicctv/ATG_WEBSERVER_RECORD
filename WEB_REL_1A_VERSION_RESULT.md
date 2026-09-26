# WEB_REL_1A_VERSION_RESULT

Phase: WEB-REL-1A — Release version + deterministic production build
Ngày: 2026-09-26 · Project: `D:\PYTHON\ATG_DIGICAM_WEBSERVER`

```
VERSION      = 1.0.0
DISPLAY_NAME = ATG_DIGICAM WebServer v1.0.0
EXE_NAME     = ATG_WEBSERVER.exe
```

## 1. Audit vị trí hiển thị

| Vị trí | Trước | Sau |
|---|---|---|
| main.py console | `ATG_DIGICAM WebServer STARTED` | `ATG_DIGICAM WebServer v1.0.0 STARTED` |
| templates/base.html `<title>` (mọi trang sau login) | `ATG_DIGICAM WebServer` | `ATG_DIGICAM WebServer v1.0.0` |
| templates/base.html sidebar `.brand` | `ATG_DIGICAM WebServer` | giữ nguyên + dòng nhỏ `v1.0.0` |
| templates/auth/login.html `<title>` | `Đăng nhập ATG_DIGICAM WebServer` | `Đăng nhập ATG_DIGICAM WebServer v1.0.0` |
| templates/auth/login.html `<h1>` | `ATG_DIGICAM WebServer` | `ATG_DIGICAM WebServer v1.0.0` |
| services/tray_service.py `APP_NAME` (window title, tooltip, balloon title) | `ATG_DIGICAM WebServer` | `ATG_DIGICAM WebServer v1.0.0` |

Không đổi (message nghiệp vụ, không cần version): routes/settings_routes.py, templates/settings/*.html, templates/dashboard.html, windows_startup.py shortcut Description.

## 2. Files changed

| File | Thay đổi |
|---|---|
| core/version.py (MỚI) | `APP_VERSION = "1.0.0"`, `APP_PRODUCT_NAME`, `APP_DISPLAY_NAME` — nguồn version duy nhất, chỉ dùng hiển thị |
| main.py | import version; `@app.context_processor` inject `app_version`, `app_display_name` cho template; dòng console STARTED |
| services/tray_service.py | `APP_NAME = APP_DISPLAY_NAME` (chỉ tên hiển thị) |
| templates/base.html | title + dòng `v1.0.0` nhỏ ở sidebar (có `default(...)` fallback) |
| templates/auth/login.html | title + h1 (có `default(...)` fallback) |
| build_onefile.bat | chọn Python cố định + `-m PyInstaller` (mục 3) |

Giữ line ending CRLF gốc. Backup trước khi sửa: `NOTE\WEB_REL_1A_BEFORE_20260926_035318\`.

Không đụng build/, dist/, web_cache/, .spec. (`compileall` trong test tự sinh `__pycache__/*.pyc` như bình thường.)

Định danh kỹ thuật xác nhận KHÔNG đổi:

- `build_onefile.spec` → `name="ATG_WEBSERVER"` → `dist\ATG_WEBSERVER.exe`
- `services/windows_startup.py` → `APP_NAME = "ATG_WEBSERVER"` (registry Run + shortcut .lnk)
- `ATG_WEBSERVER_CONFIG`, `ATG_WEBSERVER_SECRET_KEY`, `ATG_WEBSERVER_PUBLIC_DOWNLOAD`
- `Global\ATG_WEBSERVER_SINGLE_INSTANCE`, tray class `ATG_WEBSERVER_TRAY`
- Database `atg_order_system`

## 3. Build script changes (build_onefile.bat)

Thứ tự chọn Python:

1. `%~dp0.venv\Scripts\python.exe` (hiện có, `pyvenv.cfg`: home = C:\Python310, version 3.10.11)
2. `C:\Python310\python.exe`
3. `python` trong PATH (có cảnh báo)

Sau đó:

- In `Python build: ...` + `--version`; nếu Python không chạy → dừng.
- Kiểm tra 3.10 → nếu khác chỉ **cảnh báo** (không chặn).
- `"%PYTHON_BIN%" -m PyInstaller --version`; nếu thiếu → `"%PYTHON_BIN%" -m pip install pyinstaller` (chỉ PyInstaller, không nâng package khác).
- Build: `"%PYTHON_BIN%" -m PyInstaller --noconfirm --clean build_onefile.spec`
- Đã bỏ `where pyinstaller` và lệnh gọi trực tiếp `pyinstaller ...`.

Giữ nguyên: output `dist\ATG_WEBSERVER.exe`, copy `webserver_config.json`, copy `HUONG_DAN_CAI_DAT_CHAY_AN.txt`, tìm/copy `ffmpeg.exe` vào `dist\bin`, toàn bộ warning, `pause`.

## 4. Tests

Chạy trong Linux VM Python 3.10.12 (không có C:\Python310 trong môi trường test):

| # | Test | Kết quả |
|---|---|---|
| 1 | `python -m compileall -q core db routes services main.py` | PASS (rc=0, không lỗi) |
| 2 | import main + `create_app()` smoke (stub winreg/ctypes.windll chỉ trong test) | PASS, 26 routes, secret_key giữ `ATG_WEBSERVER_SECRET_KEY` |
| 3 | Route video/download/report load: `/video/download/<id>`, `/video/download-mp4/<id>`, `/video/download-original/<id>`, `/video/public-download/<id>/<token>`, `/video/stream/<id>`, `/video/play/<id>`, `/video/ecom/`, `/video/wholesale/...`, `/reports/`, `/reports/export`, `/reports/missing-files`, `/reports/missing-files/export` | PASS |
| 3b | `GET /login` → 200, title `Đăng nhập ATG_DIGICAM WebServer v1.0.0`, h1 `ATG_DIGICAM WebServer v1.0.0`; render `base.html` → title `ATG_DIGICAM WebServer v1.0.0`, sidebar `v1.0.0` | PASS |
| 4 | Search source `ATG_DIGICAM WebServer v1.0.0` (templates) + `APP_VERSION = "1.0.0"` (core/version.py); tray APP_NAME runtime = `ATG_DIGICAM WebServer v1.0.0` | PASS |
| 5 | `build_onefile.bat` chứa `"%PYTHON_BIN%" -m PyInstaller --noconfirm --clean build_onefile.spec`, không còn `where pyinstaller`/`pyinstaller ^` | PASS |
| 6 | Không build EXE | Tuân thủ |

**Sự cố trong lúc test (đã khôi phục):** smoke test trên Linux không có `win32crypt` nên `core/config_manager.load_config()` coi `webserver_config.json` (DPAPI) là unreadable, đổi tên nó thành `webserver_config.unreadable_20260926_035435.json` và ghi config mặc định. Đã `mv` file gốc về lại `webserver_config.json` ngay; xác nhận **byte-for-byte giống `dist\webserver_config.json`**, mtime gốc 2026-08-28 giữ nguyên. Không còn file unreadable mới. (Hành vi này là của code cũ, không thuộc phạm vi sửa.)

## 5. Risks

1. Chưa chạy `C:\Python310\python.exe -m compileall ...` và smoke test trên Windows thật — nên chạy lại trên máy trước khi build.
2. Tên cửa sổ ẩn của tray đổi thành `ATG_DIGICAM WebServer v1.0.0`; không có code nào FindWindow theo title (grep xác nhận), single-instance dùng mutex.
3. Tooltip tray = `ATG_DIGICAM WebServer v1.0.0 - http://127.0.0.1:<port>` (~53 ký tự, dưới giới hạn 128); balloon title 28 ký tự (giới hạn 64).
4. Nếu `.venv` bị xóa/hỏng, script tự rơi về C:\Python310 rồi `python` PATH — sẽ in rõ Python đang dùng và cảnh báo nếu không phải 3.10.
5. Bump version sau này: chỉ sửa `core/version.py` (fallback `default('...v1.0.0')` trong 2 template chỉ dùng khi context processor không chạy).

---

DATABASE_SCHEMA_CHANGED = NO
BUSINESS_LOGIC_CHANGED = NO
STORAGE_RESOLVER_CHANGED = NO
AUTH_PERMISSION_CHANGED = NO

WEB_REL_1A_READY_TO_BUILD = YES

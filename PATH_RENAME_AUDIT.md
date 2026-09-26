# PATH_RENAME_AUDIT — ATG_DIGICAM WebServer

Ngày audit: 2026-09-24 · Branch: `web-nas-local-20260924`

## 1. Old project path
`D:\PYTHON\ATG_WEBSERVER_ATG_DIGICAM`
(và path cũ hơn nữa: `D:\PYTHON\ATG_WEBSERVER_RECORD` — còn dính trong `.venv` và `build/`)

## 2. New project path
`D:\PYTHON\ATG_DIGICAM_WEBSERVER`

> **BLOCKER:** tại thời điểm audit, thư mục trên ổ D **CHƯA được đổi tên**.
> `D:\PYTHON` chỉ có `ATG_WEBSERVER_ATG_DIGICAM`, không có `ATG_DIGICAM_WEBSERVER`.
> Source đã sẵn sàng cho việc đổi tên (không còn phụ thuộc path cứng), nhưng
> việc rename thư mục vật lý phải do người dùng thực hiện (xem mục 10).

- Technical name: `ATG_DIGICAM_WEBSERVER`
- Display name: `ATG_DIGICAM WebServer`

## 3. Files có hardcoded old project path
Search source text (*.py, *.json, *.txt, *.md, *.bat, *.cmd, *.ps1, *.spec, *.ini, *.yaml, *.yml, *.toml, *.html, *.css, *.js),
loại trừ `.venv/ build/ dist/ __pycache__/ logs/ .git/`:

| Pattern | Kết quả trong source |
|---|---|
| `ATG_WEBSERVER_ATG_DIGICAM` | **0** |
| `D:\PYTHON\ATG_WEBSERVER_ATG_DIGICAM` | **0** |
| `ATG_WEBSERVER_RECORD` | **0** (chỉ có trong git remote URL, `.venv`, `build/`) |
| `D:\PYTHON\ATG_WEBSERVER_RECORD` | **0** |

Kết luận: code đã dùng dynamic path từ trước (`core/path_utils.app_root()`, `Path(__file__)`, `sys.executable`, `sys._MEIPASS`, `SPECPATH`, `%~dp0`).

### Phân loại toàn bộ đường dẫn tuyệt đối tìm thấy

| File | Path | Loại | Xử lý |
|---|---|---|---|
| services/video_stream_service.py:66-68 | `D:\PYTHON-TCR\bin\ffmpeg.exe`, `D:\PYTHON-TCR\1. EXE\ATG_AI_SYSTEM_RECORD\...\ffmpeg.exe` | C – FFmpeg fallback | Giữ nguyên. Không phải project path; chỉ là fallback sau `app_root()/bin/ffmpeg.exe` |
| build_onefile.bat:50-51 | như trên | C / F | Giữ nguyên (ưu tiên `%~dp0bin\ffmpeg.exe` trước) |
| HUONG_DAN_CAI_DAT_CHAY_AN.txt:5 | `D:\PYTHON-TCR\EXE\ATG_WEBSERVER` | E – ví dụ thư mục deploy exe | Giữ nguyên |
| HUONG_DAN_CAI_DAT_CHAY_AN.txt:19-21 | `E:\DEBUG`, `D:\VIDEO`, `D:\ATG_DataBackup` | B – video/storage | **Không sửa** |
| templates/settings/database.html:55 | placeholder `D:\VIDEO`, `D:\ATG_DataBackup` | B | **Không sửa** |
| templates/settings/startup.html:45 | ví dụ `D:\PYTHON-TCR\EXE\ATG_WEBSERVER` | E | Giữ nguyên |
| webserver_config.json | DPAPI-encrypted (không chứa path dạng text) | D | Không đụng |
| .venv/Scripts/* | `d:\PYTHON\ATG_WEBSERVER_RECORD\.venv` | venv | Cần recreate (mục 6) |
| build/build_onefile/*.toc | `...ATG_WEBSERVER_RECORD...` | H – artifact | Không sửa, build lại |
| .git remote | `github.com/thongthaicctv/ATG_WEBSERVER_RECORD.git` | Git | Không đổi remote |

## 4. Files đã sửa (chỉ tên hiển thị + gộp cơ chế app_root)

| File | Thay đổi |
|---|---|
| services/windows_startup.py | Bỏ hàm `app_root()` trùng lặp, dùng `from core.path_utils import app_root` (logic giống hệt). Description shortcut → `ATG_DIGICAM WebServer - Auto start with Windows` |
| core/path_utils.py | Docstring |
| main.py | Banner console → `ATG_DIGICAM WebServer STARTED` |
| services/tray_service.py | `APP_NAME` (tooltip/tiêu đề tray) → `ATG_DIGICAM WebServer` |
| templates/base.html | `<title>` + brand sidebar → `ATG_DIGICAM WebServer` |
| templates/auth/login.html | `<title>` + `<h1>` |
| templates/settings/startup.html | Nhãn checkbox tự khởi động |
| routes/settings_routes.py | 2 message thông báo bật/tắt tự khởi động (chỉ text) |
| build_onefile.bat | Dòng `echo` tiêu đề |
| NOTE/NOTE CAU TRUC CODE.txt | Tên thư mục gốc |
| HUONG_DAN_CAI_DAT_CHAY_AN.txt | Dòng tiêu đề |

Tổng: 11 file, +17/-20 dòng (bỏ qua khác biệt CRLF). Giữ nguyên line ending CRLF.

## 5. Những path/tên cố tình giữ nguyên

| Giá trị | Lý do giữ |
|---|---|
| `ATG_WEBSERVER.exe` / `name="ATG_WEBSERVER"` trong spec | Shortcut Startup, registry Run và hướng dẫn deploy đang trỏ tên exe này |
| `APP_NAME = "ATG_WEBSERVER"` (windows_startup.py) | Là tên value registry `HKCU\...\Run` và tên file `.lnk` — đổi sẽ sinh entry trùng/mồ côi |
| `"ATG_WEBSERVER_CONFIG"` (config_manager.py) | Entropy DPAPI — đổi sẽ **không giải mã được** webserver_config.json |
| `app.secret_key = "ATG_WEBSERVER_SECRET_KEY"` | Đổi sẽ logout toàn bộ session |
| `"ATG_WEBSERVER_PUBLIC_DOWNLOAD"` (video_routes.py) | Salt ký link tải công khai — đổi sẽ vô hiệu link đã chia sẻ |
| `Global\ATG_WEBSERVER_SINGLE_INSTANCE` | Mutex chống chạy 2 instance (bản cũ + mới) |
| `ATG_WEBSERVER_TRAY` | Window class nội bộ |
| `DEFAULT_CONFIG["app"]["name"]` | Dữ liệu config, không hiển thị |
| Database `atg_order_system`, bảng, cột | Không thay đổi |
| `D:\VIDEO`, `D:\ATG_DataBackup`, UNC/NAS, `storage_locations.base_path` | Dữ liệu video — không liên quan tên project |
| FFmpeg fallback `D:\PYTHON-TCR\...` | Không phải project path |

## 6. .venv status
- `pyvenv.cfg`: `home = C:\Python310`, Python 3.10.11 (không phụ thuộc project path).
- `Scripts\activate(.bat)` và launcher `pip.exe`, `flask.exe`, `waitress-serve.exe` hardcode **`d:\PYTHON\ATG_WEBSERVER_RECORD\.venv`** → đã hỏng từ lần đổi tên trước; `pip.exe` sẽ lỗi. `python.exe` trong .venv vẫn chạy được.
- PyInstaller **không** có trong .venv (build đang dùng Python global).
- **Cần recreate** (không tự xóa). Đề xuất, chạy sau khi đã rename thư mục:

```bat
cd /d D:\PYTHON\ATG_DIGICAM_WEBSERVER
ren .venv .venv_old
C:\Python310\python.exe -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller
:: kiểm tra xong thì xóa .venv_old
```

## 7. Build status
- `build_onefile.spec` dùng `SPECPATH` → không hardcode; `build_onefile.bat` dùng `cd /d "%~dp0"` → không hardcode. OK cho path mới.
- `build/` chứa TOC từ `ATG_WEBSERVER_RECORD` → artifact cũ, không sửa; bat đã có `--clean`.
- `dist/ATG_WEBSERVER.exe` hiện tại **chưa build lại**, nên tên hiển thị mới chỉ có sau khi chạy `build_onefile.bat`.
- Lưu ý: nếu Startup shortcut/registry đang trỏ vào `...\ATG_WEBSERVER_ATG_DIGICAM\dist\ATG_WEBSERVER.exe`, sau khi rename phải vào **Cài đặt → Tự khởi động** bấm Lưu lại để cập nhật đường dẫn.

## 8. Git status
- Branch: `web-nas-local-20260924`
- Remote: `origin https://github.com/thongthaicctv/ATG_WEBSERVER_RECORD.git` (không đổi)
- Không pull / push / reset / restore / commit.
- Trước khi sửa, `git status` đã báo ~45 file `M`; đa số chỉ khác line ending (CRLF). Diff thật bỏ qua CR: 3 file `.pyc` + `logs/webserver.log`.
- **Không có `.gitignore`.** Đang track: `__pycache__/*.pyc` (~30 file) và `logs/webserver.log`. Untracked: `build/`, `dist/`, `web_cache/`.
  Đề xuất (chưa làm): thêm `.gitignore` với `.venv/ __pycache__/ *.pyc build/ dist/ logs/ web_cache/` rồi `git rm -r --cached` các pyc/log — cần người dùng đồng ý vì sẽ thay đổi file đang track.
- Sự cố nhỏ: một lần `git status` trong sandbox để lại `.git/index.lock` rỗng; đã xóa (được cấp quyền), không ảnh hưởng repo.

## 9. Các test đã chạy
Chạy trên bản **copy** source (không đụng config thật, không ghi `__pycache__` vào project), Python 3.10, Windows API được stub:

| Test | Kết quả |
|---|---|
| py_compile 25 file .py | PASS (0 lỗi) |
| Import `core.*`, `db.mysql_client` | PASS |
| Import `core.video_path_resolver` (`resolve_video_path`) | PASS |
| Import video routes (video, ecom, wholesale) | PASS |
| Import report_routes (+ export_excel_service) | PASS |
| Import order/settings/dashboard/shipping/auth routes, windows_startup, tray, video_stream/convert | PASS |
| `windows_startup.app_root is path_utils.app_root` | True |
| `app_root()` / config / log path theo thư mục thực thi | PASS (động) |
| Config load (config mặc định) → database `atg_order_system` | PASS |
| `main.create_app()` → 26 routes, gồm `/video/play`, `/video/stream`, `/video/download*`, `/video/download-mp4`, `/video/share-link`, `/reports/*`, `/reports/export` | PASS |
| db/mysql_client.py, config_manager.py, auth_manager.py không bị sửa | Xác nhận |
| Re-search `D:\PYTHON\ATG_WEBSERVER_ATG_DIGICAM` trong source | 0 kết quả |

Không test được trong sandbox: kết nối MySQL thật, giải mã DPAPI, tray/registry Windows thật. Import `export_excel_service` đơn lẻ lỗi chỉ do stub `winreg` của môi trường test (mimetypes), không phải lỗi code.
Không tìm thấy `StorageResolver` dạng class; cơ chế hiện có là `core.video_path_resolver.resolve_video_path` — import OK.

## 10. Lỗi / blocker còn lại
1. **Thư mục chưa đổi tên thật.** Cần: tắt WebServer (tray → Exit), đóng VS Code/terminal đang mở thư mục, rồi đổi `D:\PYTHON\ATG_WEBSERVER_ATG_DIGICAM` → `D:\PYTHON\ATG_DIGICAM_WEBSERVER`.
2. Recreate `.venv` (mục 6).
3. Build lại exe bằng `build_onefile.bat`.
4. Nếu dùng tự khởi động từ `dist` trong thư mục project: bấm Lưu lại trang Tự khởi động.
5. Quyết định về `.gitignore` (mục 8).
6. Test thật trên Windows: đăng nhập, xem video, download, convert MP4, báo cáo.

---
```
OLD_PATH = D:\PYTHON\ATG_WEBSERVER_ATG_DIGICAM
NEW_PATH = D:\PYTHON\ATG_DIGICAM_WEBSERVER
APP_NAME = ATG_DIGICAM WebServer
DATABASE_SCHEMA_CHANGED = NO
BUSINESS_LOGIC_CHANGED = NO
PATH_RENAME_STATUS = FAIL (source PASS — chờ đổi tên thư mục vật lý)
```

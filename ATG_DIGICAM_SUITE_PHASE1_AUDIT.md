# ATG_DIGICAM_SUITE_PHASE1_AUDIT — SUITE-1A

Ngày: 2026-09-26 · Loại: **CHỈ AUDIT** (không sửa code, không build, không di chuyển file, không đổi config thật)

| App | Project | EXE production | Build |
|---|---|---|---|
| Recorder | `D:\PYTHON\ATG_DIGICAM` | `dist\atg_digicam.exe` (onefile v4.0.7.4, 177 MB, có SHA256 file) + bản onedir `dist\atg_digicam\` | `build_onefile.bat` → `.venv` / `C:\Python310` / `python` → `-m PyInstaller build_onefile.spec` |
| WebServer | `D:\PYTHON\ATG_DIGICAM_WEBSERVER` | `dist\ATG_WEBSERVER.exe` (v1.0.0, tag `ATG-DIGICAM-WEBSERVER-v1.0.0`) | `build_onefile.bat` (WEB-REL-1A) |
| MultiView | `D:\PYTHON\MULTIPLAY` (người dùng xác nhận) | `dist\ATG-MultiPlay.exe` (onefile, windowed) | `build_onefile.ps1` → `python` trong PATH → `-m PyInstaller ATG-MultiPlay.spec` |

Phương pháp: đọc source/spec/bat/config bằng grep/cat (read-only). Không chạy app. Mật khẩu DB trong config đã che khi đọc.

---

## 1. Current deployment architecture

```
            ┌──────────── MySQL 127.0.0.1:3306 / atg_order_system (user atg_app) ────────────┐
            │  packing_videos (file_path, storage_code, relative_path)                         │
            │  storage_locations (LOCAL_<MACHINE>, NAS01)  video_storage_locations (tracking) │
            └───────────▲───────────────────────────▲────────────────────────────▲───────────┘
                        │ ghi                        │ đọc                        │ đọc (chỉ file_path)
   Recorder atg_digicam.exe                  ATG_WEBSERVER.exe            ATG-MultiPlay.exe
   - RTSP/QR/Record → D:\VIDEO_DEBUG         - Flask/waitress :8088       - PyQt6 + VLC
   - NAS sync worker → \\192.168.23.200\     - StorageResolver            - DB poll 5s, os.path.exists
     camerasihn (delete_local_after_sync=ON) - ffmpeg stream/MP4 convert  - ffmpeg ghép video
```

- 3 app là **3 process độc lập**, chỉ giao tiếp qua MySQL + filesystem (Local/NAS). Không có IPC giữa các app.
- WebServer **không phụ thuộc** Recorder đang chạy (đọc DB + storage_locations). ✅
- MultiView **cũng không phụ thuộc** Recorder process, nhưng **phụ thuộc config.json kiểu Recorder** và **file Local còn tồn tại** (xem §4, §9).

---

## 2. Recorder dependencies (`D:\PYTHON\ATG_DIGICAM`)

| # | Hạng mục | Hiện trạng | Nguồn |
|---|---|---|---|
| 1 | EXE production | `dist\atg_digicam.exe` onefile (PyInstaller, `console=False`, name `atg_digicam`). Bản onedir `dist\atg_digicam\atg_digicam.exe` + `_internal\` cũng tồn tại (01:25) — cần xác nhận bản nào đang chạy thật | `build_onefile.spec`, `dist\` |
| 2 | Config | `config.json` **relative path** (`core/config_manager.py: CONFIG_FILE = "config.json"`), cạnh EXE nhờ `main.py` gọi `os.chdir(dirname(sys.executable))` khi frozen. Plaintext, chứa DB password, cameras, `nas_sync`, `storage_path`. `services/mysql_client.py: load_db_config("config.json")` cũng relative | `main.py:14-15` |
| 3 | Logs | `logs\camera_events.log` (rotating, `system_logger.py`), `logs\license.log` (`core/logger.py`) — relative → cạnh EXE sau chdir. `barcode_log.json` (scanner.py) relative | |
| 4 | Cache/temp | Onefile giải nén vào `%TEMP%\_MEIxxxx` mỗi lần chạy (~177 MB). Lock `%TEMP%\atg_digicam.lock`. Pre-record: buffer trong RAM (bounded queue) | `main.py:70-88` |
| 5 | ffmpeg lookup | `record_worker._find_ffmpeg()`: `cam.ffmpeg_path` (config per-camera, hiện không set) → `resource_path("bin","ffmpeg.exe")` (= `_MEIPASS\bin`, **ffmpeg được bundle trong EXE**) → `resource_path("ffmpeg.exe")` → `C:\ffmpeg\bin\ffmpeg.exe` → `shutil.which("ffmpeg")`. Build: spec **bắt buộc** có `bin\ffmpeg.exe` hoặc `C:\ffmpeg\bin` hoặc PATH | `services/record_worker.py:37-40,477-495` |
| 6 | ffprobe lookup | `pre_record.py:150`: `ffprobe.exe` cạnh ffmpeg đã tìm (trong `_MEIPASS\bin` **chỉ có ffmpeg**) → fallback `"ffprobe"` trong PATH | |
| 7 | app_root / sys.executable | `core/resource_paths.py`: `app_base_dir()` = dir(sys.executable) khi frozen; `resource_path()` = `_MEIPASS`; `ensure_app_file("hr","employees.json")` copy từ bundle ra cạnh EXE | |
| 8 | Hardcode | `C:\ffmpeg\bin\ffmpeg.exe`; `C:\Program Files\(x86)\VideoLAN\VLC\vlc.exe` (camera_grid_page mở VLC ngoài); `nvidia-smi` paths; `C:/Windows/Fonts/*.ttf` (QR); `%PROGRAMDATA%\CCTV_AI_SYSTEM\license`; default `storage_path` / `web_index_url=http://127.0.0.1:8088/` | |
| 9 | Windows Startup | **Không có** code registry/shortcut Startup trong Recorder | grep winreg/Startup = 0 |
| 10 | License/cache | `%PROGRAMDATA%\CCTV_AI_SYSTEM\license\{license.dat,cache.dat,runtime.dat,machine_uuid.dat}` (tạo lúc import `license/paths.py`) — **ngoài thư mục app**, không bị ảnh hưởng khi đổi folder | `license/paths.py` |
| 11 | Database | `config.json → db`: 127.0.0.1:3306 `atg_order_system` `atg_app`, timeout 2/3/3s | |
| 12 | Storage/NAS | `storage_path = D:/VIDEO_DEBUG`; `nas_sync.enabled=true`, `NAS01`, `\\192.168.23.200\camerasihn`, **`delete_local_after_sync=true`**, verify_before_delete=true | |
| 13 | Resource cạnh EXE | `config.json` (bắt buộc), `hr\employees.json` (tự tạo), `logs\` (tự tạo). DLL cv2/PySide6/ffmpeg nằm trong bundle. Model WeChat QR trong bundle | |
| – | Port/service | `services/web_server.py`, `http_server.py` (port 18080) **không được gọi ở đâu** (dead code). Recorder **không mở port**. `config.web_index_url = http://127.0.0.1:48080` (chỉ là link mở WebServer — khác default 8088, cần kiểm tra) | |
| – | Single instance | File lock `%TEMP%\atg_digicam.lock` (msvcrt, per-user TEMP) | |

---

## 3. WebServer dependencies (`D:\PYTHON\ATG_DIGICAM_WEBSERVER`, v1.0.0)

| # | Hạng mục | Hiện trạng | Nguồn |
|---|---|---|---|
| 1 | EXE | `dist\ATG_WEBSERVER.exe` onefile; kèm `dist\webserver_config.json`, `HUONG_DAN_CAI_DAT_CHAY_AN.txt`, `dist\ffmpeg\bin\{ffmpeg,ffprobe}.exe`, `dist\logs`, `dist\web_cache` | spec `name="ATG_WEBSERVER"` |
| 2 | Config | `app_root()\webserver_config.json` — **tuyệt đối theo sys.executable**, không phụ thuộc CWD ✅. Mã hóa **DPAPI current-user** (`ATG_WEBSERVER_CONFIG`), fallback XOR theo COMPUTERNAME+USERNAME | `core/path_utils.py`, `core/config_manager.py` |
| 3 | Logs | `app_root()\logs\webserver.log` ✅ | |
| 4 | web_cache | `download.mp4_cache_dir` mặc định `web_cache/mp4` → nếu relative thì `app_root()/…` ✅ | `services/video_convert_service.py:13-23` |
| 5 | ffmpeg lookup | `locate_ffmpeg()`: `video.ffmpeg_path` (config) → env `FFMPEG_PATH` → `app_root\bin\ffmpeg.exe` → `app_root\ffmpeg\bin\ffmpeg.exe` → **`Path.cwd()\bin\ffmpeg.exe`** → hardcode `D:\PYTHON-TCR\bin\…`, `D:\PYTHON-TCR\1. EXE\ATG_AI_SYSTEM_RECORD\bin\…`, `…\ffmpeg\bin\…` → PATH. **Không bundle** ffmpeg vào EXE | `services/video_stream_service.py:54-76` |
| 6 | ffprobe | **Không dùng** (grep = 0). `dist\ffmpeg\bin\ffprobe.exe` có nhưng thừa | |
| 7 | app_root | `Path(sys.executable).resolve().parent` khi frozen ✅; templates/static từ `_MEIPASS` | |
| 8 | Startup | `services/windows_startup.py`: Registry `HKCU\…\Run\ATG_WEBSERVER` = `"<exe>" --minimized` **và** shortcut `Startup\ATG_WEBSERVER.lnk`. **Lưu đường dẫn tuyệt đối EXE** → đổi thư mục phải bật lại Startup | |
| 9 | Tray / single-instance | Tray class `ATG_WEBSERVER_TRAY`; mutex `Global\ATG_WEBSERVER_SINGLE_INSTANCE` (toàn máy) | |
| 10 | DPAPI config | Chỉ user Windows đã mã hóa mới giải mã được. **Nếu đọc không được → config bị đổi tên `.unreadable_<ts>.json` và ghi config mặc định** (đã xảy ra trong test WEB-REL-1A và khôi phục) | `config_manager.py:82-98,192-201` |
| 11 | Database | `webserver_config.json → database` (encrypted), mặc định 127.0.0.1:3306 atg_order_system | `db/mysql_client.py` |
| 12 | StorageResolver | `core/video_path_resolver.py`: ưu tiên `relative_path` rồi `file_path`; roots = `video.storage_roots` / `storage_root` config + `storage_locations.base_path` (cache) + fallback quét ổ đĩa `X:\VIDEO`, `X:\DEBUG`, `X:\ATG_DataBackup`… (lru_cache). Dùng `packing_videos.storage_code/relative_path` (WEB-NAS-1A/B/C) | |
| 13 | Cạnh EXE | `webserver_config.json` (bắt buộc, gắn user), `logs\`, `web_cache\mp4\`, `bin\ffmpeg.exe` (hoặc `ffmpeg\bin\`), `HUONG_DAN…txt` | |
| – | Port | `app.port` mặc định **8088**, host 0.0.0.0 (giá trị thật nằm trong config DPAPI — chưa đọc được trong audit) | |

---

## 4. MultiView dependencies (`D:\PYTHON\MULTIPLAY`)

| # | Hạng mục | Hiện trạng | Nguồn |
|---|---|---|---|
| 1 | EXE | `dist\ATG-MultiPlay.exe` (onefile, `console=False`, icon.ico, antn.png) | `ATG-MultiPlay.spec` |
| 2 | Config | `dirname(sys.executable)\config.json` khi frozen ✅ (source: dir của `sys.argv[0]`). Plaintext. **Được thiết kế đọc chung config.json của Recorder** (thông báo lỗi: *"config.json cua ATG Recorder"*); file config.json trong project là bản copy config Recorder (có cameras, record_*, db…). Chỉ dùng `play_path`/`storage_path`/`video_path` + `db` | `core/config_manager.py` |
| 3 | Logs/cache/temp | `app_root\logs\multiplay_merge.log`; output ghép `<out>.part.mp4` cạnh file output; `video_index.json`/`index\` (chế độ index cũ) ghi trong storage root; không có temp riêng | `core/video_merge_worker.py:163-170` |
| 4 | ffmpeg/ffprobe | `core/ffmpeg_locator.py`: `_MEIPASS\bin` (**bundle cả ffmpeg+ffprobe vào EXE** nếu có `bin\` lúc build) → `app_root\bin` → `app_root` → PATH. Không có hardcode | |
| 5 | Database | `config.json → db` (pymysql), `connect_timeout=5`, **không có read_timeout**. Query `packing_videos … WHERE file_path IS NOT NULL ORDER BY created_at DESC LIMIT 10000` **mỗi 5 giây** (`db_refresh_timer.start(5000)`) + `os.path.exists()` từng file | `core/database_reader.py`, `ui/main_window.py:216` |
| 6 | StorageResolver | **KHÔNG có**. Chỉ dùng `file_path` (absolute) hoặc `storage_root + file_path`. Không đọc `storage_code`/`relative_path`/`storage_locations` | |
| 7 | Local/NAS lookup | **Chỉ Local**. Với Recorder `delete_local_after_sync=true`, video đã sync NAS và bị xóa Local sẽ **biến mất khỏi MultiView** (bị lọc bởi `os.path.exists`) | ⚠ rủi ro nghiệp vụ |
| 8 | DLL/resource | **VLC bắt buộc** (`python-vlc`): tìm `dir(sys.argv[0])\bin\vlc`, `…\vlc`, `C:\Program Files\VideoLAN\VLC`, `C:\Program Files (x86)\VideoLAN\VLC`; không bundle → máy đích phải cài VLC. PyAV (`av`) + numpy bundle trong EXE. `icon.ico`, `antn.png` bundle | `ui/player_vlc_widget.py:6-33` |
| 9 | Startup | Không có | |
| 10 | Hardcode | VLC Program Files paths; `C:\ProgramData\ATGMultiPlay\license_cache.dat` (license_manager — **không được gọi**, dead code); `license_cache.json` trong project không dùng; `utils.resource_path` dùng `os.path.abspath(".")` khi chạy source (CWD) | |
| – | Port / single-instance | Không mở port. **Không có single-instance** | |
| – | Build | `build_onefile.ps1` dùng `python` trong PATH (chưa khóa .venv/3.10 như 2 app kia). `.venv` (C:\Python310, 3.10.11) đang bị track trong git và có thay đổi (có sẵn, không do audit) | |

---

## 5. FFmpeg / FFprobe lookup comparison

| Thứ tự | Recorder | WebServer | MultiView |
|---|---|---|---|
| 0 | `cameras[].ffmpeg_path` (config) | `video.ffmpeg_path` (config), env `FFMPEG_PATH` | – |
| Bundle | `_MEIPASS\bin\ffmpeg.exe` ✅ (bundle bắt buộc) | ❌ không bundle | `_MEIPASS\bin\ffmpeg.exe`, `ffprobe.exe` ✅ |
| APP_DIR | `_MEIPASS\ffmpeg.exe` (không phải APP_DIR!) | `APP_DIR\bin\ffmpeg.exe`, `APP_DIR\ffmpeg\bin\ffmpeg.exe` | `APP_DIR\bin\`, `APP_DIR\` |
| CWD | – | `CWD\bin\ffmpeg.exe` | – |
| Legacy hardcode | `C:\ffmpeg\bin\ffmpeg.exe` | `D:\PYTHON-TCR\bin`, `D:\PYTHON-TCR\1. EXE\ATG_AI_SYSTEM_RECORD\{bin,ffmpeg\bin}` | – |
| PATH | `ffmpeg` | `ffmpeg` | `ffmpeg`, `ffprobe` |
| ffprobe | cạnh ffmpeg → `ffprobe` PATH | không dùng | như ffmpeg |
| SUITE_ROOT\bin | ❌ | ❌ | ❌ |

**Đánh giá chuẩn hóa** theo thứ tự `<SUITE_ROOT>\bin` → `<APP_DIR>\bin` → PATH → legacy:

- Khả thi cho cả 3. `SUITE_ROOT` nên xác định = `dirname(APP_DIR)` **chỉ khi** tồn tại `SUITE_ROOT\bin\ffmpeg.exe` (không đoán mò), có thể thêm env `ATG_SUITE_ROOT` để override.
- **Giữ config override** (`ffmpeg_path`) ở đầu danh sách để không phá cấu hình đang chạy.
- **Recorder**: nên giữ ffmpeg **bundle** làm ưu tiên cao cho luồng record (ổn định realtime, không phụ thuộc file ngoài). Đề xuất thứ tự Recorder: config → bundle `_MEIPASS\bin` → `SUITE_ROOT\bin` → `APP_DIR\bin` → `C:\ffmpeg\bin` → PATH. (Nếu muốn dùng chung SUITE ffmpeg cho record → phải test RTSP/pre-record lại, rủi ro cao hơn.)
- **WebServer**: thêm `SUITE_ROOT\bin` trước `APP_DIR\bin`; giữ các candidate cũ phía sau (backward compatible).
- **MultiView**: thêm `SUITE_ROOT\bin` sau bundle hoặc trước `APP_DIR\bin`.

File cần sửa ở SUITE-1B:

| App | File | Hàm |
|---|---|---|
| Recorder | `services/record_worker.py` | `_find_ffmpeg()`, `FFMPEG_PATHS` |
| Recorder | `services/pre_record.py` (dòng ~150) | ffprobe lookup |
| Recorder | (mới) `core/suite_paths.py` hoặc thêm vào `core/resource_paths.py` | `suite_root()`, `suite_bin()` |
| WebServer | `services/video_stream_service.py` | `locate_ffmpeg()` |
| WebServer | `core/path_utils.py` | thêm `suite_root()` |
| MultiView | `core/ffmpeg_locator.py` | `_find_executable()` |

---

## 6. Config location comparison

| App | File | Vị trí | Phụ thuộc CWD? | Mã hóa | Rủi ro shortcut/startup |
|---|---|---|---|---|---|
| Recorder | `config.json` | cạnh EXE | **Có** (relative) nhưng được sửa bằng `os.chdir(exe_dir)` khi frozen. Chạy source từ thư mục khác → đọc sai config | Plaintext (DB password) | Thấp với EXE (chdir chạy ở đầu main.py). Nhưng `license/*` được import **trước** chdir (chỉ dùng %PROGRAMDATA% → OK). Nếu module nào đọc `config.json` lúc import trước dòng 15 → sai; hiện `core.config_manager` import trước nhưng chỉ đọc lazy → OK |
| WebServer | `webserver_config.json` | `app_root()` | Không ✅ | DPAPI current-user | **Chạy dưới user khác (service/Task Scheduler SYSTEM) → config bị đổi tên .unreadable + reset mặc định** |
| MultiView | `config.json` | `dirname(sys.executable)` | Không (frozen) ✅; source dùng argv[0] | Plaintext | Thấp. Nhưng hiện **dùng chung schema/bản copy config Recorder** → nếu đặt MultiView vào folder riêng phải có config.json riêng (tối thiểu `storage_path` + `db`) |

→ **Không gộp config**. Ở target, MultiView cần `MultiView\config.json` riêng (tối giản), không trỏ vào `Recorder\config.json`.

---

## 7. Log / cache / temp comparison

| App | Log | Cache | Temp |
|---|---|---|---|
| Recorder | `<APP>\logs\camera_events.log`, `license.log`; `<APP>\barcode_log.json` | `hr\employees.json`; `data\report.db`, `db\packing.db` (chỉ ở project, không bundle) | `%TEMP%\_MEIxxxx` (~177 MB/lần), `%TEMP%\atg_digicam.lock` |
| WebServer | `<APP>\logs\webserver.log` | `<APP>\web_cache\mp4\` (MP4 convert) | `%TEMP%\_MEIxxxx` |
| MultiView | `<APP>\logs\multiplay_merge.log` | – | `%TEMP%\_MEIxxxx`; `*.part.mp4` cạnh output |

Tên file log **khác nhau** và mỗi app ghi vào `logs\` của thư mục riêng → khi mỗi app ở folder riêng (`Recorder\logs`, `WebServer\logs`, `MultiView\logs`) **không bị ghi chung**. ⚠ Nếu đặt 2 app chung 1 thư mục thì vẫn khác tên file, nhưng không nên.

---

## 8. Startup / port / process comparison

| | Recorder | WebServer | MultiView |
|---|---|---|---|
| Port | Không (web_server/http_server 18080 là dead code) | **8088** (default, host 0.0.0.0) | Không |
| Single-instance | File lock `%TEMP%\atg_digicam.lock` (per-user) | Mutex `Global\ATG_WEBSERVER_SINGLE_INSTANCE` (toàn máy) | **Không có** |
| Tray | Không (Qt window) | `ATG_WEBSERVER_TRAY` | Không |
| Startup Windows | Không | HKCU Run `ATG_WEBSERVER` + `Startup\ATG_WEBSERVER.lnk` (`--minimized`, path tuyệt đối) | Không |
| GUI framework | PySide6 | Win32 tray + Flask/waitress | PyQt6 + VLC |

Chạy đồng thời 3 app: **không có xung đột định danh** (lock/mutex/tên khác nhau, chỉ WebServer mở port). PySide6 và PyQt6 ở 2 process riêng → không xung đột DLL (mỗi onefile có `_MEI` riêng). Tải chung chủ yếu: MySQL (MultiView poll 5 s LIMIT 10000) và I/O ổ Local/NAS.

---

## 9. Database / StorageResolver comparison

| | Recorder | WebServer | MultiView |
|---|---|---|---|
| Vai trò | **Ghi** packing_videos, video_storage_locations, storage_locations; NAS sync; (NAS-META-1B) ghi storage_code/relative_path | Đọc | Đọc |
| Nguồn DB config | `config.json` plaintext | `webserver_config.json` DPAPI | `config.json` plaintext |
| Resolver | `services/storage_resolver.py` (vsl VERIFIED, Local → NAS) | `core/video_path_resolver.py` (relative_path/file_path + storage_locations + config roots + quét ổ đĩa) | **Không có** — chỉ `file_path` + `os.path.exists` |
| Thấy video chỉ còn trên NAS | ✅ | ✅ | ❌ |
| Phụ thuộc Recorder chạy | – | Không ✅ | Không ✅ |

Kiến trúc mong muốn (Recorder → DB → NAS; WebServer/MultiView → DB → StorageResolver → Local/NAS) **đạt ở WebServer, CHƯA đạt ở MultiView**.

---

## 10. Hardcoded path inventory

| App | Path | File | Mức |
|---|---|---|---|
| Recorder | `C:\ffmpeg\bin\ffmpeg.exe` | services/record_worker.py:38, build_onefile.spec | legacy fallback |
| Recorder | `C:\Program Files\(x86)\VideoLAN\VLC\vlc.exe` | ui/pages/camera_grid_page.py:195-196,272 | tính năng mở VLC ngoài |
| Recorder | `C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe`, `C:\Windows\System32\nvidia-smi.exe` | core/gpu_acceleration.py:8-9 | OK (system) |
| Recorder | `C:/Windows/Fonts/arial.ttf`, `segoeui.ttf` | hr/qr_generator.py | OK (system) |
| Recorder | `%PROGRAMDATA%\CCTV_AI_SYSTEM\license\*` | license/paths.py | OK (máy) |
| Recorder | `%TEMP%\atg_digicam.lock` | main.py:74 | OK |
| Recorder | `config.json`, `logs/…`, `barcode_log.json` relative | core/config_manager.py, system_logger.py, core/logger.py, services/scanner.py, services/mysql_client.py, ui/pages/log_page.py, log_panel.py | phụ thuộc chdir |
| Recorder | default `storage_path`, `web_index_url http://127.0.0.1:8088/` | core/config_manager.py | default |
| WebServer | `D:\PYTHON-TCR\bin\ffmpeg.exe`, `D:\PYTHON-TCR\1. EXE\ATG_AI_SYSTEM_RECORD\bin\ffmpeg.exe`, `…\ffmpeg\bin\ffmpeg.exe` | services/video_stream_service.py:66-68, build_onefile.bat | legacy dev path |
| WebServer | `Path.cwd()\bin\ffmpeg.exe` | services/video_stream_service.py:65 | phụ thuộc CWD |
| WebServer | Quét `A:..Z:\{VIDEO,DEBUG,ATG_DataBackup,…}` | core/video_path_resolver.py:10,164 | fallback khi không có root |
| MultiView | `C:\Program Files\VideoLAN\VLC`, `C:\Program Files (x86)\VideoLAN\VLC` | ui/player_vlc_widget.py | **bắt buộc có VLC** |
| MultiView | `C:\ProgramData\ATGMultiPlay\license_cache.dat` | core/license_manager.py | dead code |
| MultiView | `os.path.abspath(".")` (source mode) | utils.py | chỉ khi chạy source |

---

## 11. Shared resources that CAN be centralized

1. `ffmpeg.exe`, `ffprobe.exe` → `SUITE_ROOT\bin\` (WebServer, MultiView chắc chắn; Recorder làm fallback sau bundle).
2. `README.txt` / hướng dẫn cài đặt chung ở `SUITE_ROOT`.
3. (Tùy chọn) VLC portable → `SUITE_ROOT\bin\vlc\` — **cần sửa MultiView** lookup (hiện tìm theo dir(argv[0])\bin\vlc, tức `MultiView\bin\vlc`).
4. Tài liệu SQL (`db/*.sql`) có thể để `SUITE_ROOT\docs\`.
5. Kết nối DB **cùng giá trị** nhưng **không cùng file** (xem §12).

## 12. Resources that MUST remain app-specific

- **Config**: `Recorder\config.json` (plaintext, runtime), `WebServer\webserver_config.json` (DPAPI, gắn Windows user), `MultiView\config.json`.
- **Logs**: `<App>\logs\`.
- **Cache**: `WebServer\web_cache\`, Recorder `hr\employees.json`, `barcode_log.json`.
- **Single-instance/lock/mutex/tray/startup identifiers** (giữ nguyên: `atg_digicam.lock`, `Global\ATG_WEBSERVER_SINGLE_INSTANCE`, `ATG_WEBSERVER_TRAY`, `ATG_WEBSERVER` Run key/.lnk).
- **License**: Recorder `%PROGRAMDATA%\CCTV_AI_SYSTEM` (giữ nguyên).
- **ffmpeg bundle bên trong Recorder EXE** (đảm bảo realtime record).
- EXE name: `atg_digicam.exe`, `ATG_WEBSERVER.exe`, `ATG-MultiPlay.exe`.

---

## 13. Proposed target folder tree

```
D:\ATG_DIGICAM_SUITE\
│  README.txt
│
├─ bin\
│   ffmpeg.exe
│   ffprobe.exe
│   (tùy chọn) vlc\  libvlc.dll, libvlccore.dll, plugins\
│
├─ Recorder\
│   atg_digicam.exe            (onefile, ffmpeg bundle bên trong)
│   config.json                (riêng, plaintext)
│   hr\employees.json          (tự tạo)
│   logs\camera_events.log, license.log
│   barcode_log.json           (tự tạo)
│
├─ WebServer\
│   ATG_WEBSERVER.exe
│   webserver_config.json      (DPAPI – phải tạo/lưu lại trên đúng máy + user)
│   HUONG_DAN_CAI_DAT_CHAY_AN.txt
│   logs\webserver.log
│   web_cache\mp4\
│
└─ MultiView\
    ATG-MultiPlay.exe
    config.json                (riêng, tối giản: storage_path + db)
    logs\multiplay_merge.log
```

Ngoài suite (giữ nguyên): `%PROGRAMDATA%\CCTV_AI_SYSTEM\license\`, `HKCU\…\Run\ATG_WEBSERVER`, `shell:startup\ATG_WEBSERVER.lnk`, `%TEMP%\atg_digicam.lock`.

---

## 14. Migration risks

| # | Rủi ro | Mức | Giảm thiểu |
|---|---|---|---|
| R1 | **MultiView không thấy video đã xóa Local sau NAS sync** (Recorder đang `delete_local_after_sync=true`) — đã là lỗi hiện tại, không do suite | **Cao** | SUITE-1B/phase riêng: MultiView dùng `storage_code/relative_path` + `storage_locations` (giống WebServer). Không thuộc phạm vi "không sửa MultiView playback" → cần người dùng duyệt |
| R2 | WebServer config DPAPI: copy sang máy khác / chạy user khác → bị đổi tên `.unreadable` và **reset mặc định** | Cao | Copy `webserver_config.json` trên **cùng máy + cùng user**; máy mới → cấu hình lại qua UI. Ghi rõ README. Backup trước khi di chuyển |
| R3 | WebServer Startup lưu path tuyệt đối EXE cũ → sau di chuyển, Windows vẫn chạy EXE cũ (hoặc không chạy) | Cao | Tắt Startup ở bản cũ **trước**, di chuyển, bật lại trong bản mới (Settings → Startup) |
| R4 | Recorder `config.json` relative + chdir: chạy bản source từ CWD khác đọc sai config | Thấp (EXE OK) | Không đổi; hoặc SUITE-1B chuyển sang `app_path("config.json")` (rủi ro chạm core → cân nhắc) |
| R5 | MultiView hiện đọc config kiểu Recorder (có thể đang đặt chung thư mục với Recorder) → tách folder sẽ báo "Loi Config" | Trung bình | Tạo `MultiView\config.json` riêng trước khi chạy |
| R6 | MultiView cần VLC cài sẵn (không bundle) | Trung bình | Kiểm tra VLC trên máy đích; hoặc VLC portable ở `MultiView\bin\vlc` |
| R7 | MultiView poll DB 5 s, LIMIT 10000 + `os.path.exists` (có thể là UNC) → tải DB/IO, UI lag | Trung bình | Không đổi trong suite; ghi nhận cho phase tối ưu |
| R8 | 2 bản ffmpeg khác version (bundle Recorder vs SUITE\bin) | Thấp | Ghi version ffmpeg trong README; test record + web convert |
| R9 | WebServer `dist\ffmpeg\bin` vs build bat copy `dist\bin` — không nhất quán layout | Thấp | Chuẩn hóa `SUITE_ROOT\bin` |
| R10 | `web_index_url` Recorder = `http://127.0.0.1:48080` khác WebServer default 8088 | Thấp | Xác minh port thật trong WebServer settings |
| R11 | Recorder có 2 bản dist (onefile + onedir) → nhầm bản khi copy | Thấp | Chốt dùng `dist\atg_digicam.exe` (có SHA256) |
| R12 | Onefile giải nén `%TEMP%` mỗi lần (Recorder 177 MB) — ổ C đầy/antivirus chặn | Thấp | Không đổi; theo dõi |
| R13 | MultiView không single-instance → mở nhiều cửa sổ, nhân tải DB | Thấp | Tùy chọn thêm mutex ở phase sau |

---

## 15. Exact files that would need changes in SUITE-1B

Tối thiểu (FFmpeg dùng chung, không đụng nghiệp vụ):

| App | File | Thay đổi dự kiến |
|---|---|---|
| Recorder | `core/resource_paths.py` | + `suite_root()` / `suite_bin_path(name)` (read-only helper) |
| Recorder | `services/record_worker.py` | `_find_ffmpeg()`: thêm `SUITE_ROOT\bin`, `APP_DIR\bin` **sau** bundle; giữ `C:\ffmpeg` + PATH |
| Recorder | `services/pre_record.py` | ffprobe: thêm `SUITE_ROOT\bin\ffprobe.exe`, `APP_DIR\bin` trước PATH |
| WebServer | `core/path_utils.py` | + `suite_root()` |
| WebServer | `services/video_stream_service.py` | `locate_ffmpeg()`: thêm `SUITE_ROOT\bin` sau config/env; giữ legacy phía sau |
| WebServer | `build_onefile.bat` | (tùy chọn) copy ffmpeg vào `dist\bin` — đã có; thêm ffprobe nếu cần |
| MultiView | `core/ffmpeg_locator.py` | `_find_executable()`: thêm `SUITE_ROOT\bin` |
| MultiView | `build_onefile.ps1` | khóa Python `.venv\Scripts\python.exe` → `C:\Python310` → `python` (giống 2 app kia) |
| Suite | (mới) `D:\ATG_DIGICAM_SUITE\README.txt` + script đóng gói `make_suite.ps1` (chỉ copy từ 3 `dist\`) | |
| Tests | `tests/test_suite_ffmpeg_lookup.py` (Recorder), test tương tự WebServer, `tests/test_ffmpeg_locator.py` (MultiView, đã có) | |

Tách riêng (cần duyệt, **không** thuộc SUITE-1B tối thiểu):

- MultiView StorageResolver (R1): `core/database_reader.py`, `ui/main_window.py` (load_index_from_database).
- MultiView VLC từ `SUITE_ROOT\bin\vlc`: `ui/player_vlc_widget.py`.
- Recorder config tuyệt đối: `core/config_manager.py`, `services/mysql_client.py`, `system_logger.py`, `core/logger.py`.

---

## 16. Test plan — chạy đồng thời 3 app

Chuẩn bị: backup `Recorder\config.json`, `WebServer\webserver_config.json`, `MultiView\config.json`; tắt Startup WebServer bản cũ; ghi SHA256 3 EXE.

| # | Bước | Kỳ vọng |
|---|---|---|
| T1 | Chạy `Recorder\atg_digicam.exe` từ shortcut Desktop (Start in khác thư mục) | Đọc đúng `Recorder\config.json`; log vào `Recorder\logs\`; camera online |
| T2 | Chạy `WebServer\ATG_WEBSERVER.exe` | Tray `ATG_DIGICAM WebServer v1.0.0`; `http://127.0.0.1:<port>` mở; log `WebServer\logs\webserver.log`; config **không** bị đổi tên .unreadable |
| T3 | Chạy `MultiView\ATG-MultiPlay.exe` | Đọc `MultiView\config.json`; list đơn từ DB; VLC phát được |
| T4 | Chạy lần 2 mỗi app | Recorder: từ chối; WebServer: từ chối; MultiView: (hiện) mở thêm — ghi nhận |
| T5 | Scan QR + record 1 đơn test (3 app đang chạy) | Barcode/record realtime không trễ; file Local tạo đúng |
| T6 | Chờ NAS sync | `storage_code='NAS01'`, `relative_path` có giá trị; Recorder không lag |
| T7 | WebServer: play/stream + download MP4 video T5 | ffmpeg tìm từ `SUITE_ROOT\bin` (sau SUITE-1B); `web_cache\mp4` trong WebServer |
| T8 | MultiView: mở + ghép video T5 | ffmpeg/ffprobe OK; log `MultiView\logs\multiplay_merge.log` |
| T9 | Tắt Recorder → dùng WebServer & MultiView | Vẫn hoạt động (không phụ thuộc Recorder process) |
| T10 | Video đã xóa Local (NAS only) | WebServer phát được từ NAS; MultiView: **hiện sẽ không thấy** (R1) |
| T11 | Rút mạng NAS | Recorder vẫn record Local; WebServer báo lỗi file mềm; không crash |
| T12 | Đổi tên/xóa tạm `SUITE_ROOT\bin\ffmpeg.exe` | Recorder vẫn record (bundle); WebServer/MultiView fallback `APP_DIR\bin`/PATH hoặc báo lỗi rõ ràng |
| T13 | Reboot Windows với Startup WebServer bật trong bản suite | Chạy đúng `D:\ATG_DIGICAM_SUITE\WebServer\ATG_WEBSERVER.exe --minimized` |
| T14 | Kiểm tra `logs\` | 3 thư mục log riêng, không file log chung |
| T15 | Theo dõi 30 phút CPU/RAM/MySQL connections | Không tăng bất thường |

---

## Kết luận

Kiến trúc hiện tại đã tách process/port/lock rõ ràng, config và log của WebServer/MultiView gắn theo thư mục EXE, Recorder dựa vào `chdir` (hoạt động với EXE). Việc gom vào `D:\ATG_DIGICAM_SUITE` **khả thi** với thay đổi nhỏ (ffmpeg lookup ×3 app + build script MultiView + README/đóng gói). Điểm cần quyết định trước khi triển khai: **R1 (MultiView không có StorageResolver trong khi Recorder đang xóa Local sau NAS sync)** và **R2/R3 (DPAPI + Startup path của WebServer khi di chuyển)**.

RECORDER_CODE_CHANGED = NO
WEBSERVER_CODE_CHANGED = NO
MULTIVIEW_CODE_CHANGED = NO
PRODUCTION_FILES_MOVED = NO

SUITE_1A_READY_FOR_IMPLEMENTATION = YES
(YES cho SUITE-1B phạm vi ffmpeg/build/đóng gói; R1 MultiView StorageResolver cần phase riêng được duyệt)

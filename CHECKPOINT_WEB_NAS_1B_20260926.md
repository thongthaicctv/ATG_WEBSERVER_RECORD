# CHECKPOINT WEB-NAS-1B

Date: 2026-09-26

Project:
ATG_DIGICAM_WEBSERVER

Path:
D:\PYTHON\ATG_DIGICAM_WEBSERVER

Phase:
WEB-NAS-1B — New ATG_DIGICAM NAS Metadata Compatibility

## Result

PASS

## Recorder version used

ATG_DIGICAM v4.0.7.4

Recorder release tag:
ATG-DIGICAM-v4.0.7.4

## Test video

video_id:
1784

order_code:
SPXVN066477271639

packing_videos.storage_code:
NAS01

packing_videos.relative_path:
2026-09-26\SPXVN066477271639_C2_NA_20260926_094337.ts

packing_videos.file_path:
D:\VIDEO_DEBUG\2026-09-26\SPXVN066477271639_C2_NA_20260926_094337.ts

Local physical file:
DELETED / MISSING

NAS physical file:
\\192.168.23.200\cameraSihn\2026-09-26\SPXVN066477271639_C2_NA_20260926_094337.ts

NAS physical file:
EXISTS

## End-to-end Web test

Search order:
PASS

Video detail:
PASS

Play from NAS:
PASS

Download original TS from NAS:
PASS

Convert/download MP4 from NAS:
PASS

## Architecture validated

Database
→ packing_videos
→ storage_code + relative_path
→ storage_locations
→ NAS base_path
→ video_path_resolver
→ NAS physical file
→ Play / Download / MP4

WebServer does not require the Local video to remain available.

WebServer does not need to scan NAS to discover orders.

## Backward compatibility

Legacy video with:

storage_code = NULL
relative_path = NULL
file_path = old Local path

was also tested separately and successfully resolved from NAS.

WEB-NAS-1A:
PASS

WEB-NAS-1B:
PASS

DATABASE_SCHEMA_CHANGED = NO
WEBSERVER_BUSINESS_LOGIC_CHANGED = NO
STORAGE_RESOLVER_STATUS = PASS
NAS_ONLY_PLAYBACK = PASS
NAS_ONLY_ORIGINAL_DOWNLOAD = PASS
NAS_ONLY_MP4_DOWNLOAD = PASS

WEB_NAS_1B_STATUS = PASS

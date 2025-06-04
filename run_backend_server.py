import uvicorn
import argparse
import os
import sys 
import datetime
import traceback

_REAL_ORIGINAL_STDOUT = sys.stdout
_REAL_ORIGINAL_STDERR = sys.stderr
_debug_log_file_handle = None
_FINAL_DEBUG_LOG_FILE_PATH = None
_DEBUG_LOG_ENABLED = True 

from config.backend_settings import settings, update_settings_from_args

if __name__ == "__main__":
    current_stdout_before_redirect = sys.stdout
    current_stderr_before_redirect = sys.stderr

    parser = argparse.ArgumentParser(description="Nepenthe Backend API Service")
    parser.add_argument("--host", default=None, help="API Host to bind")
    parser.add_argument("--port", type=int, default=None, help="API Port to bind")
    parser.add_argument("--video_paths", default=None, help="Video library paths (comma-separated)")
    parser.add_argument("--db-file-path", default=None, help="Full path to the SQLite database file")
    parser.add_argument("--thumbnails-storage-path", default=None, help="Full path to the thumbnails storage directory")
    parser.add_argument("--ffmpeg-path", default=None, help="Full path to ffmpeg executable")
    parser.add_argument("--ffprobe-path", default=None, help="Full path to ffprobe executable")

    args = None
    try:
        args = parser.parse_args()
    except SystemExit as e_argparse:
        if current_stderr_before_redirect:
            print(f"Argparse exit: {e_argparse.code}", file=current_stderr_before_redirect, flush=True)
        sys.exit(e_argparse.code)

    if _DEBUG_LOG_ENABLED:
        app_data_dir_for_log = None
        if args and args.db_file_path:
            potential_data_dir = os.path.dirname(os.path.abspath(args.db_file_path))
            if os.path.isdir(potential_data_dir):
                app_data_dir_for_log = potential_data_dir
        
        if not app_data_dir_for_log:
            app_data_dir_for_log = os.path.expanduser("~")
            if current_stderr_before_redirect:
                 print(f"Warning: Log defaulting to user home: {app_data_dir_for_log}", file=current_stderr_before_redirect, flush=True)
        
        _FINAL_DEBUG_LOG_FILE_PATH = os.path.join(app_data_dir_for_log, "nepenthe_backend.log") 

        try:
            if not os.path.exists(app_data_dir_for_log):
                os.makedirs(app_data_dir_for_log, exist_ok=True)
            
            _debug_log_file_handle = open(_FINAL_DEBUG_LOG_FILE_PATH, "w", encoding="utf-8", buffering=1)
            
            sys.stdout = _debug_log_file_handle
            sys.stderr = _debug_log_file_handle

            print(f"--- Nepenthe Backend Log Start (File: {_FINAL_DEBUG_LOG_FILE_PATH}) ---", flush=True)
            print(f"Timestamp: {datetime.datetime.now()}", flush=True)
            print(f"Python Executable: {sys.executable}", flush=True)
            print(f"CWD: {os.getcwd()}", flush=True)
            print(f"sys.argv: {sys.argv}", flush=True)
        except Exception as e_log_setup:
            sys.stdout = current_stdout_before_redirect
            sys.stderr = current_stderr_before_redirect
            if sys.stderr:
                print(f"CRITICAL: Failed to setup log file '{_FINAL_DEBUG_LOG_FILE_PATH}': {e_log_setup}", file=sys.stderr, flush=True)
                traceback.print_exc(file=sys.stderr)
            _DEBUG_LOG_ENABLED = False
            if _debug_log_file_handle:
                try: _debug_log_file_handle.close()
                except: pass
                _debug_log_file_handle = None
    
    from config.backend_settings import settings, update_settings_from_args
    
    effective_video_paths_str = None
    if args.video_paths is not None:
        effective_video_paths_str = args.video_paths
    elif os.getenv("NEPENTHE_VIDEO_PATHS"):
        effective_video_paths_str = os.getenv("NEPENTHE_VIDEO_PATHS")
    else:
        effective_video_paths_str = ",".join(settings.video_paths) if settings.video_paths else ""
    
    final_args_for_update = argparse.Namespace(**vars(args))
    final_args_for_update.video_paths = effective_video_paths_str
    if final_args_for_update.host is None: final_args_for_update.host = settings.api_host
    if final_args_for_update.port is None: final_args_for_update.port = settings.api_port

    update_settings_from_args(final_args_for_update) 
    
    print(f"Effective settings after update:", flush=True)
    print(f"  API Host: {settings.api_host}", flush=True)
    print(f"  API Port: {settings.api_port}", flush=True)
    print(f"  Video Paths: {settings.video_paths}", flush=True)
    print(f"  DB Override: {settings._db_file_path_override}", flush=True)
    print(f"  DB URL: {settings.database_url}", flush=True)
    print(f"  Thumbnails Path: {settings.thumbnails_storage_path}", flush=True)
    print(f"  FFmpeg: {settings.ffmpeg_path}", flush=True)
    print(f"  FFprobe: {settings.ffprobe_path}", flush=True)

    try:
        from apps.backend_fastapi_app import app 
        print("Successfully imported FastAPI app instance.", flush=True)
    except Exception as e_import_app:
        print(f"CRITICAL: Failed to import FastAPI app instance: {e_import_app}", flush=True)
        traceback.print_exc()
        if _debug_log_file_handle and not _debug_log_file_handle.closed: _debug_log_file_handle.close()
        sys.stdout = _REAL_ORIGINAL_STDOUT
        sys.stderr = _REAL_ORIGINAL_STDERR
        sys.exit(1)

    if settings.ffmpeg_path:
        try:
            from components import video_metadata_extractor
            video_metadata_extractor.FFMPEG_PATH = settings.ffmpeg_path
            print(f"Set video_metadata_extractor.FFMPEG_PATH: {settings.ffmpeg_path}", flush=True)
        except Exception as e_ffmpeg_set:
            print(f"Warning: Could not set FFMPEG_PATH: {e_ffmpeg_set}", flush=True)
    if settings.ffprobe_path:
        try:
            from components import video_metadata_extractor
            video_metadata_extractor.FFPROBE_PATH = settings.ffprobe_path
            print(f"Set video_metadata_extractor.FFPROBE_PATH: {settings.ffprobe_path}", flush=True)
        except Exception as e_ffprobe_set:
            print(f"Warning: Could not set FFPROBE_PATH: {e_ffprobe_set}", flush=True)

    print(f"Starting Uvicorn server on host={settings.api_host}, port={settings.api_port}", flush=True)

    try:
        uvicorn.run(
            app,
            host=settings.api_host,
            port=settings.api_port,
            log_level="info",
            access_log=False 
        )
    except Exception as e_uvicorn:
        print(f"CRITICAL: Uvicorn run failed: {e_uvicorn}", flush=True)
        traceback.print_exc()
    finally:
        if _debug_log_file_handle and not _debug_log_file_handle.closed:
            print("--- Nepenthe Backend Log End ---", flush=True)
            _debug_log_file_handle.close()
        sys.stdout = _REAL_ORIGINAL_STDOUT
        sys.stderr = _REAL_ORIGINAL_STDERR
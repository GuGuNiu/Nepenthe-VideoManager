import uvicorn
import argparse
import os
import sys 

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # 当通过 PyInstaller 打包并以 --windowed 模式运行时，sys.stdout 和 sys.stderr 可能为 None
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w') # 重定向到 null 设备
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w') # 重定向到 null 设备

if sys.stdout and sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

if sys.stderr and sys.stderr.encoding != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


from config.backend_settings import settings, update_settings_from_args
from apps.backend_fastapi_app import app 

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nepenthe Backend API Service")
    parser.add_argument("--host", default=os.getenv("NEPENTHE_API_HOST", settings.api_host), help="API Host to bind")
    parser.add_argument("--port", type=int, default=int(os.getenv("NEPENTHE_API_PORT", settings.api_port)), help="API Port to bind")
    parser.add_argument("--video_paths", default=os.getenv("NEPENTHE_VIDEO_PATHS", ""), help="Video library paths (comma-separated)")
    parser.add_argument("--db-file-path", default=None, help="Full path to the SQLite database file")
    parser.add_argument("--thumbnails-storage-path", default=None, help="Full path to the thumbnails storage directory")
    parser.add_argument("--ffmpeg-path", default=None, help="Full path to ffmpeg executable")
    parser.add_argument("--ffprobe-path", default=None, help="Full path to ffprobe executable")
    args = parser.parse_args()

    # 将 video_paths 从环境变量或参数中正确处理为列表
    if args.video_paths: # 来自命令行参数
        pass # update_settings_from_args 会处理
    elif os.getenv("NEPENTHE_VIDEO_PATHS"): # 来自环境变量
        args.video_paths = os.getenv("NEPENTHE_VIDEO_PATHS")
    else: # 使用 settings 中的默认值（如果存在）
        args.video_paths = ",".join(settings.video_paths) if settings.video_paths else ""

    update_settings_from_args(args) 
    
    if settings.ffmpeg_path:
        try:
            from components import video_metadata_extractor
            video_metadata_extractor.FFMPEG_PATH = settings.ffmpeg_path
            print(f"Dynamically set video_metadata_extractor.FFMPEG_PATH to: {settings.ffmpeg_path}")
        except ImportError:
            print("Warning: Could not import video_metadata_extractor to set FFMPEG_PATH")
    if settings.ffprobe_path:
        try:
            from components import video_metadata_extractor
            video_metadata_extractor.FFPROBE_PATH = settings.ffprobe_path
            print(f"Dynamically set video_metadata_extractor.FFPROBE_PATH to: {settings.ffprobe_path}")
        except ImportError:
            print("Warning: Could not import video_metadata_extractor to set FFPROBE_PATH")

    uvicorn.run(
    app,
    host=settings.api_host,
    port=settings.api_port,
    log_level="info",
    access_log=False  # 关闭 access log（可选）
    )

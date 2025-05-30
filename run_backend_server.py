
import uvicorn
import argparse
import os
import sys 




if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception as e:
        print(f"Warning: Failed to reconfigure stdout encoding to utf-8: {e}")
if sys.stderr.encoding != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception as e:
        print(f"Warning: Failed to reconfigure stderr encoding to utf-8: {e}")


from config.backend_settings import settings, update_settings_from_args
from apps.backend_fastapi_app import app

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="忘忧露后端API服务")
    
    parser.add_argument("--host", default=os.getenv("NEPENTHE_HOST", settings.api_host), help="绑定主机")
    parser.add_argument("--port", type=int, default=int(os.getenv("NEPENTHE_PORT", settings.api_port)), help="绑定端口")
    parser.add_argument("--video_paths", default="", help="视频库路径 (逗号分隔)")
    
    args = parser.parse_args()

    update_settings_from_args(args) 

    
    
    uvicorn.run(app, host=settings.api_host, port=settings.api_port, log_level="info")
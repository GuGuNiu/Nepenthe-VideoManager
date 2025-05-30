# config/backend_settings.py
from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    video_paths: list[str] = []
    
    _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
    _data_storage_dir = os.path.join(_project_root, "data")

    database_file_name: str = "nepenthe_videos.db"
    _db_file_path = os.path.join(_data_storage_dir, database_file_name)
    database_url: str = f"sqlite:///{_db_file_path}"

    _thumbnails_dir_name: str = "thumbnails"
    thumbnails_storage_path: str = os.path.join(_data_storage_dir, _thumbnails_dir_name)
    thumbnails_base_url: str = "/static/thumbnails" # 这是相对URL路径

    class Config:
        env_prefix = "NEPENTHE_"

settings = Settings()

def _ensure_dir_exists(dir_path: str, dir_description: str):
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path, exist_ok=True)
            print(f"创建{dir_description}目录: {dir_path}")
        except Exception as e:
            print(f"创建{dir_description}目录 {dir_path} 失败: {e}")
    elif not os.path.isdir(dir_path):
        print(f"错误: 路径 {dir_path} 已存在但不是一个目录，无法用作{dir_description}目录。")

def update_settings_from_args(args):
    global settings 
    if args.host is not None: settings.api_host = args.host
    if args.port is not None: settings.api_port = args.port
    if args.video_paths: 
        settings.video_paths = [path.strip() for path in args.video_paths.split(',') if path.strip()]
    else:
        settings.video_paths = [] 
    
    _ensure_dir_exists(settings._data_storage_dir, "数据存储根")
    _ensure_dir_exists(settings.thumbnails_storage_path, "缩略图")

    print(f"配置已更新: Host={settings.api_host}, Port={settings.api_port}, VideoPaths={settings.video_paths}")
    print(f"数据库文件将位于: {settings.database_url.replace('sqlite:///', '')}")
    print(f"缩略图将存储于: {settings.thumbnails_storage_path}")
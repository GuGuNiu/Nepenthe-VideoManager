# config/backend_settings.py
import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    video_paths: list[str] = []
    
    # 尝试更动态地获取项目根目录，假设此配置文件在项目根的子目录中
    # __file__ 是当前文件 (config/backend_settings.py)
    # os.path.dirname(__file__) 是 config 目录
    # os.path.dirname(os.path.dirname(__file__)) 是项目根目录
    _nepenthe_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    _data_storage_dir_default_for_dev = os.path.join(_nepenthe_project_root, "data")

    database_file_name: str = "nepenthe_videos.db"
    _db_file_path_override: Optional[str] = None
    
    _thumbnails_dir_name: str = "thumbnails"
    _thumbnails_storage_path_override: Optional[str] = None

    ffmpeg_path_override: Optional[str] = None
    ffprobe_path_override: Optional[str] = None
    thumbnails_base_url: str = "/static/thumbnails"

    @property
    def database_url(self) -> str:
        path_to_use = self._db_file_path_override
        if not path_to_use:
            path_to_use = os.path.join(self._data_storage_dir_default_for_dev, self.database_file_name)
        
        db_dir = os.path.dirname(path_to_use)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        return f"sqlite:///{path_to_use}"

    @property
    def thumbnails_storage_path(self) -> str:
        path_to_use = self._thumbnails_storage_path_override
        if not path_to_use:
            base_data_dir_for_thumbs = self._data_storage_dir_default_for_dev
            # 如果数据库路径被覆盖了，并且我们希望缩略图也在其附近，则调整 base_data_dir_for_thumbs
            if self._db_file_path_override:
                 potential_data_dir = os.path.dirname(self._db_file_path_override)
                 # 简单假设：如果覆盖的db路径不在默认的data_dev_default下，则缩略图也放在db同级
                 if os.path.abspath(potential_data_dir) != os.path.abspath(self._data_storage_dir_default_for_dev):
                     base_data_dir_for_thumbs = potential_data_dir

            path_to_use = os.path.join(base_data_dir_for_thumbs, self._thumbnails_dir_name)
        
        if not os.path.exists(path_to_use):
            os.makedirs(path_to_use, exist_ok=True)
        return path_to_use
    
    @property
    def ffmpeg_path(self) -> Optional[str]:
        return self.ffmpeg_path_override
    
    @property
    def ffprobe_path(self) -> Optional[str]:
        return self.ffprobe_path_override

    class Config:
        env_prefix = "NEPENTHE_"

settings = Settings()

def update_settings_from_args(args):
    # ... (这个函数应该保持与我上一条回复中的一致，它只负责设置 _override 属性) ...
    global settings 
    if hasattr(args, 'host') and args.host is not None: settings.api_host = args.host
    if hasattr(args, 'port') and args.port is not None: settings.api_port = args.port
    
    if hasattr(args, 'video_paths') and args.video_paths: 
        settings.video_paths = [path.strip() for path in args.video_paths.split(',') if path.strip()]
    elif not settings.video_paths: 
        settings.video_paths = []
    
    if hasattr(args, 'db_file_path') and args.db_file_path:
        settings._db_file_path_override = os.path.abspath(args.db_file_path) # 确保是绝对路径
            
    if hasattr(args, 'thumbnails_storage_path') and args.thumbnails_storage_path:
        settings._thumbnails_storage_path_override = os.path.abspath(args.thumbnails_storage_path) # 确保是绝对路径

    if hasattr(args, 'ffmpeg_path') and args.ffmpeg_path:
        settings.ffmpeg_path_override = args.ffmpeg_path
    if hasattr(args, 'ffprobe_path') and args.ffprobe_path:
        settings.ffprobe_path_override = args.ffprobe_path
    
    final_db_url = settings.database_url # 触发 @property getter
    final_thumb_path = settings.thumbnails_storage_path # 触发 @property getter

    print(f"配置已更新: Host={settings.api_host}, Port={settings.api_port}, VideoPaths={settings.video_paths}")
    print(f"最终数据库文件将位于: {final_db_url.replace('sqlite:///', '')}")
    print(f"最终缩略图将存储于: {final_thumb_path}")
    if settings.ffmpeg_path: print(f"FFmpeg 路径: {settings.ffmpeg_path}")
    if settings.ffprobe_path: print(f"FFprobe 路径: {settings.ffprobe_path}")
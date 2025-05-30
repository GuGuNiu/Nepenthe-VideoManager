from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from config.backend_settings import settings
from routes import general_api
from tools.db_utils import create_db_and_tables, SessionLocal
import threading
import os
import sys
import mimetypes 

app = FastAPI(
    title="忘忧露视频管理API",
    description="Nepenthe Video Manager 的后端 API 服务。",
    version="0.1.0",
)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174", 
    "http://127.0.0.1:5174", 
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 确保目录存在
if not os.path.exists(settings.thumbnails_storage_path):
    try:
        os.makedirs(settings.thumbnails_storage_path, exist_ok=True)
    except Exception as e:
        print(f"启动时创建缩略图目录 {settings.thumbnails_storage_path} 失败: {e}")

if os.path.isdir(settings.thumbnails_storage_path):
    @app.get(settings.thumbnails_base_url + "/{filename:path}", tags=["Thumbnails"])
    async def get_thumbnail(filename: str):
        file_path = os.path.join(settings.thumbnails_storage_path, filename)
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            raise HTTPException(status_code=404, detail="Thumbnail not found")
        
        # 尝试获取 MIME 类型
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            mime_type = "application/octet-stream" # 默认类型
        
        with open(file_path, "rb") as f:
            content = f.read()
        return Response(content=content, media_type=mime_type)

    print(f"自定义缩略图服务已挂载: URL '{settings.thumbnails_base_url}/<filename>'")
else:
    print(f"警告: 缩略图目录 '{settings.thumbnails_storage_path}' 无效，无法挂载静态文件服务。")


@app.on_event("startup")
async def startup_event():
    print(f"忘忧露后端 (API) 正在启动，地址: http://{settings.api_host}:{settings.api_port}")
    print(f"视频库路径 (来自配置): {settings.video_paths}")
    print(f"数据库位置: {settings.database_url}")
    print(f"缩略图存储于: {settings.thumbnails_storage_path}")
    create_db_and_tables()
    print("后端服务已启动。视频库扫描需通过 API (/api/scan-library) 手动触发。")

app.include_router(general_api.router)

@app.get("/", tags=["Root"])
async def read_root_app():
    return {"message": "欢迎来到忘忧露视频管理系统后端！访问 /docs 或 /redoc 查看 API 文档。"}

@app.on_event("shutdown")
async def shutdown_event():
    print("忘忧露后端正在关闭。")
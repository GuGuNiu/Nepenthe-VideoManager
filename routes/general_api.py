from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, Response
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from components import database_models as models
from tools.db_utils import get_db
from components import video_scanner
from config.backend_settings import settings
import threading
import sys
import os
import mimetypes
import socket
import asyncio
from fastapi.responses import StreamingResponse, JSONResponse
import send2trash
import traceback

router = APIRouter(
    prefix="/api",
    tags=["General & Videos"],
)

class TagBase(BaseModel): name: str = Field(..., min_length=1, max_length=50)
class TagCreate(TagBase): pass
class TagResponse(TagBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class PersonBase(BaseModel): name: str = Field(..., min_length=1, max_length=100)
class PersonCreate(PersonBase): pass
class PersonResponse(PersonBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class VideoBase(BaseModel):
    id: int; name: str; path: str; folder: str; view_count: int
    duration: Optional[int] = None; width: Optional[int] = None
    height: Optional[int] = None; thumbnail_path: Optional[str] = None
    added_date: Optional[datetime] = None
    rating: Optional[float] = Field(None, ge=0, le=5) 
    model_config = ConfigDict(from_attributes=True)

class VideoResponseWithDetails(VideoBase):
    tags: List[TagResponse] = []
    persons: List[PersonResponse] = []
    thumbnail_url: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class VideoUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    tags: Optional[List[str]] = Field(None)
    persons: Optional[List[str]] = Field(None)
    rating: Optional[float] = Field(None, ge=0, le=5) 


@router.get("/")
async def read_api_root(): return {"message": "欢迎使用忘忧露视频管理 API！ (API 根路径)"}

@router.get("/health")
async def health_check(): return {"status": "OK", "message": "API 健康"}

@router.post("/tags", response_model=TagResponse, status_code=201)
async def create_tag(tag: TagCreate, db: Session = Depends(get_db)):
    db_tag = db.query(models.Tag).filter(models.Tag.name == tag.name).first()
    if db_tag: raise HTTPException(status_code=400, detail="标签已存在")
    new_tag = models.Tag(name=tag.name)
    try: db.add(new_tag); db.commit(); db.refresh(new_tag)
    except Exception as e: db.rollback(); raise HTTPException(status_code=500, detail=f"创建标签失败: {str(e)}")
    return new_tag

@router.get("/tags", response_model=List[TagResponse])
async def get_all_tags(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    tags = db.query(models.Tag).order_by(models.Tag.name).offset(skip).limit(limit).all()
    return tags

@router.post("/persons", response_model=PersonResponse, status_code=201)
async def create_person(person: PersonCreate, db: Session = Depends(get_db)):
    db_person = db.query(models.Person).filter(models.Person.name == person.name).first()
    if db_person: raise HTTPException(status_code=400, detail="人物已存在")
    new_person = models.Person(name=person.name)
    try: db.add(new_person); db.commit(); db.refresh(new_person)
    except Exception as e: db.rollback(); raise HTTPException(status_code=500, detail=f"创建人物失败: {str(e)}")
    return new_person

@router.get("/persons", response_model=List[PersonResponse])
async def get_all_persons(skip: int = 0, limit: int = 200, db: Session = Depends(get_db)):
    persons = db.query(models.Person).order_by(models.Person.name).offset(skip).limit(limit).all()
    return persons

def _format_video_response(video_orm_obj: models.Video) -> VideoResponseWithDetails:
    video_dto = VideoResponseWithDetails.model_validate(video_orm_obj)
    if video_dto.thumbnail_path:
        video_dto.thumbnail_url = f"{settings.thumbnails_base_url}/{video_dto.thumbnail_path}"
    else:
        video_dto.thumbnail_url = None
    return video_dto

@router.post("/videos/{video_id}/tags/{tag_id}", response_model=VideoResponseWithDetails)
async def add_tag_to_video(video_id: int, tag_id: int, db: Session = Depends(get_db)):
    video = db.query(models.Video).options(selectinload(models.Video.tags), selectinload(models.Video.persons)).filter(models.Video.id == video_id).first()
    if not video: raise HTTPException(status_code=404, detail="视频未找到")
    tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()
    if not tag: raise HTTPException(status_code=404, detail="标签未找到")
    if tag not in video.tags:
        video.tags.append(tag)
        try: db.commit(); db.refresh(video)
        except Exception as e: db.rollback(); raise HTTPException(status_code=500, detail="添加标签失败")
    return _format_video_response(video)

@router.delete("/videos/{video_id}/tags/{tag_id}", response_model=VideoResponseWithDetails)
async def remove_tag_from_video(video_id: int, tag_id: int, db: Session = Depends(get_db)):
    video = db.query(models.Video).options(selectinload(models.Video.tags), selectinload(models.Video.persons)).filter(models.Video.id == video_id).first()
    if not video: raise HTTPException(status_code=404, detail="视频未找到")
    tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()
    if not tag: raise HTTPException(status_code=404, detail="标签未找到")
    if tag in video.tags:
        video.tags.remove(tag)
        try: db.commit(); db.refresh(video)
        except Exception as e: db.rollback(); raise HTTPException(status_code=500, detail="移除标签失败")
    return _format_video_response(video)

@router.post("/videos/{video_id}/persons/{person_id}", response_model=VideoResponseWithDetails)
async def add_person_to_video(video_id: int, person_id: int, db: Session = Depends(get_db)):
    video = db.query(models.Video).options(selectinload(models.Video.tags), selectinload(models.Video.persons)).filter(models.Video.id == video_id).first()
    if not video: raise HTTPException(status_code=404, detail="视频未找到")
    person = db.query(models.Person).filter(models.Person.id == person_id).first()
    if not person: raise HTTPException(status_code=404, detail="人物未找到")
    if person not in video.persons:
        video.persons.append(person)
        try: db.commit(); db.refresh(video)
        except Exception as e: db.rollback(); raise HTTPException(status_code=500, detail="添加人物失败")
    return _format_video_response(video)

@router.delete("/videos/{video_id}/persons/{person_id}", response_model=VideoResponseWithDetails)
async def remove_person_from_video(video_id: int, person_id: int, db: Session = Depends(get_db)):
    video = db.query(models.Video).options(selectinload(models.Video.tags), selectinload(models.Video.persons)).filter(models.Video.id == video_id).first()
    if not video: raise HTTPException(status_code=404, detail="视频未找到")
    person = db.query(models.Person).filter(models.Person.id == person_id).first()
    if not person: raise HTTPException(status_code=404, detail="人物未找到")
    if person in video.persons:
        video.persons.remove(person)
        try: db.commit(); db.refresh(video)
        except Exception as e: db.rollback(); raise HTTPException(status_code=500, detail="移除人物失败")
    return _format_video_response(video)

@router.post("/videos/{video_id}/view", response_model=VideoResponseWithDetails)
async def increment_view_count(video_id: int, db: Session = Depends(get_db)):
    video = db.query(models.Video).options(selectinload(models.Video.tags), selectinload(models.Video.persons)).filter(models.Video.id == video_id).first()
    if not video: raise HTTPException(status_code=404, detail=f"视频未找到 (ID: {video_id})")
    video.view_count = (video.view_count or 0) + 1 
    try: db.commit(); db.refresh(video) 
    except Exception as e: db.rollback(); raise HTTPException(status_code=500, detail="更新观看次数失败")
    return _format_video_response(video)

@router.get("/videos", response_model=dict)
async def get_videos_with_search_sort(
    skip: int = 0, limit: int = 25, search_term: Optional[str] = None,
    tags: Optional[str] = None, persons_search: Optional[str] = None,
    min_rating: Optional[float] = None, 
    sort_by: Optional[str] = "id", sort_order: Optional[str] = "desc",
    db: Session = Depends(get_db)
):
    try:
        base_query = db.query(models.Video)
        count_base_query = db.query(func.count(models.Video.id))
        query_filters = []
        if search_term:
            search_filter = []
            search_filter.append(models.Video.name.ilike(f"%{search_term}%"))
            query_filters.append(func.or_(*search_filter))

        if tags:
            tag_names_list = [t.strip() for t in tags.split(',') if t.strip()]
            if tag_names_list:
                for tag_name in tag_names_list: query_filters.append(models.Video.tags.any(models.Tag.name == tag_name))
        
        if persons_search:
            person_names_list = [p.strip() for p in persons_search.split(',') if p.strip()]
            if person_names_list:
                for person_name in person_names_list: query_filters.append(models.Video.persons.any(models.Person.name == person_name))
        
        if min_rating is not None: 
            query_filters.append(models.Video.rating >= min_rating)
        
        if query_filters:
            for f_filter in query_filters:
                base_query = base_query.filter(f_filter)
                count_base_query = count_base_query.filter(f_filter)

        total_count = count_base_query.scalar()
        sort_column_map = { 
            "id": models.Video.id, "name": models.Video.name, 
            "duration": models.Video.duration, "view_count": models.Video.view_count, 
            "added_date": models.Video.added_date, "rating": models.Video.rating,
            "updated_date": models.Video.updated_date
        }
        sort_column = sort_column_map.get(sort_by.lower(), models.Video.id)
        ordered_query = base_query.order_by(sort_column.asc() if sort_order.lower() == "asc" else sort_column.desc())
        videos_orm = ordered_query.options(selectinload(models.Video.tags), selectinload(models.Video.persons)).offset(skip).limit(limit).all()
        videos_data = [_format_video_response(vo).model_dump(mode='json') for vo in videos_orm]
        return {"videos": videos_data, "total_count": total_count}
    except Exception as e:
        traceback.print_exc(); raise HTTPException(status_code=500, detail="获取视频列表失败")
    
@router.get("/videos/{video_id}", response_model=VideoResponseWithDetails)
async def get_video_details(video_id: int, db: Session = Depends(get_db)):
    video_orm_obj = db.query(models.Video).options(selectinload(models.Video.tags), selectinload(models.Video.persons)).filter(models.Video.id == video_id).first()
    if not video_orm_obj: raise HTTPException(status_code=404, detail="视频未找到")
    return _format_video_response(video_orm_obj)

@router.put("/videos/{video_id}", response_model=VideoResponseWithDetails)
async def update_video_details(video_id: int, video_update_data: VideoUpdate, db: Session = Depends(get_db)):
    db_video = db.query(models.Video).options(selectinload(models.Video.tags), selectinload(models.Video.persons)).filter(models.Video.id == video_id).first()
    if not db_video: raise HTTPException(status_code=404, detail="视频未找到")
    if video_update_data.name is not None: db_video.name = video_update_data.name
    if video_update_data.rating is not None: db_video.rating = video_update_data.rating 
    if video_update_data.tags is not None:
        updated_video_tags = []
        if video_update_data.tags: 
            for tag_name_str in video_update_data.tags:
                clean_tag_name = tag_name_str.strip()
                if not clean_tag_name: continue
                tag_obj = db.query(models.Tag).filter(models.Tag.name == clean_tag_name).first()
                if not tag_obj: tag_obj = models.Tag(name=clean_tag_name); db.add(tag_obj)
                updated_video_tags.append(tag_obj)
        db_video.tags = updated_video_tags
    if video_update_data.persons is not None:
        updated_video_persons = []
        if video_update_data.persons:
            for person_name_str in video_update_data.persons:
                clean_person_name = person_name_str.strip()
                if not clean_person_name: continue
                person_obj = db.query(models.Person).filter(models.Person.name == clean_person_name).first()
                if not person_obj: person_obj = models.Person(name=clean_person_name); db.add(person_obj)
                updated_video_persons.append(person_obj)
        db_video.persons = updated_video_persons
    try: db.commit(); db.refresh(db_video)
    except Exception as e: db.rollback(); raise HTTPException(status_code=500, detail=f"更新视频失败: {str(e)}")
    return _format_video_response(db_video)

@router.delete("/videos/{video_id}/to-trash", status_code=200)
async def delete_video_to_trash(video_id: int, db: Session = Depends(get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video: raise HTTPException(status_code=404, detail="视频未找到")
    video_path = video.path; video_name = video.name
    if os.path.exists(video_path):
        try: send2trash.send2trash(video_path)
        except Exception as e: raise HTTPException(status_code=500, detail=f"无法将视频文件发送到回收站: {str(e)}")
    else: print(f"警告: 视频文件 '{video_path}' 在磁盘上未找到，但仍将从数据库中删除记录。")
    try: db.delete(video); db.commit()
    except Exception as e: db.rollback(); raise HTTPException(status_code=500, detail=f"数据库记录删除失败: {str(e)}")
    return {"message": f"视频 '{video_name}' 已发送到回收站并从数据库移除。"}

@router.post("/scan-library")
async def scan_library_api(background_tasks: BackgroundTasks):
    def scan_in_background_with_new_session():
        db_bg = next(get_db())
        try:
            video_scanner.scan_video_folders_and_save(
                db_bg, video_paths_to_scan=settings.video_paths,
                current_thumbnails_storage_path=settings.thumbnails_storage_path,
                process_existing_missing_metadata=True 
            )
        except Exception as e: traceback.print_exc()
        finally: db_bg.close()
    background_tasks.add_task(scan_in_background_with_new_session)
    return {"message": "视频库扫描任务已在后台启动。"}

@router.get("/stream/{video_id}")
async def stream_video(video_id: int, request: Request, db: Session = Depends(get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video or not video.path or not os.path.exists(video.path) or not os.path.isfile(video.path):
        print(f"[API Stream - Simpler] 视频文件未找到或路径无效 for video_id: {video_id}, path: {video.path if video else 'N/A'}")
        raise HTTPException(status_code=404, detail="视频文件未找到或路径无效")

    file_path = video.path
    try:
        file_size = os.stat(file_path).st_size
    except Exception as e:
        print(f"[API Stream - Simpler] 无法获取文件信息 for {file_path}: {e}")
        raise HTTPException(status_code=500, detail="无法获取文件信息")

    range_header = request.headers.get("range")
    
    content_type, _ = mimetypes.guess_type(file_path)
    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext == ".mp4": content_type = "video/mp4"
    elif file_ext == ".webm": content_type = "video/webm"
    # ... (可以根据需要添加更多MIME类型判断) ...
    if content_type is None: content_type = "application/octet-stream"

    headers = {
        "Content-Type": content_type,
        "Accept-Ranges": "bytes",
        "Connection": "keep-alive",
    }

    if range_header:
        try:
            range_value = range_header.strip().lower().replace("bytes=", "")
            parts = range_value.split("-")
            start_byte = int(parts[0]) if parts[0] else 0
            end_byte_requested = file_size - 1 
            if len(parts) > 1 and parts[1]:
                end_byte_requested = int(parts[1])
            
            end_byte = min(end_byte_requested, file_size - 1)

            if start_byte < 0 or start_byte >= file_size or start_byte > end_byte:
                print(f"[API Stream - Simpler] 无效的 Range 请求 for {file_path}: {range_header}, file_size: {file_size}")
                headers["Content-Range"] = f"bytes */{file_size}"
                return Response(content=None, status_code=416, headers=headers)

            length_to_send = end_byte - start_byte + 1
            headers["Content-Length"] = str(length_to_send)
            headers["Content-Range"] = f"bytes {start_byte}-{end_byte}/{file_size}"
            status_code = 206
            
            print(f"[API Stream - Simpler] Range request for {file_path}: bytes {start_byte}-{end_byte}/{file_size}, length_to_send: {length_to_send}")

            def ranged_iterfile_sync(): # 使用同步文件读取
                bytes_yielded = 0
                try:
                    with open(file_path, "rb") as f_stream: # 同步打开
                        f_stream.seek(start_byte)
                        while bytes_yielded < length_to_send:
                            chunk_size = min(65536, length_to_send - bytes_yielded)
                            data = f_stream.read(chunk_size) # 同步读取
                            if not data:
                                print(f"[API Stream - Simpler] Ranged stream: 文件读取完毕但未达到预期长度 for {file_path}")
                                break
                            yield data
                            bytes_yielded += len(data)
                except (socket.error, ConnectionResetError, BrokenPipeError) as e_sock: # 移除了 asyncio.CancelledError
                    print(f"[API Stream - Simpler] Socket/Connection error during ranged streaming for {file_path} (client likely disconnected): {type(e_sock).__name__} - {e_sock}")
                except Exception as e_iter:
                    print(f"[API Stream - Simpler] Unexpected error during ranged streaming for {file_path}: {type(e_iter).__name__} - {e_iter}")
                    traceback.print_exc()
                finally:
                    print(f"[API Stream - Simpler] Ranged stream for {file_path} finished or terminated. Yielded {bytes_yielded} bytes.")
            
            return StreamingResponse(ranged_iterfile_sync(), status_code=status_code, headers=headers, media_type=content_type)

        except ValueError:
            print(f"[API Stream - Simpler] 无效的 Range header for {file_path}: {range_header}")
            raise HTTPException(status_code=400, detail="Invalid Range header")
        except Exception as e_range_proc:
            print(f"[API Stream - Simpler] Error processing Range request for {file_path}: {e_range_proc}")
            traceback.print_exc()
            raise HTTPException(status_code=500, detail="Error processing Range request")
    else:
        print(f"[API Stream - Simpler] Full file request for {file_path}, size: {file_size}")
        headers["Content-Length"] = str(file_size)
        status_code = 200

        def full_iterfile_sync(): # 使用同步文件读取
            try:
                with open(file_path, "rb") as f_stream_full: # 同步打开
                    while True:
                        chunk = f_stream_full.read(65536) # 同步读取
                        if not chunk:
                            break
                        yield chunk
            except (socket.error, ConnectionResetError, BrokenPipeError) as e_sock_full: # 移除了 asyncio.CancelledError
                print(f"[API Stream - Simpler] Socket/Connection error during full streaming for {file_path} (client likely disconnected): {type(e_sock_full).__name__} - {e_sock_full}")
            except Exception as e_iter_full:
                print(f"[API Stream - Simpler] Unexpected error during full streaming for {file_path}: {type(e_iter_full).__name__} - {e_iter_full}")
                traceback.print_exc()
            finally:
                print(f"[API Stream - Simpler] Full stream for {file_path} finished or terminated.")

        return StreamingResponse(full_iterfile_sync(), status_code=status_code, headers=headers, media_type=content_type)
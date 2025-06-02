import os
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, desc
from components import database_models as models
from . import video_metadata_extractor 
from typing import List 

SUPPORTED_VIDEO_EXTENSIONS = [".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".ts"]

def _process_video_metadata_and_thumbnail(db: Session, video: models.Video, current_thumbnails_storage_path: str):
    if not video.id:
        print(f"错误: 视频 {video.name} (路径: {video.path}) 没有 ID，无法处理元数据/缩略图。")
        return False # 返回 False 表示未处理或处理失败

    needs_db_update = False # 标记是否有字段被实际更新

    # --- 处理元数据 ---
    if video.duration is None or video.width is None or video.height is None:
        print(f"提取视频元数据: {video.path}")
        metadata = video_metadata_extractor.get_video_metadata(video.path)
        if metadata: # 即使 metadata 字典中的某些键是 None，也尝试更新
            if metadata.get("duration") is not None and video.duration != metadata["duration"]:
                video.duration = metadata["duration"]
                needs_db_update = True
            if metadata.get("width") is not None and video.width != metadata["width"]:
                video.width = metadata["width"]
                needs_db_update = True
            if metadata.get("height") is not None and video.height != metadata["height"]:
                video.height = metadata["height"]
                needs_db_update = True
            
            if needs_db_update:
                print(f"视频 {video.name} 元数据已准备更新。")
        else:
            print(f"未能获取视频 {video.name} 的元数据。")

    # --- 处理缩略图 ---
    # 只有在数据库中没有缩略图记录时才尝试生成或检查文件系统
    if video.thumbnail_path is None:
        print(f"检查/生成视频缩略图 for: {video.name} (ID: {video.id})")
        
        expected_thumbnail_filename = f"video_{video.id}.jpg"
        expected_thumbnail_fullpath = os.path.join(current_thumbnails_storage_path, expected_thumbnail_filename)

        if os.path.exists(expected_thumbnail_fullpath) and os.path.getsize(expected_thumbnail_fullpath) > 0:
            print(f"视频 {video.name} 的缩略图文件 '{expected_thumbnail_filename}' 已存在，更新数据库记录。")
            video.thumbnail_path = expected_thumbnail_filename
            needs_db_update = True
        else:
            print(f"文件系统未找到缩略图 '{expected_thumbnail_filename}' for {video.name}，尝试生成...")
            generated_filename = video_metadata_extractor.generate_thumbnail(
                video_path=video.path, 
                video_id=video.id,
                thumbnails_storage_path=current_thumbnails_storage_path
            )
            if generated_filename:
                video.thumbnail_path = generated_filename
                needs_db_update = True
                print(f"视频 {video.name} 缩略图已生成并记录。")
            else:
                print(f"未能为视频 {video.name} 生成缩略图。")
    
    if needs_db_update:
        db.add(video) # 将更改（元数据或缩略图路径）添加到 session
    return needs_db_update # 返回是否有任何字段被更新


def scan_video_folders_and_save(db: Session, video_paths_to_scan: list[str], current_thumbnails_storage_path: str, process_existing_missing_metadata: bool = False):
    print("开始视频库扫描和处理...")
    if not video_paths_to_scan:
        print("未提供视频库路径，扫描中止。"); return

    processed_paths_this_scan = set()
    newly_added_videos_this_scan = [] # 存储新添加到数据库的 Video 对象
    print("阶段1: 扫描新视频文件...")
    for folder_path in video_paths_to_scan:
        abs_folder_path = os.path.abspath(folder_path)
        if abs_folder_path in processed_paths_this_scan: continue
        if not os.path.isdir(abs_folder_path):
            print(f"警告: 视频文件夹路径无效: {abs_folder_path}"); processed_paths_this_scan.add(abs_folder_path); continue
        print(f"正在扫描文件夹: {abs_folder_path}"); processed_paths_this_scan.add(abs_folder_path)
        for root, _, files in os.walk(abs_folder_path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in SUPPORTED_VIDEO_EXTENSIONS):
                    file_path = os.path.join(root, file)
                    existing_video = db.query(models.Video).filter(models.Video.path == file_path).first()
                    if not existing_video:
                        video = models.Video(name=file, path=file_path, folder=abs_folder_path)
                        db.add(video) 
                        newly_added_videos_this_scan.append(video) # 添加到列表，稍后统一 commit
    
    if newly_added_videos_this_scan:
        try:
            db.commit() # 提交所有新视频，使它们获得 ID
            print(f"阶段1完成: {len(newly_added_videos_this_scan)} 个新视频已添加到数据库并获得ID。")
            for video_obj in newly_added_videos_this_scan: # 确保对象有ID
                if not video_obj.id: 
                    db.refresh(video_obj) # 从数据库刷新以获取ID
        except Exception as e:
            db.rollback()
            print(f"阶段1错误: 添加新视频到数据库失败: {e}")
            # 如果这里失败，newly_added_videos_this_scan 中的对象可能没有ID，后续处理会出问题
            # 可以选择清空 newly_added_videos_this_scan 或直接返回
            newly_added_videos_this_scan = [] # 清空，避免后续处理无ID对象

    # --- 阶段2: 处理元数据和缩略图 ---
    videos_to_process_queue = []
    # 1. 添加本次新扫描到的、已成功获取ID的视频
    for new_video in newly_added_videos_this_scan:
        if new_video.id: # 再次确认有ID
            videos_to_process_queue.append(new_video)
        else:
            print(f"警告: 新增视频 {new_video.name} 仍未获得有效ID，跳过元数据处理。")

    # 2. (可选) 查找数据库中已存在但缺少元数据或缩略图的视频
    if process_existing_missing_metadata:
        print("查找数据库中缺少元数据/缩略图的现有视频...")
        # 查询条件：duration, width, height, thumbnail_path 中至少有一个为 None
        existing_videos_missing_data = db.query(models.Video).filter(
            or_(
                models.Video.duration.is_(None), # 使用 is_() 比较 None
                models.Video.width.is_(None),
                models.Video.height.is_(None),
                models.Video.thumbnail_path.is_(None)
            )
        ).all()
        
        existing_video_ids_in_queue = {v.id for v in videos_to_process_queue if v.id}
        for ev in existing_videos_missing_data:
            if ev.id not in existing_video_ids_in_queue: # 避免重复处理
                videos_to_process_queue.append(ev)
        print(f"找到 {len(existing_videos_missing_data)} 个可能需要更新元数据/缩略图的现有视频（总计待处理 {len(videos_to_process_queue)}）。")

    if videos_to_process_queue:
        print(f"阶段2: 开始为 {len(videos_to_process_queue)} 个视频提取元数据和生成缩略图...")
        any_video_updated_in_stage2 = False
        for video_obj in videos_to_process_queue:
            if _process_video_metadata_and_thumbnail(db, video_obj, current_thumbnails_storage_path):
                any_video_updated_in_stage2 = True # 只要有一个视频被更新了，就标记
        
        if any_video_updated_in_stage2: # 如果有任何视频的元数据或缩略图路径被更新
            try:
                db.commit() # 统一提交所有在 _process_video_metadata_and_thumbnail 中 add() 的更改
                print(f"阶段2完成: 部分或全部视频的元数据/缩略图信息已更新并保存。")
            except Exception as e:
                db.rollback()
                print(f"阶段2错误: 保存元数据/缩略图更新失败: {e}")
        else:
            print("阶段2完成: 没有视频的元数据/缩略图被更新。")
    else:
        print("阶段2: 没有需要处理元数据或生成缩略图的视频。")

    total_videos_in_db = db.query(models.Video).count()
    print(f"视频库扫描和处理全部完成。数据库中总视频数: {total_videos_in_db}")

def scan_video_folders_and_save(
    db: Session, 
    video_paths_to_scan: List[str], # 使用 typing.List
    current_thumbnails_storage_path: str, 
    process_existing_missing_metadata: bool = False
):
    print(f"[Scanner] 开始视频库扫描。待扫描路径: {video_paths_to_scan}, 缩略图存储: {current_thumbnails_storage_path}")
    if not video_paths_to_scan:
        print("[Scanner] 未提供视频库路径，扫描中止。")
        return {"message": "未提供视频库路径", "total_videos_in_db": db.query(func.count(models.Video.id)).scalar() or 0}

    processed_paths_this_scan = set()
    newly_added_videos_this_scan = []
    
    for folder_path in video_paths_to_scan:
        # ... (扫描文件夹，添加新视频到 newly_added_videos_this_scan 的逻辑，与你之前能工作的版本一致) ...
        # ... (确保在添加新视频后，执行 db.commit() 使它们获得 ID) ...
        abs_folder_path = os.path.abspath(folder_path)
        if abs_folder_path in processed_paths_this_scan: continue
        if not os.path.isdir(abs_folder_path):
            print(f"[Scanner] 警告: 视频文件夹路径无效: {abs_folder_path}"); processed_paths_this_scan.add(abs_folder_path); continue
        print(f"[Scanner] 正在扫描文件夹: {abs_folder_path}"); processed_paths_this_scan.add(abs_folder_path)
        for root, _, files in os.walk(abs_folder_path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in SUPPORTED_VIDEO_EXTENSIONS):
                    file_path = os.path.join(root, file)
                    existing_video = db.query(models.Video).filter(models.Video.path == file_path).first()
                    if not existing_video:
                        video = models.Video(name=os.path.basename(file_path), path=file_path, folder=abs_folder_path) # 使用 os.path.basename
                        db.add(video) 
                        newly_added_videos_this_scan.append(video)
    
    if newly_added_videos_this_scan:
        try:
            db.commit()
            print(f"[Scanner] {len(newly_added_videos_this_scan)} 个新视频已初步添加到数据库。")
            for video_obj in newly_added_videos_this_scan:
                if not video_obj.id: db.refresh(video_obj)
        except Exception as e:
            db.rollback()
            print(f"[Scanner] 添加新视频到数据库失败: {e}")
            newly_added_videos_this_scan = [] 

    videos_to_process_queue = [v for v in newly_added_videos_this_scan if v.id] # 只处理有ID的新视频
    if process_existing_missing_metadata:
        # ... (添加已存在但缺少元数据的视频到队列的逻辑) ...
        existing_videos_missing_data = db.query(models.Video).filter(
            or_(models.Video.duration.is_(None), models.Video.width.is_(None), models.Video.height.is_(None), models.Video.thumbnail_path.is_(None))
        ).all()
        existing_video_ids_in_queue = {v.id for v in videos_to_process_queue}
        for ev in existing_videos_missing_data:
            if ev.id not in existing_video_ids_in_queue: videos_to_process_queue.append(ev)
    
    if videos_to_process_queue:
        print(f"[Scanner] 开始为 {len(videos_to_process_queue)} 个视频提取元数据和生成缩略图...")
        any_video_updated_in_stage2 = False
        for video_obj in videos_to_process_queue:
            if _process_video_metadata_and_thumbnail(db, video_obj, current_thumbnails_storage_path):
                any_video_updated_in_stage2 = True
        if any_video_updated_in_stage2:
            try:
                db.commit()
                print(f"[Scanner] 部分或全部视频的元数据/缩略图信息已更新并保存。")
            except Exception as e:
                db.rollback()
                print(f"[Scanner] 保存元数据/缩略图更新失败: {e}")
    
    total_videos_in_db = db.query(func.count(models.Video.id)).scalar() or 0
    print(f"[Scanner] 视频库扫描和处理全部完成。数据库中总视频数: {total_videos_in_db}")
    return {"message": "视频库扫描完成", "total_videos_in_db": total_videos_in_db}
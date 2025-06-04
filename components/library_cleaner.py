import os
from sqlalchemy.orm import Session
from sqlalchemy import not_
from typing import List
from components import database_models as models 

def clean_orphaned_videos(
    db: Session, 
    current_configured_paths: List[str], 
    thumbnails_storage_path: str
) -> dict:
    """
    Cleans video records from the database and their associated thumbnails 
    if their parent folder is no longer in the current_configured_paths.
    All log messages will be in English.
    """
    cleaned_count = 0
    errors = []

    print(f"[Cleaner] Starting cleanup of orphaned videos. Configured library paths: {current_configured_paths}")

    abs_current_configured_paths = [os.path.abspath(p) for p in current_configured_paths if p and isinstance(p, str)]

    if not abs_current_configured_paths:
        print("[Cleaner] No library paths are currently configured. All video records and thumbnails will be removed.")
        all_videos_in_db = db.query(models.Video).all()
        if not all_videos_in_db:
            print("[Cleaner] Database is already empty. No videos to clean.")
            return {"message": "No library paths configured and database is empty.", "cleaned_count": 0, "errors": 0}
        
        print(f"[Cleaner] Found {len(all_videos_in_db)} video records to remove as no paths are configured.")
        for video_to_delete in all_videos_in_db:
            if video_to_delete.thumbnail_path:
                thumb_full_path = os.path.join(thumbnails_storage_path, video_to_delete.thumbnail_path)
                if os.path.exists(thumb_full_path):
                    try:
                        os.remove(thumb_full_path)
                        print(f"[Cleaner] Deleted orphaned thumbnail: {thumb_full_path}")
                    except OSError as e:
                        error_msg = f"Failed to delete thumbnail {thumb_full_path}: {e}"
                        print(f"[Cleaner] Error: {error_msg}")
                        errors.append(error_msg)
            db.delete(video_to_delete)
            cleaned_count += 1
    else:
        all_videos_in_db = db.query(models.Video).all()
        videos_to_delete_list = []

        if not all_videos_in_db:
            print("[Cleaner] Database is empty. No videos to check for orphaning.")
            return {"message": "Database is empty.", "cleaned_count": 0, "errors": 0}

        print(f"[Cleaner] Checking {len(all_videos_in_db)} video records against {len(abs_current_configured_paths)} configured paths.")
        for video in all_videos_in_db:
            video_path_abs = os.path.abspath(video.path)
            is_orphaned = True
            for configured_path_abs in abs_current_configured_paths:  
                if video_path_abs.startswith(configured_path_abs):
                    if len(video_path_abs) == len(configured_path_abs) or \
                       (len(video_path_abs) > len(configured_path_abs) and video_path_abs[len(configured_path_abs)] == os.sep):
                        is_orphaned = False
                        break
            
            if is_orphaned:
                videos_to_delete_list.append(video)
                print(f"[Cleaner] Identified orphaned video: {video.name} (Path: {video.path})")

        if not videos_to_delete_list:
            print("[Cleaner] No orphaned video records found to clean.")
            return {"message": "No orphaned videos found.", "cleaned_count": 0, "errors": 0}

        print(f"[Cleaner] Found {len(videos_to_delete_list)} orphaned video records to remove.")
        for video_to_delete in videos_to_delete_list:
            if video_to_delete.thumbnail_path:
                thumb_full_path = os.path.join(thumbnails_storage_path, video_to_delete.thumbnail_path)
                if os.path.exists(thumb_full_path):
                    try:
                        os.remove(thumb_full_path)
                        print(f"[Cleaner] Deleted orphaned thumbnail: {thumb_full_path}")
                    except OSError as e:
                        error_msg = f"Failed to delete thumbnail {thumb_full_path}: {e}"
                        print(f"[Cleaner] Error: {error_msg}")
                        errors.append(error_msg)
            db.delete(video_to_delete)
            cleaned_count += 1
            
    if cleaned_count > 0 or errors: 
        try:
            db.commit()
            print(f"[Cleaner] Successfully committed removal of {cleaned_count} orphaned video records.")
        except Exception as e:
            db.rollback()
            error_msg = f"Database error during commit of cleanup: {e}"
            print(f"[Cleaner] Error: {error_msg}")
            errors.append(error_msg)
            cleaned_count = 0 
    
    result_message = f"Cleanup finished. Removed {cleaned_count} orphaned video(s)."
    if errors:
        result_message += f" Encountered {len(errors)} error(s)."
        print(f"[Cleaner] Errors during cleanup: {errors}")

    return {"message": result_message, "cleaned_count": cleaned_count, "errors": len(errors)}

def cleanup_unreferenced_thumbnail_files(db: Session, thumbnails_storage_path: str):
    print("[Cleaner] Starting cleanup of unreferenced physical thumbnail files...")
    if not os.path.isdir(thumbnails_storage_path):
        print(f"[Cleaner] Thumbnails storage path does not exist: {thumbnails_storage_path}")
        return 0
    
    referenced_thumbnail_filenames = set()
    for video_thumb_path in db.query(models.Video.thumbnail_path).filter(models.Video.thumbnail_path.isnot(None)).all():
        if video_thumb_path[0]: # video_thumb_path is a tuple
            referenced_thumbnail_filenames.add(os.path.basename(video_thumb_path[0]))

    deleted_count = 0
    for filename in os.listdir(thumbnails_storage_path):
        if filename.lower().endswith(".jpg"): # 或者你使用的缩略图扩展名
            if filename not in referenced_thumbnail_filenames:
                file_to_delete = os.path.join(thumbnails_storage_path, filename)
                try:
                    os.remove(file_to_delete)
                    print(f"[Cleaner] Deleted unreferenced thumbnail file: {file_to_delete}")
                    deleted_count += 1
                except OSError as e:
                    print(f"[Cleaner] Error deleting unreferenced thumbnail file {file_to_delete}: {e}")
    print(f"[Cleaner] Finished cleanup of unreferenced physical thumbnail files. Deleted: {deleted_count}")
    return deleted_count
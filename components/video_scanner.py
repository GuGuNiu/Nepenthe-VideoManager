import os
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, desc 
from components import database_models as models
from . import video_metadata_extractor 
from typing import List 

SUPPORTED_VIDEO_EXTENSIONS = [".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".ts"] 

def _process_video_metadata_and_thumbnail(db: Session, video: models.Video, current_thumbnails_storage_path: str):
    if not video.id:
        print(f"[Scanner ProcessMeta] Error: Video {video.name} (Path: {video.path}) has no ID. Cannot process metadata/thumbnail.")
        return False 

    needs_db_update = False 

    if video.duration is None or video.width is None or video.height is None:
        print(f"[Scanner ProcessMeta] Extracting metadata for video: {video.path}")
        metadata = video_metadata_extractor.get_video_metadata(video.path)
        if metadata:
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
                print(f"[Scanner ProcessMeta] Video {video.name} metadata prepared for update.")
        else:
            print(f"[Scanner ProcessMeta] Failed to get metadata for video {video.name}.")

    if video.thumbnail_path is None:
        print(f"[Scanner ProcessMeta] Checking/generating thumbnail for video: {video.name} (ID: {video.id})")
        expected_thumbnail_filename = f"video_{video.id}.jpg"
        expected_thumbnail_fullpath = os.path.join(current_thumbnails_storage_path, expected_thumbnail_filename)

        if os.path.exists(expected_thumbnail_fullpath) and os.path.getsize(expected_thumbnail_fullpath) > 0:
            print(f"[Scanner ProcessMeta] Thumbnail file '{expected_thumbnail_filename}' for video {video.name} already exists. Updating database record.")
            video.thumbnail_path = expected_thumbnail_filename
            needs_db_update = True
        else:
            print(f"[Scanner ProcessMeta] Thumbnail file '{expected_thumbnail_filename}' not found for {video.name}. Attempting to generate...")
            generated_filename = video_metadata_extractor.generate_thumbnail(
                video_path=video.path, 
                video_id=video.id,
                thumbnails_storage_path=current_thumbnails_storage_path
            )
            if generated_filename:
                video.thumbnail_path = generated_filename
                needs_db_update = True
                print(f"[Scanner ProcessMeta] Thumbnail for video {video.name} generated and recorded.")
            else:
                print(f"[Scanner ProcessMeta] Failed to generate thumbnail for video {video.name}.")
    
    if needs_db_update:
        db.add(video) 
    return needs_db_update


def scan_video_folders_and_save(
    db: Session, 
    video_paths_to_scan: List[str],
    current_thumbnails_storage_path: str, 
    process_existing_missing_metadata: bool = False # This flag is still useful
):
    print(f"[Scanner] Starting video library scan. Paths to scan: {video_paths_to_scan}, Thumbnails storage: {current_thumbnails_storage_path}")
    if not video_paths_to_scan:
        print("[Scanner] No video library paths provided for scanning, scan aborted.")
        return {"message": "No video library paths provided for scanning.", "total_videos_in_db": db.query(func.count(models.Video.id)).scalar() or 0}

    # Cleanup logic is now handled externally before this function is called.
    # This function now focuses only on adding/updating videos from the given paths.

    processed_paths_this_scan = set()
    newly_added_videos_this_scan = []
    
    print("[Scanner] Phase 1: Scanning for new video files...")
    for folder_path in video_paths_to_scan:
        abs_folder_path = os.path.abspath(folder_path)
        if abs_folder_path in processed_paths_this_scan: 
            print(f"[Scanner] Path {abs_folder_path} already processed in this scan, skipping.")
            continue
        if not os.path.isdir(abs_folder_path):
            print(f"[Scanner] Warning: Video folder path is invalid: {abs_folder_path}")
            processed_paths_this_scan.add(abs_folder_path)
            continue
        
        print(f"[Scanner] Scanning folder: {abs_folder_path}")
        processed_paths_this_scan.add(abs_folder_path)
        for root, _, files in os.walk(abs_folder_path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in SUPPORTED_VIDEO_EXTENSIONS):
                    file_path = os.path.join(root, file)
                    existing_video = db.query(models.Video).filter(models.Video.path == file_path).first()
                    if not existing_video:
                        video_name = os.path.basename(file_path)
                        print(f"[Scanner] New video found: {video_name} at {file_path}")
                        video = models.Video(name=video_name, path=file_path, folder=abs_folder_path)
                        db.add(video) 
                        newly_added_videos_this_scan.append(video)
    
    if newly_added_videos_this_scan:
        try:
            db.commit()
            print(f"[Scanner] Phase 1 complete: {len(newly_added_videos_this_scan)} new video(s) initially added to database and received IDs.")
            for video_obj in newly_added_videos_this_scan:
                if not video_obj.id: 
                    db.refresh(video_obj) 
        except Exception as e:
            db.rollback()
            print(f"[Scanner] Phase 1 Error: Failed to add new videos to database: {e}")
            newly_added_videos_this_scan = [] 
    else:
        print("[Scanner] Phase 1 complete: No new video files found to add.")


    videos_to_process_queue = []
    for new_video in newly_added_videos_this_scan:
        if new_video.id:
            videos_to_process_queue.append(new_video)
        else:
            print(f"[Scanner] Warning: Newly added video {new_video.name} still has no valid ID after commit/refresh, skipping metadata processing.")

    if process_existing_missing_metadata:
        print("[Scanner] Checking database for existing videos missing metadata/thumbnails...")
        existing_videos_missing_data = db.query(models.Video).filter(
            or_(
                models.Video.duration.is_(None),
                models.Video.width.is_(None),
                models.Video.height.is_(None),
                models.Video.thumbnail_path.is_(None)
            )
        ).all()
        
        existing_video_ids_in_queue = {v.id for v in videos_to_process_queue if v.id}
        added_from_existing = 0
        for ev in existing_videos_missing_data:
            if ev.id not in existing_video_ids_in_queue:
                videos_to_process_queue.append(ev)
                added_from_existing +=1
        print(f"[Scanner] Found {len(existing_videos_missing_data)} existing videos potentially needing updates. Added {added_from_existing} of them to process queue (Total to process: {len(videos_to_process_queue)}).")

    if videos_to_process_queue:
        print(f"[Scanner] Phase 2: Starting metadata extraction and thumbnail generation for {len(videos_to_process_queue)} video(s)...")
        any_video_updated_in_stage2 = False
        for video_obj in videos_to_process_queue:
            if _process_video_metadata_and_thumbnail(db, video_obj, current_thumbnails_storage_path):
                any_video_updated_in_stage2 = True
        
        if any_video_updated_in_stage2:
            try:
                db.commit()
                print(f"[Scanner] Phase 2 complete: Metadata/thumbnail information for some/all processed videos updated and saved.")
            except Exception as e:
                db.rollback()
                print(f"[Scanner] Phase 2 Error: Failed to save metadata/thumbnail updates: {e}")
        else:
            print("[Scanner] Phase 2 complete: No metadata/thumbnails were updated for the processed videos.")
    else:
        print("[Scanner] Phase 2: No videos in queue for metadata or thumbnail processing.")

    total_videos_in_db = db.query(func.count(models.Video.id)).scalar() or 0
    print(f"[Scanner] Video library scan and processing finished. Total videos in database: {total_videos_in_db}")
    return {"message": "Video library scan finished.", "total_videos_in_db": total_videos_in_db}
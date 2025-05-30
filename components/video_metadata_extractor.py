import subprocess
import json
import os
from typing import Optional

# --- !!! 重要：将下面的路径替换为你系统中 ffmpeg.exe 和 ffprobe.exe 的实际完整路径 !!! ---
FFPROBE_PATH = r"E:\SF\ffmpeg\bin\ffprobe.exe"  # 请替换为你的实际路径
FFMPEG_PATH = r"E:\SF\ffmpeg\bin\ffmpeg.exe"    # 请替换为你的实际路径
# --- ------------------------------------------------------------------------------------ ---

def get_video_metadata(video_path: str) -> Optional[dict]:
    command = [
        FFPROBE_PATH, "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", video_path
    ]
    print(f"[METADATA_EXTRACTOR] 执行 ffprobe: {' '.join(command)}")
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(timeout=60)
        if process.returncode != 0:
            error_message = stderr.decode('utf-8', errors='replace').strip()
            print(f"ffprobe 执行失败 for '{video_path}'. 返回码: {process.returncode}. 错误: {error_message}")
            return None
        try:
            metadata_json = json.loads(stdout)
        except json.JSONDecodeError as e:
            print(f"ffprobe 输出 JSON 解析失败 for '{video_path}': {e}")
            print(f"ffprobe stdout: {stdout.decode('utf-8', errors='replace')[:500]}...")
            return None
        duration, width, height = None, None, None
        if 'format' in metadata_json and 'duration' in metadata_json['format']:
            try:
                duration_str = metadata_json['format']['duration']
                if duration_str is not None: duration = int(float(duration_str))
            except (ValueError, TypeError) as e:
                print(f"解析时长失败 for '{video_path}': {e}. Duration: {metadata_json['format'].get('duration')}")
        if 'streams' in metadata_json:
            for stream in metadata_json['streams']:
                if stream.get('codec_type') == 'video':
                    try:
                        w_str, h_str = stream.get('width'), stream.get('height')
                        if w_str is not None: width = int(w_str)
                        if h_str is not None: height = int(h_str)
                        break
                    except (ValueError, TypeError) as e:
                        print(f"解析宽高失败 for '{video_path}' (stream {stream.get('index')}): {e}. W: {stream.get('width')}, H: {stream.get('height')}")
        if duration is None and width is None and height is None and process.returncode == 0 and not metadata_json.get('streams'):
             print(f"未能从 '{video_path}' 提取任何有效的元数据（可能是非媒体文件），但 ffprobe 执行未报错。")
        elif duration is None and width is None and height is None:
             print(f"未能从 '{video_path}' 提取任何有效的元数据。")
        return {"duration": duration, "width": width, "height": height}
    except subprocess.TimeoutExpired: print(f"ffprobe 执行超时 for '{video_path}'"); return None
    except FileNotFoundError: print(f"错误: ffprobe 命令 ('{FFPROBE_PATH}') 未找到。请检查硬编码路径。"); return None
    except Exception as e: print(f"获取视频元数据时发生未知错误 for '{video_path}': {e}"); return None

def generate_thumbnail(video_path: str, video_id: int, thumbnails_storage_path: str, timestamp: str = "00:00:03") -> Optional[str]:
    if not thumbnails_storage_path or not os.path.isdir(thumbnails_storage_path):
        print(f"错误: 无效或不存在的缩略图存储路径: '{thumbnails_storage_path}'")
        return None
    if not os.path.exists(video_path):
        print(f"错误: 输入视频文件不存在: '{video_path}'")
        return None
    thumbnail_filename = f"video_{video_id}.jpg" 
    output_full_path = os.path.join(thumbnails_storage_path, thumbnail_filename)
    command = [
        FFMPEG_PATH, "-ss", timestamp, "-i", video_path, "-vframes", "1",
        "-vf", "scale=320:-2,format=yuvj420p", "-q:v", "3", "-y", output_full_path
    ]
    print(f"[METADATA_EXTRACTOR] 执行 ffmpeg: {' '.join(command)}")
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, stderr_output = process.communicate(timeout=60) 
        if process.returncode != 0:
            error_message = stderr_output.decode('utf-8', errors='replace').strip()
            print(f"ffmpeg 生成缩略图失败 for '{video_path}'. 返回码: {process.returncode}. 错误: {error_message}")
            return None
        if os.path.exists(output_full_path) and os.path.getsize(output_full_path) > 0:
            print(f"成功生成缩略图: {output_full_path}")
            return thumbnail_filename 
        else:
            error_message = stderr_output.decode('utf-8', errors='replace').strip()
            print(f"ffmpeg 执行可能成功但未找到有效输出文件 for '{video_path}'. Stderr: {error_message}")
            if os.path.exists(output_full_path) and os.path.getsize(output_full_path) == 0:
                print(f"警告: 生成的缩略图文件 '{output_full_path}' 为空，已删除。")
                try: os.remove(output_full_path)
                except OSError as e_rm: print(f"删除空缩略图文件失败: {e_rm}")
            return None
    except subprocess.TimeoutExpired: print(f"ffmpeg 生成缩略图超时 for '{video_path}'"); return None
    except FileNotFoundError: print(f"错误: ffmpeg 命令 ('{FFMPEG_PATH}') 未找到。请检查硬编码路径。"); return None
    except Exception as e: print(f"生成缩略图时发生未知错误 for '{video_path}': {e}"); return None
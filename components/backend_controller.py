import subprocess
import threading
import os
import sys
import traceback
from typing import Optional 

backend_process = None
on_log_message_callback = None
on_status_update_callback = None
current_status_key = "已停止" 

def set_callbacks(log_callback, status_callback):
    global on_log_message_callback, on_status_update_callback
    on_log_message_callback = log_callback
    on_status_update_callback = status_callback

def _log_direct(message):
    if on_log_message_callback:
        on_log_message_callback(message)

def _update_status(status_text): 
    global current_status_key
    current_status_key = status_text
    if on_status_update_callback:
        on_status_update_callback(status_text)

def _read_stream(stream, is_stderr=False):
    prefix = "[后端错误]" if is_stderr else "[后端输出]"
    for line_bytes in iter(stream.readline, b''): 
        try:
            line_str = line_bytes.decode('utf-8').strip()
        except UnicodeDecodeError:
            try:
                line_str = line_bytes.decode(sys.getdefaultencoding(), errors='replace').strip()
            except Exception: 
                 line_str = line_bytes.decode('latin-1', errors='replace').strip() 
        _log_direct(f"{prefix} {line_str}")
    stream.close()

def _monitor_process():
    global backend_process
    if backend_process:
        backend_process.wait() 
        exit_code = backend_process.returncode
        log_msg = f"后端进程已退出，代码: {exit_code}" if exit_code == 0 else f"后端进程因错误退出，代码: {exit_code}"
        _log_direct(log_msg)
        backend_process = None 
        _update_status("已停止") 

def start(script_path, host, port, video_paths_str, 
          db_file_full_path: Optional[str] = None, # 改为 Optional，默认 None
          thumbnails_storage_full_path: Optional[str] = None, # 改为 Optional，默认 None
          ffmpeg_exec_path: Optional[str] = None,
          ffprobe_exec_path: Optional[str] = None
          ):
    global backend_process
    if backend_process and backend_process.poll() is None: 
        _log_direct("后端已在运行或启动中。")
        return False
    
    if not os.path.exists(script_path) or not os.path.isfile(script_path):
        _log_direct(f"后端脚本未找到: {script_path}")
        _update_status("错误")
        return False

    _update_status("启动中...")
    _log_direct("尝试启动后端...")

    try:
        python_executable = sys.executable 
        cmd = [
            python_executable, "-u", script_path, 
            "--host", host,
            "--port", str(port), # 确保端口是字符串
            "--video_paths", video_paths_str
        ]
        # 只有当路径被提供时才添加到命令行参数
        if db_file_full_path:
            cmd.extend(["--db-file-path", db_file_full_path])
        if thumbnails_storage_full_path:
            cmd.extend(["--thumbnails-storage-path", thumbnails_storage_full_path])
        if ffmpeg_exec_path:
            cmd.extend(["--ffmpeg-path", ffmpeg_exec_path])
        if ffprobe_exec_path:
            cmd.extend(["--ffprobe-path", ffprobe_exec_path])
        
        _log_direct(f"执行命令: {' '.join(cmd)}")
        _log_direct(f"使用的Python解释器: {python_executable}")

        startupinfo = None
        creation_flags = 0 
        if os.name == 'nt': 
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE 
            creation_flags = subprocess.CREATE_NO_WINDOW 
        
        process_env = os.environ.copy()
        backend_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startupinfo,
            creationflags=creation_flags,
            env=process_env 
        )
        _log_direct(f"后端进程已启动 (PID: {backend_process.pid})。")
        _update_status("运行中")
        
        threading.Thread(target=_read_stream, args=(backend_process.stdout,), daemon=True).start()
        threading.Thread(target=_read_stream, args=(backend_process.stderr, True), daemon=True).start()
        threading.Thread(target=_monitor_process, daemon=True).start()
        return True
    except Exception as e:
        _log_direct(f"启动后端失败: {str(e)}")
        _log_direct(traceback.format_exc()) # 打印完整的错误栈
        backend_process = None 
        _update_status("错误")
        return False

def stop():
    global backend_process
    if backend_process and backend_process.poll() is None: 
        _update_status("停止中...")
        _log_direct("尝试停止后端...")
        try:
            backend_process.terminate() 
        except Exception as e:
            _log_direct(f"停止后端失败: {str(e)}")
            _update_status("错误") 
            return False
        return True 
    else:
        _log_direct("没有后端进程可以停止。")
        if backend_process is None: 
            _update_status("已停止")
        return False

def is_running():
    return backend_process is not None and backend_process.poll() is None
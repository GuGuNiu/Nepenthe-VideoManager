import json
import os

CONFIG_FILE_NAME = "nepenthe_launcher_settings.json"
DEFAULT_CONFIG = {
    "api_host": "127.0.0.1",
    "api_port": "8000",
    "video_paths": [],
    "backend_script_path": "run_backend_server.py",
    
}



current_config = DEFAULT_CONFIG.copy()

def get_config_path():
    home_dir = os.path.expanduser("~")
    config_dir = os.path.join(home_dir, ".nepenthe_video_manager")
    if not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, CONFIG_FILE_NAME)

def load_config():
    global current_config
    cfg_path = get_config_path()
    
    current_config["theme"] = "light" 

    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                for key in DEFAULT_CONFIG:
                    if key in loaded and key != "theme": 
                        current_config[key] = loaded[key]
        except Exception:
            
            temp_theme = current_config["theme"]
            current_config = DEFAULT_CONFIG.copy()
            current_config["theme"] = temp_theme
            save_config() 
    else:
        save_config() 
    return current_config

def save_config():
    global current_config
    current_config["theme"] = "light" 
    cfg_path = get_config_path()
    try:
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(current_config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"保存启动器配置失败: {e}")

def update_setting(key, value):
    global current_config
    if key == "theme": 
        print("警告: 主题已固定为明亮模式，无法更改。")
        current_config["theme"] = "light" 
        return
    if key in current_config:
        current_config[key] = value
    else:
        print(f"警告: 尝试更新未知配置项 '{key}'")
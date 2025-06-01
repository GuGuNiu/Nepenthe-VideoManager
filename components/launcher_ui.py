# components/launcher_ui.py
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from config import launcher_settings as config
from components import backend_controller as backend_manager
import os
import webbrowser
import urllib.request
import urllib.error
import json
import threading

class UIManager:
    def __init__(self, app_root):
        self.app = app_root
        self.elements = {}
        self.status_var = tk.StringVar()
        self.video_paths_listbox = None
        ctk.set_appearance_mode("light")

    def setup_main_layout(self):
        self.app.title("忘忧露启动器 - Nepenthe Video Manager")
        self.app.geometry("1000x680")

        main_container = ctk.CTkFrame(master=self.app, fg_color="transparent")
        main_container.pack(padx=10, pady=10, fill="both", expand=True)

        main_container.grid_columnconfigure(0, weight=4) 
        main_container.grid_columnconfigure(1, weight=6) 
        main_container.grid_rowconfigure(0, weight=1)    

        left_column = ctk.CTkFrame(master=main_container)
        left_column.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="nsew")

        control_section_frame = ctk.CTkFrame(master=left_column, fg_color="transparent")
        control_section_frame.pack(pady=(10,5), padx=15, fill="x", expand=False)
        ctk.CTkLabel(master=control_section_frame, text="控制中心", font=("Arial", 18, "bold")).pack(pady=(0,10))
        self._create_control_widgets(control_section_frame)

       
        scan_button_frame = ctk.CTkFrame(master=left_column, fg_color="transparent")
        scan_button_frame.pack(pady=(5,10), padx=15, fill="x", expand=False)
        self.elements["scan_library_button"] = ctk.CTkButton(
            master=scan_button_frame, 
            text="扫描/更新视频库", 
            command=self._trigger_scan_library_action, 
            height=35
        )
        self.elements["scan_library_button"].pack(fill="x", pady=5)
       

        separator = ctk.CTkFrame(master=left_column, height=2, fg_color="gray70")
        separator.pack(pady=10, padx=15, fill="x")

        settings_section_frame = ctk.CTkFrame(master=left_column, fg_color="transparent")
        settings_section_frame.pack(pady=(5,10), padx=15, fill="x", expand=False) 
        ctk.CTkLabel(master=settings_section_frame, text="参数设置", font=("Arial", 18, "bold")).pack(pady=(0,10))
        settings_content_area = ctk.CTkFrame(master=settings_section_frame, fg_color="transparent")
        settings_content_area.pack(fill="x", expand=True) 
        self._create_settings_widgets(settings_content_area) 

        right_column_logs = ctk.CTkFrame(master=main_container)
        right_column_logs.grid(row=0, column=1, padx=(0,0), pady=0, sticky="nsew")
        ctk.CTkLabel(master=right_column_logs, text="运行日志", font=("Arial", 18, "bold")).pack(pady=(10,5), padx=10)
        self._create_logs_widgets(right_column_logs)
        
        self.update_status_display(backend_manager.current_status_key)
        self._update_scan_button_state()

    def _create_control_widgets(self, parent_frame):
       
        ctk.CTkLabel(master=parent_frame, text="状态:", font=("Arial", 14)).pack(pady=(5,0), padx=20)
        ctk.CTkLabel(master=parent_frame, textvariable=self.status_var, font=("Arial", 16, "bold")).pack(pady=(0,15), padx=20)
        self.elements["start_button"] = ctk.CTkButton(master=parent_frame, text="启动后端服务", command=self._start_backend_action, height=35)
        self.elements["start_button"].pack(pady=5, padx=20, fill="x")
        self.elements["stop_button"] = ctk.CTkButton(master=parent_frame, text="停止后端服务", command=self._stop_backend_action_ui, height=35)
        self.elements["stop_button"].pack(pady=5, padx=20, fill="x")
        self.elements["open_ui_button"] = ctk.CTkButton(master=parent_frame, text="打开 Web 管理界面", command=self._open_web_ui_action, height=35)
        self.elements["open_ui_button"].pack(pady=(5,10), padx=20, fill="x")


    def _create_settings_widgets(self, parent_settings_area):
       
        settings_content_frame = ctk.CTkFrame(master=parent_settings_area, fg_color="transparent")
        settings_content_frame.pack(fill="x", padx=5, pady=5)
        row_idx = 0
        ctk.CTkLabel(master=settings_content_frame, text="API 主机:").grid(row=row_idx, column=0, padx=(0,10), pady=5, sticky="w")
        self.elements["host_entry"] = ctk.CTkEntry(master=settings_content_frame)
        self.elements["host_entry"].grid(row=row_idx, column=1, padx=0, pady=5, sticky="ew"); row_idx += 1
        ctk.CTkLabel(master=settings_content_frame, text="API 端口:").grid(row=row_idx, column=0, padx=(0,10), pady=5, sticky="w")
        self.elements["port_entry"] = ctk.CTkEntry(master=settings_content_frame)
        self.elements["port_entry"].grid(row=row_idx, column=1, padx=0, pady=5, sticky="ew"); row_idx += 1
        ctk.CTkLabel(master=settings_content_frame, text="后端脚本:").grid(row=row_idx, column=0, padx=(0,10), pady=5, sticky="w")
        script_frame = ctk.CTkFrame(master=settings_content_frame, fg_color="transparent")
        script_frame.grid(row=row_idx, column=1, padx=0, pady=5, sticky="ew")
        self.elements["backend_script_entry"] = ctk.CTkEntry(master=script_frame)
        self.elements["backend_script_entry"].pack(side="left", fill="x", expand=True, padx=(0,5))
        ctk.CTkButton(master=script_frame, text="浏览", command=self._browse_backend_script, width=60).pack(side="left"); row_idx += 1
        ctk.CTkLabel(master=settings_content_frame, text="视频库路径:").grid(row=row_idx, column=0, padx=(0,10), pady=(5,0), sticky="nw")
        listbox_frame = ctk.CTkFrame(master=settings_content_frame)
        listbox_frame.grid(row=row_idx, column=1, padx=0, pady=5, sticky="ew")
        self.video_paths_listbox = tk.Listbox(master=listbox_frame, height=5, exportselection=False, relief="solid", borderwidth=1)
        self.video_paths_listbox.configure(bg="#FEFEFE", fg="#333333", selectbackground="#D0E0FF", selectforeground="#000000", font=("微软雅黑", 9))
        self.video_paths_listbox.pack(pady=(0,5), fill="x", expand=True)
        video_path_buttons_frame = ctk.CTkFrame(master=listbox_frame, fg_color="transparent")
        video_path_buttons_frame.pack(fill="x", pady=(0,5))
        ctk.CTkButton(master=video_path_buttons_frame, text="添加路径", command=self._add_video_path_dialog, width=80).pack(side="left", padx=(0,5))
        ctk.CTkButton(master=video_path_buttons_frame, text="移除选中", command=self._remove_selected_video_path, width=80).pack(side="left"); row_idx += 1
        save_button_frame = ctk.CTkFrame(master=settings_content_frame, fg_color="transparent")
        save_button_frame.grid(row=row_idx, column=0, columnspan=2, pady=(15,10), sticky="ew")
        self.elements["save_button"] = ctk.CTkButton(master=save_button_frame, text="保存设置", command=self._save_settings_action, height=35)
        self.elements["save_button"].pack(fill="x", padx=0, expand=True) 
        settings_content_frame.grid_columnconfigure(1, weight=1)
        self._populate_settings_ui()


    def _create_logs_widgets(self, parent_frame):
       
        self.elements["logs_textbox"] = ctk.CTkTextbox(master=parent_frame, wrap="word", state="disabled", font=("Consolas", 10), border_width=1, border_color="gray75")
        self.elements["logs_textbox"].pack(pady=(0,10), padx=10, fill="both", expand=True)
        ctk.CTkButton(master=parent_frame, text="清空日志", command=self._clear_logs_action, height=30).pack(pady=(0,10), fill="x", padx=100)


    def log_message(self, message):
        if "logs_textbox" in self.elements and self.elements["logs_textbox"].winfo_exists():
            self.elements["logs_textbox"].configure(state="normal")
            self.elements["logs_textbox"].insert("end", message + "\n")
            self.elements["logs_textbox"].configure(state="disabled")
            self.elements["logs_textbox"].see("end")
        else:
            print(f"[UIManager Log Direct] {message}") # Fallback if textbox not ready

    def update_status_display(self, status_text):
        self.status_var.set(status_text)
        is_running = status_text == "运行中"
        is_starting_stopping = status_text in ["启动中...", "停止中..."]

        if "start_button" in self.elements and self.elements["start_button"].winfo_exists():
            self.elements["start_button"].configure(state="disabled" if is_running or is_starting_stopping else "normal")
        if "stop_button" in self.elements and self.elements["stop_button"].winfo_exists():
            self.elements["stop_button"].configure(state="disabled" if not is_running or is_starting_stopping else "normal")
        if "open_ui_button" in self.elements and self.elements["open_ui_button"].winfo_exists():
            self.elements["open_ui_button"].configure(state="normal" if is_running else "disabled")
        self._update_scan_button_state()
        
    def _update_scan_button_state(self):
        if "scan_library_button" in self.elements and self.elements["scan_library_button"].winfo_exists():
            if backend_manager.is_running():
                self.elements["scan_library_button"].configure(state="normal")
            else:
                self.elements["scan_library_button"].configure(state="disabled")
    
    def _populate_settings_ui(self):
       
        cfg = config.current_config
        self.elements["host_entry"].delete(0, tk.END); self.elements["host_entry"].insert(0, cfg.get("api_host", ""))
        self.elements["port_entry"].delete(0, tk.END); self.elements["port_entry"].insert(0, cfg.get("api_port", ""))
        self.video_paths_listbox.delete(0, tk.END)
        for path_item in cfg.get("video_paths", []): self.video_paths_listbox.insert(tk.END, path_item)
        self.elements["backend_script_entry"].delete(0, tk.END); self.elements["backend_script_entry"].insert(0, cfg.get("backend_script_path", ""))

    def _update_config_from_ui(self):
       
        config.update_setting("api_host", self.elements["host_entry"].get())
        config.update_setting("api_port", self.elements["port_entry"].get())
        config.update_setting("video_paths", list(self.video_paths_listbox.get(0, tk.END)))
        config.update_setting("backend_script_path", self.elements["backend_script_entry"].get())

    def _save_settings_action(self):
       
        self._update_config_from_ui()
        config.save_config()
        messagebox.showinfo("设置", "设置已成功保存！")
        self.log_message("配置已保存。")

    def _add_video_path_dialog(self):
       
        path = filedialog.askdirectory(title="选择视频库文件夹")
        if path and path not in self.video_paths_listbox.get(0, tk.END): self.video_paths_listbox.insert(tk.END, path)

    def _remove_selected_video_path(self):
       
        selected_indices = self.video_paths_listbox.curselection()
        if not selected_indices: messagebox.showwarning("提示", "请选择要移除的路径."); return
        for i in reversed(selected_indices): self.video_paths_listbox.delete(i)

    def _browse_backend_script(self):
       
        initial_dir = os.path.abspath(".")
        script_p = filedialog.askopenfilename(initialdir=initial_dir, title="选择后端 Python 脚本", filetypes=(("Python files", "*.py"), ("All files", "*.*")))
        if script_p:
            try:
                relative_path = os.path.relpath(script_p, initial_dir)
                final_path_to_show = relative_path if not (".." in relative_path and relative_path.count("..") > 1) else script_p
            except ValueError: final_path_to_show = script_p
            self.elements["backend_script_entry"].delete(0, tk.END); self.elements["backend_script_entry"].insert(0, final_path_to_show)

    def _start_backend_action_ui(self):
        cfg = config.current_config
        video_paths_str = ",".join(cfg.get("video_paths", []))
        backend_script_relative_path = cfg.get("backend_script_path", "run_backend_server.py")
        
        # 在开发模式下，我们让后端使用其自身的默认数据路径
        # 只有在打包后，Electron才会指定数据路径
        # 因此，这里传递 None 给 db_file_full_path 和 thumbnails_storage_full_path
        # 后端的 argparse 会接收到 None，然后 update_settings_from_args 不会覆盖它们
        # 从而 settings 对象的 @property 会使用 _data_storage_dir_default_for_dev
        
        dev_db_file_path_for_cmd = None # 传递 None，让后端使用自己的默认
        dev_thumbnails_storage_path_for_cmd = None # 传递 None

        # FFmpeg/FFprobe 路径仍然可以从启动器配置中读取并传递
        ffmpeg_path = cfg.get("ffmpeg_path") 
        ffprobe_path = cfg.get("ffprobe_path")

        self.log_message(f"启动器: 准备启动后端 (开发模式 - 后端将使用其默认数据路径)。")
        if ffmpeg_path: self.log_message(f"  FFmpeg可执行文件 (若配置): {ffmpeg_path}")
        if ffprobe_path: self.log_message(f"  FFprobe可执行文件 (若配置): {ffprobe_path}")

        success = backend_manager.start(
            script_path=backend_script_relative_path, 
            host=cfg.get("api_host", "127.0.0.1"), 
            port=cfg.get("api_port", "8000"), 
            video_paths_str=video_paths_str,
            db_file_full_path=dev_db_file_path_for_cmd, # 传递 None
            thumbnails_storage_full_path=dev_thumbnails_storage_path_for_cmd, # 传递 None
            ffmpeg_exec_path=ffmpeg_path,
            ffprobe_exec_path=ffprobe_path
        )
        if not success and not backend_manager.is_running():
             messagebox.showerror("启动失败", "启动后端服务失败，请检查运行日志获取详细信息。")
        self._update_scan_button_state()

    def _stop_backend_action_ui(self):
        backend_manager.stop()
        self._update_scan_button_state()

   
    def _trigger_scan_library_action(self):
        if not backend_manager.is_running():
            messagebox.showwarning("提示", "后端服务未运行，无法扫描视频库。")
            return

        self.log_message("启动器: 发送扫描视频库请求到后端...")
        self.elements["scan_library_button"].configure(state="disabled", text="扫描中...")

        def send_scan_request():
            api_host = config.current_config.get("api_host", "127.0.0.1")
            api_port = config.current_config.get("api_port", "8000")
            scan_url = f"http://{api_host}:{api_port}/api/scan-library"
            
            try:
               
                req = urllib.request.Request(scan_url, method="POST")
                with urllib.request.urlopen(req, timeout=10) as response:
                    response_data = response.read().decode('utf-8')
                    try:
                        json_response = json.loads(response_data)
                        self.log_message(f"启动器: 后端扫描API响应: {json_response.get('message', response_data)}")
                    except json.JSONDecodeError:
                        self.log_message(f"启动器: 后端扫描API响应 (非JSON): {response_data}")
            except urllib.error.URLError as e:
                self.log_message(f"启动器: 调用扫描API失败 (URLError): {e.reason}")
                messagebox.showerror("扫描失败", f"无法连接到后端扫描API: {e.reason}")
            except Exception as e:
                self.log_message(f"启动器: 调用扫描API时发生未知错误: {e}")
                messagebox.showerror("扫描失败", f"调用扫描API时发生错误: {e}")
            finally:
               
               
                if self.app:
                    self.app.after(100, self._restore_scan_button)

       
        scan_thread = threading.Thread(target=send_scan_request, daemon=True)
        scan_thread.start()

    def _restore_scan_button(self):
        """恢复扫描按钮的状态和文本"""
        if "scan_library_button" in self.elements:
            self.elements["scan_library_button"].configure(text="扫描/更新视频库")
            self._update_scan_button_state()

   
   
    def _start_backend_action(self):
        self._start_backend_action_ui()


    def _open_web_ui_action(self):
       
        host = config.current_config.get("api_host", "127.0.0.1"); port = config.current_config.get("api_port", "8000")
        url = f"http://{host}:{port}"; webbrowser.open(url)

    def _clear_logs_action(self):
       
        if "logs_textbox" in self.elements:
            self.elements["logs_textbox"].configure(state="normal"); self.elements["logs_textbox"].delete("1.0", tk.END)
            self.elements["logs_textbox"].configure(state="disabled")
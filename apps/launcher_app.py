import customtkinter as ctk
from tkinter import messagebox
from config import launcher_settings as config
from components import backend_controller as backend_manager
from components import launcher_ui as ui_manager

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        config.load_config() 
        ctk.set_appearance_mode(config.current_config.get("theme", "light")) 

        self.ui_manager_instance = ui_manager.UIManager(self)
        self.ui_manager_instance.setup_main_layout()

        backend_manager.set_callbacks(
            self.ui_manager_instance.log_message, 
            self.ui_manager_instance.update_status_display
        )
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _on_closing(self):
        if backend_manager.is_running():
            if messagebox.askyesno("退出确认", "后端服务仍在运行中，是否停止并退出？", icon='warning'):
                backend_manager.stop()
                self.destroy()
            else:
                return 
        else:
            self.destroy()
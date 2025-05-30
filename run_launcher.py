
import sys 




if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception as e:
        print(f"Warning: Failed to reconfigure stdout encoding to utf-8: {e}")
if sys.stderr.encoding != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception as e:
        print(f"Warning: Failed to reconfigure stderr encoding to utf-8: {e}")


from apps.launcher_app import App

if __name__ == "__main__":
    
    
    app_instance = App()
    app_instance.mainloop()
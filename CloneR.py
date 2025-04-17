import tkinter as tk
from tkinter import filedialog, messagebox
import os
import shutil
import webbrowser
import pyperclip
import threading
import time
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

def get_user_home():
    return os.path.expanduser("~")

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def replace_user_variable(path):
    if "%USER%" in path:
        path = path.replace("%USER%", get_user_home())
    return path

def browse_file_destination(entry_widget):
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, folder_selected)

def find_downloaded_file(download_folder):
    files = os.listdir(download_folder)
    files = [f for f in files if os.path.isfile(os.path.join(download_folder, f))]
    if files:
        latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(download_folder, f)))
        return os.path.join(download_folder, latest_file)
    return None

class DownloadHandler(FileSystemEventHandler):
    def __init__(self, dest_path, callback, observer):
        self.dest_path = dest_path
        self.callback = callback
        self.observer = observer
        self.download_timers = {}

    def on_created(self, event):
        print(f"[作成検出] {event.src_path}")

    def on_modified(self, event):
        if not event.is_directory:
            file_path = event.src_path
            if file_path.endswith((".crdownload", ".part", ".tmp")):
                return
            if file_path in self.download_timers:
                self.download_timers[file_path].cancel()
            timer = threading.Timer(3.0, self.handle_download_complete, args=[file_path])
            self.download_timers[file_path] = timer
            timer.start()

    def handle_download_complete(self, file_path):
        print(f"[確認開始] {file_path}")
        if not self.is_download_complete(file_path):
            print("[未完了] サイズ不安定またはロック中")
            return
        try:
            os.makedirs(self.dest_path, exist_ok=True)
            shutil.copy(file_path, self.dest_path)
            self.callback(success=True, path=self.dest_path)
        except Exception as e:
            self.callback(success=False, error=str(e))
        finally:
            self.observer.stop()

    def is_download_complete(self, file_path):
        try:
            last_size = -1
            for _ in range(5):
                current_size = os.path.getsize(file_path)
                if current_size == last_size and self.is_file_ready(file_path):
                    return True
                last_size = current_size
                time.sleep(1.5)
            return False
        except Exception:
            return False

    def is_file_ready(self, path):
        try:
            with open(path, 'rb'):
                return True
        except IOError:
            return False

    def is_download_complete(self, file_path):
        try:
            initial_size = os.path.getsize(file_path)
            for _ in range(5):
                time.sleep(2)
                final_size = os.path.getsize(file_path)
                if initial_size == final_size:
                    return True
                initial_size = final_size
            return False
        except Exception:
            return False

def place_file_from_web(code):
    if "|" not in code:
        messagebox.showerror("エラー", "無効なコード形式です（URL|配置先パス）")
        return
    url, raw_path = code.split("|", 1)
    raw_path = raw_path.strip()
    dest_path = replace_user_variable(raw_path)
    dest_path = os.path.expanduser(dest_path)
    download_folder = os.path.join(get_user_home(), "Downloads")
    def finish(success, path=None, error=None):
        if success:
            success_win = tk.Toplevel(root)
            success_win.title("完了")
            success_win.geometry("400x150")
            success_win.resizable(False, False)
            tk.Label(success_win, text="ファイルを配置しました：", font=("Arial", 11)).pack(pady=(20, 5))
            tk.Label(success_win, text=path, wraplength=380, fg="gray", font=("Arial", 9)).pack()
            open_btn = tk.Button(success_win, text="配置先フォルダを開く", command=lambda: open_folder(path))
            open_btn.pack(pady=(10, 5))
            ok_btn = tk.Button(success_win, text="OK", command=success_win.destroy)
            ok_btn.pack()
        else:
            messagebox.showerror("エラー", f"ファイルの配置中に問題が発生しました:\n{error}")
    observer = Observer()
    event_handler = DownloadHandler(dest_path, finish, observer)
    observer.schedule(event_handler, download_folder, recursive=False)
    observer.start()
    webbrowser.open(url)
    observer.join()

def open_folder(path):
    try:
        os.startfile(path)
    except Exception as e:
        messagebox.showerror("エラー", f"フォルダを開くことができませんでした:\n{e}")
def on_submit():
    code = code_entry.get()
    threading.Thread(target=place_file_from_web, args=(code,), daemon=True).start()

def on_generate_code():
    def generate():
        url = url_entry.get().strip()
        path = path_entry.get().strip()
        if not url or not path:
            messagebox.showerror("エラー", "URLと配置パスの両方を入力してください")
            return
        code = f"{url}|{path}"
        pyperclip.copy(code)
        messagebox.showinfo("成功", "コードをクリップボードにコピーしました")

    generator = tk.Toplevel(root)
    generator.title("配布用コード生成")
    tk.Label(generator, text="ダウンロードURL:").pack(pady=(10, 0))
    url_entry = tk.Entry(generator, width=60)
    url_entry.pack()
    tk.Label(generator, text="配置先パス:").pack(pady=(10, 0))
    path_entry = tk.Entry(generator, width=60)
    path_entry.pack()
    browse_btn = tk.Button(generator, text="配置先を選択", command=lambda: browse_file_destination(path_entry))
    browse_btn.pack(pady=5)
    generate_btn = tk.Button(generator, text="コード生成（コピー）", command=generate)
    generate_btn.pack(pady=10)

root = tk.Tk()
root.title("Cloner")
root.geometry("500x250")
root.iconbitmap(resource_path("Cloner.ico"))
tk.Label(root, text="コードを入力してください（URL|配置パス）:").pack(pady=10)
code_entry = tk.Entry(root, width=60)
code_entry.pack()
submit_btn = tk.Button(root, text="配置開始", command=on_submit)
submit_btn.pack(pady=10)
generate_code_btn = tk.Button(root, text="配布用コード生成", command=on_generate_code)
generate_code_btn.pack(pady=10)
credit_label = tk.Label(root, text="制作:Shake_1227", fg="gray", cursor="hand2", font=("Arial", 8))
credit_label.place(relx=1.0, rely=1.0, anchor="se", x=-10, y=-10)

def open_creator_url(event):
    webbrowser.open("https://x.com/Shake_1227")

credit_label.bind("<Button-1>", open_creator_url)
root.mainloop()

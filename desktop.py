import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Добавляем корень проекта в путь чтобы creds.py был доступен
_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

import threading
import time
import socket
import tkinter as tk
import requests as req_lib
import webview
from app import create_app
from version import __version__

GITHUB_REPO = "dombroviki/kabinet-technologa"
CHECK_UPDATE_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

app = create_app()

def start_flask():
    app.run(port=5000, debug=False, use_reloader=False)

def wait_for_flask(host='127.0.0.1', port=5000, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.1)
    return False

def check_for_updates():
    """Проверяет GitHub Releases. Возвращает (latest_version, download_url) или None."""
    try:
        r = req_lib.get(CHECK_UPDATE_URL, timeout=5)
        if r.status_code != 200:
            return None
        data = r.json()
        latest = data.get("tag_name", "").lstrip("v")
        if not latest:
            return None
        # Ищем .exe в assets
        assets = data.get("assets", [])
        download_url = data.get("html_url", "")  # fallback — страница релиза
        for asset in assets:
            if asset["name"].endswith(".exe"):
                download_url = asset["browser_download_url"]
                break
        return latest, download_url
    except Exception:
        return None

def version_tuple(v):
    return tuple(int(x) for x in v.split("."))

def show_update_dialog(latest_version, download_url):
    """Диалог с прогрессом скачивания и авто-запуском установщика."""
    root = tk.Tk()
    root.title("Доступно обновление")
    root.configure(bg='#0e1120')
    root.resizable(False, False)

    w, h = 420, 220
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f'{w}x{h}+{(sw-w)//2}+{(sh-h)//2}')
    root.attributes('-topmost', True)

    tk.Label(root, text='🆕 Доступно обновление',
             font=('Segoe UI', 13, 'bold'), bg='#0e1120', fg='#f8faff').pack(pady=(24, 6))
    tk.Label(root, text=f'Версия {latest_version}  (у вас {__version__})',
             font=('Segoe UI', 10), bg='#0e1120', fg='#7280a8').pack()

    status_label = tk.Label(root, text='',
                            font=('Segoe UI', 9), bg='#0e1120', fg='#60a5fa')
    status_label.pack(pady=(10, 4))

    progress_var = tk.DoubleVar()
    progress = tk.Canvas(root, width=340, height=8, bg='#1d2135',
                         highlightthickness=0, bd=0)
    progress.pack()
    bar = progress.create_rectangle(0, 0, 0, 8, fill='#60a5fa', width=0)

    btn_frame = tk.Frame(root, bg='#0e1120')
    btn_frame.pack(pady=16)

    def do_update():
        update_btn.config(state='disabled')
        skip_btn.config(state='disabled')

        def download():
            try:
                status_label.config(text='Скачивание...')
                import tempfile, subprocess, sys

                tmp = tempfile.gettempdir()
                fname = f"КабинетТехнолога_setup_{latest_version}.exe"
                fpath = os.path.join(tmp, fname)

                r = req_lib.get(download_url, stream=True, timeout=60)
                total = int(r.headers.get('content-length', 0))
                downloaded = 0

                with open(fpath, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total:
                                pct = downloaded / total
                                progress.coords(bar, 0, 0, 340 * pct, 8)
                                status_label.config(
                                    text=f'Скачивание... {int(pct*100)}%'
                                )

                status_label.config(text='Запуск установщика...')
                root.after(800, root.destroy)
                subprocess.Popen([fpath])
                # Закрываем приложение
                os._exit(0)

            except Exception as e:
                status_label.config(text=f'Ошибка: {e}', fg='#f87171')
                update_btn.config(state='normal')
                skip_btn.config(state='normal')

        threading.Thread(target=download, daemon=True).start()

    update_btn = tk.Button(btn_frame, text='  Обновить  ',
                           font=('Segoe UI', 10, 'bold'),
                           bg='#60a5fa', fg='#0e1120', relief='flat',
                           cursor='hand2', command=do_update)
    update_btn.pack(side='left', padx=8)

    skip_btn = tk.Button(btn_frame, text='  Пропустить  ',
                         font=('Segoe UI', 10),
                         bg='#1d2135', fg='#b8c0e0', relief='flat',
                         cursor='hand2', command=root.destroy)
    skip_btn.pack(side='left', padx=8)

    root.mainloop()

def run_update_check():
    """Запускается в фоне после старта приложения."""
    time.sleep(3)
    result = check_for_updates()
    if result is None:
        return
    latest, download_url = result
    try:
        if version_tuple(latest) > version_tuple(__version__):
            show_update_dialog(latest, download_url)
    except Exception:
        pass


# ── АВТОЗАПУСК ──────────────────────────────────────────────────────────────

AUTOSTART_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_NAME = "КабинетТехнолога"

def is_autostart_enabled():
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, AUTOSTART_NAME)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False

def set_autostart(enable: bool):
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_SET_VALUE)
        if enable:
            exe_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
            winreg.SetValueEx(key, AUTOSTART_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
        else:
            try:
                winreg.DeleteValue(key, AUTOSTART_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Autostart error: {e}")


# ── СИСТЕМНЫЙ ТРЕЙ ───────────────────────────────────────────────────────────

_tray_icon = None
_webview_window = None

def _make_tray_image():
    try:
        from PIL import Image, ImageDraw
        img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([4, 4, 60, 60], radius=14, fill=(91, 141, 238, 255))
        return img
    except Exception:
        from PIL import Image
        return Image.new('RGB', (64, 64), color=(91, 141, 238))

def _show_window():
    if _webview_window:
        try:
            _webview_window.show()
        except Exception:
            pass

def _toggle_autostart_menu(icon, item):
    set_autostart(not is_autostart_enabled())

def _exit_app(icon, item):
    icon.stop()
    os._exit(0)

def start_tray():
    global _tray_icon
    try:
        import pystray
        from pystray import MenuItem as Item, Menu

        menu = Menu(
            Item('Открыть', lambda icon, item: _show_window(), default=True),
            Menu.SEPARATOR,
            Item('Автозапуск при старте Windows',
                 _toggle_autostart_menu,
                 checked=lambda item: is_autostart_enabled()),
            Menu.SEPARATOR,
            Item('Выход', _exit_app),
        )
        _tray_icon = pystray.Icon(
            AUTOSTART_NAME,
            _make_tray_image(),
            f'Кабинет технолога v{__version__}',
            menu,
        )
        _tray_icon.run()
    except Exception as e:
        print(f"Tray error: {e}")

def show_splash():
    root = tk.Tk()
    root.overrideredirect(True)
    root.configure(bg='#0e1120')
    root.attributes('-topmost', True)

    w, h = 420, 220
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f'{w}x{h}+{(sw-w)//2}+{(sh-h)//2}')

    tk.Label(root, text='📺', font=('Segoe UI Emoji', 42),
             bg='#0e1120', fg='#f8faff').pack(pady=(32, 8))
    tk.Label(root, text='Кабинет технолога', font=('Segoe UI', 16, 'bold'),
             bg='#0e1120', fg='#f8faff').pack()
    tk.Label(root, text=f'v{__version__}', font=('Segoe UI', 10),
             bg='#0e1120', fg='#60a5fa').pack(pady=(4, 0))
    tk.Label(root, text='Запуск...', font=('Segoe UI', 10),
             bg='#0e1120', fg='#7280a8').pack(pady=(4, 0))

    dots_label = tk.Label(root, text='●○○', font=('Segoe UI', 12),
                          bg='#0e1120', fg='#60a5fa')
    dots_label.pack(pady=(10, 0))

    frames = ['●○○', '○●○', '○○●', '○●○']
    frame_idx = [0]

    def animate():
        dots_label.config(text=frames[frame_idx[0] % len(frames)])
        frame_idx[0] += 1
        root.after(300, animate)

    animate()
    return root

if __name__ == '__main__':
    import platform
    print(f"HOME: {os.path.expanduser('~')}")
    print(f"USERNAME: {os.environ.get('USERNAME')}")
    print(f"NODE: {platform.node()}")
    t = threading.Thread(target=start_flask, daemon=True)
    t.start()

    splash = show_splash()

    def wait_and_close():
        start = time.time()
        wait_for_flask()
        elapsed = time.time() - start
        if elapsed < 1.5:
            time.sleep(1.5 - elapsed)
        splash.after(0, splash.destroy)

    threading.Thread(target=wait_and_close, daemon=True).start()
    splash.mainloop()

    # Проверка обновлений до запуска webview (tkinter требует главный тред)
    result = check_for_updates()
    if result:
        latest, download_url = result
        try:
            if version_tuple(latest) > version_tuple(__version__):
                show_update_dialog(latest, download_url)
        except Exception:
            pass

    webview_window = webview.create_window(
        f'Кабинет технолога v{__version__}',
        'http://127.0.0.1:5000/desktop-autologin',
        width=1400,
        height=900,
        min_size=(800, 600),
    )

    globals()['_webview_window'] = webview_window

    def on_closing():
        try:
            webview_window.hide()
        except Exception:
            pass
        return False

    webview_window.events.closing += on_closing
    threading.Thread(target=start_tray, daemon=True).start()

    webview.start(storage_path=os.path.join(os.path.expanduser('~'), '.kabinet_technologa'))


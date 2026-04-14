import os
from dotenv import load_dotenv
load_dotenv()

import threading
import time
import webview
from app import create_app

app = create_app()

def start_flask():
    app.run(port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    t = threading.Thread(target=start_flask, daemon=True)
    t.start()
    time.sleep(2)

    webview.create_window(
        'Кабинет технолога',
        'http://127.0.0.1:5000',
        width=1400,
        height=900,
        min_size=(800, 600),
    )
    webview.start()

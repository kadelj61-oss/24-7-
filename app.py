from flask import Flask, Response
import io
import time
from PIL import Image, ImageDraw
import threading

app = Flask(__name__)

# Fake camera buffer
camera_buffer = bytearray(3 * 1920 * 1080)  # RGB buffer
buffer_lock = threading.Lock()
buffer_fill = 0

def fake_camera_thread():
    """Simulate camera filling buffer"""
    global buffer_fill
    while True:
        with buffer_lock:
            # Simulate slow buffer fill (1% per second)
            if buffer_fill < 100:
                buffer_fill += 1
        time.sleep(1)

# Start fake camera thread
camera_thread = threading.Thread(target=fake_camera_thread, daemon=True)
camera_thread.start()

@app.route('/')
def index():
    """Web UI"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>24-7 Camera Stream</title>
        <style>
            body { font-family: Arial; text-align: center; margin-top: 50px; }
            .buffer { width: 300px; height: 30px; border: 2px solid #ccc; margin: 20px auto; }
            .fill { height: 100%; background: #4CAF50; width: 0%; transition: width 0.3s; }
            h1 { color: #333; }
        </style>
    </head>
    <body>
        <h1>📺 24-7 Camera Stream</h1>
        <h2 id="buffer">Buffer: 0%</h2>
        <div class="buffer">
            <div class="fill" id="fill"></div>
        </div>
        <script>
            setInterval(() => {
                fetch('/status/hd').then(r => r.json()).then(data => {
                    document.getElementById('buffer').textContent = `Buffer: ${data.buffer_fill}%`;
                    document.getElementById('fill').style.width = data.buffer_fill + '%';
                });
            }, 1000);
        </script>
    </body>
    </html>
    """

@app.route('/status/<quality>')
def status(quality):
    """Return camera status"""
    with buffer_lock:
        return {"buffer_fill": buffer_fill}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

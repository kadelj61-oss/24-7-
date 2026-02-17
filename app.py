from flask import Flask, Response, jsonify
import cv2
import threading
import time
from collections import deque

app = Flask(__name__)

# Config
CAMERA_ID = "http://192.168.1.72:8080/video"  # << Use your MJPEG stream here!
frame_buffer = deque(maxlen=30)
buffer_fill = 0
camera_lock = threading.Lock()

def capture_thread():
    """Capture frames from camera or network stream"""
    global buffer_fill
    cap = cv2.VideoCapture(CAMERA_ID)
    
    if not cap.isOpened():
        print("❌ Camera or stream not found!")
        return
    
    print("✅ Camera or stream opened")
    
    while True:
        ret, frame = cap.read()
        if ret:
            with camera_lock:
                frame_buffer.append(frame)
                buffer_fill = min(100, (len(frame_buffer) / 30.0) * 100)
        time.sleep(0.033)

def stream_generator():
    """Generate MJPEG stream"""
    while True:
        with camera_lock:
            if len(frame_buffer) == 0:
                time.sleep(0.1)
                continue
            frame = frame_buffer[-1].copy()
        
        # Resize
        frame = cv2.resize(frame, (1280, 720))
        
        # Encode
        success, buffer = cv2.imencode('.jpg', frame)
        if not success:
            continue
        
        frame_data = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n'
               b'Content-Length: ' + str(len(frame_data)).encode() + b'\r\n\r\n' +
               frame_data + b'\r\n')

@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html>
    <body style="text-align: center; font-family: Arial; background: #f5f5f5; margin: 0; padding: 20px;">
        <div style="max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px;">
            <h1>📺 24-7 Camera Stream</h1>
            <img src="/video" style="max-width: 100%; border: 2px solid #ddd; border-radius: 4px;">
            <p>Buffer: <span id="buf">0%</span> | Status: <span id="stat">Connecting...</span></p>
            <script>
                setInterval(() => {
                    fetch('/api/status').then(r => r.json()).then(d => {
                        document.getElementById('buf').textContent = d.buffer.toFixed(1) + '%';
                        document.getElementById('stat').textContent = d.connected ? '✅ Connected' : '❌ Disconnected';
                    });
                }, 1000);
            </script>
        </div>
    </body>
    </html>
    """

@app.route('/video')
def video():
    return Response(stream_generator(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/status')
def api_status():
    return jsonify({
        'buffer': buffer_fill,
        'connected': len(frame_buffer) > 0
    })

if __name__ == '__main__':
    print("🎥 Starting camera or stream capture...")
    t = threading.Thread(target=capture_thread, daemon=True)
    t.start()
    
    print("🌐 Open: http://localhost:8080")
    app.run(host='0.0.0.0', port=8080, debug=False)

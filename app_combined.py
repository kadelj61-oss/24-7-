from flask import Flask, Response, request, jsonify
import time
import os
from collections import deque
from threading import Lock, Thread
import cv2
import logging

from flask_cors import CORS

app = Flask(__name__)

# Add this after creating app
CORS(app, origins=[
    "https://kadelj61-oss.github.io",
    "http://localhost:*",
    "https://*.ngrok.io",
    "https://*.ngrok-free.app",
    "https://*.ngrok-free.dev"
])

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

frame_buffers = {
    'hd': deque(maxlen=30),
    'sd': deque(maxlen=30),
    'uhd': deque(maxlen=30)
}
buffer_lock = Lock()

def camera_thread():
    """Capture from webcam in background"""
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    
    logging.info("Camera thread started")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            logging.warning("Failed to capture frame")
            time.sleep(1)
            continue
        
        # Encode as JPEG
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        
        with buffer_lock:
            frame_buffers['hd'].append(buffer.tobytes())
        
        time.sleep(0.033)  # ~30fps
    
    cap.release()

@app.route('/stream/<quality>')
def stream(quality):
    if quality not in frame_buffers:
        return "Invalid quality", 404

    def generate():
        while True:
            with buffer_lock:
                if frame_buffers[quality]:
                    frame = frame_buffers[quality][-1]
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.033)

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return """
    <html>
    <body>
    <h1>24/7 Camera Stream</h1>
    <img src="/stream/hd" width="1280">
    </body>
    </html>
    """

@app.route('/health')
def health():
    return 'OK', 200

if __name__ == '__main__':
    # Start camera thread
    camera_t = Thread(target=camera_thread, daemon=True)
    camera_t.start()
    
    port = int(os.getenv('PORT', 8080))
    print(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, threaded=True)
  

import os
import cv2
from flask import Flask, jsonify, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=[
    "https://kadelj61-oss.github.io",
    "https://*.up.railway.app",
    "https://direction-may-banners-december.trycloudflare.com"
])

@app.route('/')
def home():
    return 'Flask server is running!', 200

from flask import jsonify

@app.route('/health')
def health():
    return jsonify({"status": "OK"})

@app.route('/api/stats')
def api_stats():
    return jsonify({
        "status": "online",
        "resolution": "1920x1080",
        "fps": 30,
        "bitrate": "3Mbps",
        "viewers": 1
    })

def gen_frames():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Camera could not be opened!")
        return
    while True:
        success, frame = cap.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    cap.release()

@app.route('/stream')
def stream():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

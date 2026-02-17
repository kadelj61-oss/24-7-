import os
import cv2
from flask import Flask, Response

app = Flask(__name__)

# First, try to read from environment variable, or use direct assignment
CAMERA_SOURCE = os.getenv("CAMERA_SOURCE", "http://192.168.1.72:8080/video")
cap = cv2.VideoCapture(CAMERA_SOURCE)

def gen_frames():
    while True:
        success, frame = cap.read()
        if not success:
            break
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video')
def video():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# ...rest of your Flask app...

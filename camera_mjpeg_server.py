from flask import Flask, Response
import cv2

app = Flask(__name__)

# Try 0 or 1 if you have multiple cameras; 0 is usually the built-in, 1 is often USB
CAMERA_ID = 1
cap = cv2.VideoCapture(CAMERA_ID)

def gen_frames():
    while True:
        success, frame = cap.read()
        if not success:
            break
        # Optionally resize: frame = cv2.resize(frame, (1280, 720))
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    return '''
    <html>
    <head><title>USB Camera MJPEG Stream</title></head>
    <body>
    <h1>USB Camera Stream</h1>
    <img src="/video" width="640" />
    </body>
    </html>
    '''

@app.route('/video')
def video():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("Camera server running! Open http://localhost:8080 in your browser.")
    app.run(host='0.0.0.0', port=8080)

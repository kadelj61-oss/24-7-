from flask import Flask, Response, render_template
from PIL import Image
import numpy as np
import io

app = Flask(__name__)

# Fake camera frame generator for testing
def fake_camera_stream():
    buffer = io.BytesIO()
    while True:
        # Create a fake frame (e.g. random noise)
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        # Convert to PIL Image and encode to JPEG
        img = Image.fromarray(frame, 'RGB')
        buffer.seek(0)
        buffer.truncate()
        img.save(buffer, format='JPEG', quality=85)
        frame_bytes = buffer.getvalue()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(fake_camera_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

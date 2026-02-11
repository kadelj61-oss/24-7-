from flask import Flask, Response, request, jsonify
import io
from collections import deque
from threading import Lock

app = Flask(__name__)

# Store frames in memory (last 30 frames per quality)
frame_buffers = {
    'hd': deque(maxlen=30),
    'sd': deque(maxlen=30),
    'uhd': deque(maxlen=30)
}
buffer_lock = Lock()

@app.route('/upload/<quality>', methods=['POST'])
def upload_frame(quality):
    """Receive frames from local camera"""
    if quality not in frame_buffers:
        return jsonify({'error': 'Invalid quality'}), 400
    
    frame_data = request.data
    if not frame_data:
        return jsonify({'error': 'No frame data'}), 400
    
    with buffer_lock:
        frame_buffers[quality].append(frame_data)
    
    return jsonify({'status': 'ok', 'buffer_size': len(frame_buffers[quality])}), 200

@app.route('/stream/<quality>')
def stream(quality):
    """Serve the stream to viewers"""
    if quality not in frame_buffers:
        return "Invalid quality", 404
    
    def generate():
        while True:
            with buffer_lock:
                if frame_buffers[quality]:
                    frame = frame_buffers[quality][-1]  # Get latest frame
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.033)  # ~30fps
    
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

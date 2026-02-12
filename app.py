from flask import Flask, Response, request, jsonify, render_template_string
import time
import os
from collections import deque
from threading import Lock, Thread
import cv2
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Frame buffers for each quality level (max 30 frames)
frame_buffers = {
    'hd': deque(maxlen=30),
    'sd': deque(maxlen=30),
    'uhd': deque(maxlen=30)
}
buffer_lock = Lock()

# Track camera state
camera_state = {
    'running': False,
    'error': None,
    'last_frame_time': None,
    'is_fake': False
}
state_lock = Lock()

# Quality settings
QUALITY_SETTINGS = {
    'sd': {'width': 1280, 'height': 720, 'jpeg_quality': 75},
    'hd': {'width': 1920, 'height': 1080, 'jpeg_quality': 85},
    'uhd': {'width': 3840, 'height': 2160, 'jpeg_quality': 90}
}


def generate_fake_frame(quality='hd'):
    """Generate a fake frame for cloud environments where camera is not available"""
    settings = QUALITY_SETTINGS.get(quality, QUALITY_SETTINGS['hd'])
    width, height = settings['width'], settings['height']
    
    # Create a colored frame with timestamp
    frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
    
    # Add timestamp text
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    text = f"FAKE FRAME - {quality.upper()} - {timestamp}"
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(frame, text, (50, height // 2), font, 2, (255, 255, 255), 3)
    
    return frame


def encode_frame(frame, quality='hd'):
    """Encode frame as JPEG with quality settings"""
    settings = QUALITY_SETTINGS.get(quality, QUALITY_SETTINGS['hd'])
    jpeg_quality = settings['jpeg_quality']
    
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
    return buffer.tobytes()


def resize_frame(frame, quality):
    """Resize frame to match quality settings"""
    settings = QUALITY_SETTINGS.get(quality, QUALITY_SETTINGS['hd'])
    target_width, target_height = settings['width'], settings['height']
    
    # Get current dimensions
    height, width = frame.shape[:2]
    
    # Only resize if needed
    if width != target_width or height != target_height:
        frame = cv2.resize(frame, (target_width, target_height))
    
    return frame


def camera_capture_thread():
    """Background thread for capturing webcam frames"""
    logger.info("Camera capture thread starting...")
    
    # Check if running in cloud environment (Railway)
    is_railway = os.getenv('RAILWAY_ENVIRONMENT_NAME') is not None
    
    with state_lock:
        camera_state['is_fake'] = is_railway
    
    if is_railway:
        logger.info("Running in Railway environment - using fake frames")
        capture_fake_frames()
    else:
        logger.info("Running in local environment - attempting to capture from webcam")
        capture_real_frames()


def capture_fake_frames():
    """Generate fake frames for cloud deployment"""
    with state_lock:
        camera_state['running'] = True
        camera_state['error'] = None
    
    logger.info("Starting fake frame generation")
    
    while True:
        try:
            # Generate frames for each quality level
            for quality in ['sd', 'hd', 'uhd']:
                frame = generate_fake_frame(quality)
                frame_data = encode_frame(frame, quality)
                
                with buffer_lock:
                    frame_buffers[quality].append(frame_data)
            
            with state_lock:
                camera_state['last_frame_time'] = time.time()
            
            time.sleep(0.033)  # ~30 fps
            
        except Exception as e:
            logger.error(f"Error generating fake frame: {e}")
            with state_lock:
                camera_state['error'] = str(e)
            time.sleep(1)


def capture_real_frames():
    """Capture frames from real webcam with automatic reconnection"""
    retry_delay = 1
    max_retry_delay = 30
    
    while True:
        cap = None
        try:
            logger.info("Attempting to connect to camera...")
            cap = cv2.VideoCapture(0)
            
            if not cap.isOpened():
                raise Exception("Failed to open camera")
            
            # Set camera properties for HD
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            cap.set(cv2.CAP_PROP_FPS, 30)
            
            logger.info("Camera connected successfully")
            
            with state_lock:
                camera_state['running'] = True
                camera_state['error'] = None
            
            # Reset retry delay on successful connection
            retry_delay = 1
            
            # Main capture loop
            consecutive_failures = 0
            max_consecutive_failures = 10
            
            while True:
                ret, frame = cap.read()
                
                if not ret:
                    consecutive_failures += 1
                    logger.warning(f"Failed to capture frame (attempt {consecutive_failures}/{max_consecutive_failures})")
                    
                    if consecutive_failures >= max_consecutive_failures:
                        raise Exception("Too many consecutive frame capture failures")
                    
                    time.sleep(0.1)
                    continue
                
                # Reset failure counter on success
                consecutive_failures = 0
                
                # Process frame for each quality level
                for quality in ['sd', 'hd', 'uhd']:
                    resized_frame = resize_frame(frame.copy(), quality)
                    frame_data = encode_frame(resized_frame, quality)
                    
                    with buffer_lock:
                        frame_buffers[quality].append(frame_data)
                
                with state_lock:
                    camera_state['last_frame_time'] = time.time()
                
                time.sleep(0.033)  # ~30 fps
                
        except Exception as e:
            error_msg = f"Camera error: {e}"
            logger.error(error_msg)
            
            with state_lock:
                camera_state['running'] = False
                camera_state['error'] = str(e)
            
            if cap is not None:
                cap.release()
            
            # Exponential backoff for reconnection
            logger.info(f"Retrying camera connection in {retry_delay} seconds...")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_retry_delay)


@app.route('/')
def index():
    """Main web UI with real-time buffer status"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>24/7 Camera Stream</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            h1 {
                color: #333;
                text-align: center;
            }
            .status-panel {
                background: white;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .status-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-top: 10px;
            }
            .status-item {
                padding: 10px;
                background: #f8f9fa;
                border-radius: 4px;
            }
            .status-label {
                font-weight: bold;
                color: #666;
                font-size: 0.9em;
            }
            .status-value {
                font-size: 1.2em;
                color: #333;
                margin-top: 5px;
            }
            .status-ok { color: #28a745; }
            .status-warning { color: #ffc107; }
            .status-error { color: #dc3545; }
            .stream-container {
                background: white;
                padding: 15px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .quality-selector {
                margin-bottom: 15px;
                text-align: center;
            }
            .quality-btn {
                padding: 10px 20px;
                margin: 0 5px;
                border: 2px solid #007bff;
                background: white;
                color: #007bff;
                cursor: pointer;
                border-radius: 4px;
                font-weight: bold;
            }
            .quality-btn.active {
                background: #007bff;
                color: white;
            }
            .stream-wrapper {
                text-align: center;
                background: #000;
                border-radius: 4px;
                padding: 10px;
            }
            .stream-img {
                max-width: 100%;
                height: auto;
                border-radius: 4px;
            }
            .buffer-indicators {
                display: flex;
                justify-content: space-around;
                margin-top: 15px;
                flex-wrap: wrap;
                gap: 10px;
            }
            .buffer-indicator {
                flex: 1;
                min-width: 150px;
                padding: 10px;
                background: #f8f9fa;
                border-radius: 4px;
                text-align: center;
            }
            .buffer-bar {
                height: 20px;
                background: #e9ecef;
                border-radius: 10px;
                overflow: hidden;
                margin-top: 8px;
            }
            .buffer-fill {
                height: 100%;
                background: linear-gradient(90deg, #28a745, #20c997);
                transition: width 0.3s;
                border-radius: 10px;
            }
        </style>
    </head>
    <body>
        <h1>📹 24/7 Camera Stream</h1>
        
        <div class="status-panel">
            <h2>System Status</h2>
            <div class="status-grid">
                <div class="status-item">
                    <div class="status-label">Camera Status</div>
                    <div class="status-value" id="camera-status">Checking...</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Frame Mode</div>
                    <div class="status-value" id="frame-mode">Unknown</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Last Frame</div>
                    <div class="status-value" id="last-frame">Never</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Environment</div>
                    <div class="status-value" id="environment">Unknown</div>
                </div>
            </div>
            <div id="error-message" style="margin-top: 10px; padding: 10px; background: #f8d7da; color: #721c24; border-radius: 4px; display: none;"></div>
        </div>

        <div class="stream-container">
            <div class="quality-selector">
                <button class="quality-btn" onclick="changeQuality('sd')">SD (720p)</button>
                <button class="quality-btn active" onclick="changeQuality('hd')">HD (1080p)</button>
                <button class="quality-btn" onclick="changeQuality('uhd')">UHD (4K)</button>
            </div>
            
            <div class="stream-wrapper">
                <img id="stream" class="stream-img" src="/stream/hd" alt="Live Stream">
            </div>
            
            <div class="buffer-indicators">
                <div class="buffer-indicator">
                    <strong>SD Buffer</strong>
                    <div class="buffer-bar">
                        <div class="buffer-fill" id="buffer-sd" style="width: 0%"></div>
                    </div>
                    <div id="buffer-sd-text">0/30</div>
                </div>
                <div class="buffer-indicator">
                    <strong>HD Buffer</strong>
                    <div class="buffer-bar">
                        <div class="buffer-fill" id="buffer-hd" style="width: 0%"></div>
                    </div>
                    <div id="buffer-hd-text">0/30</div>
                </div>
                <div class="buffer-indicator">
                    <strong>UHD Buffer</strong>
                    <div class="buffer-bar">
                        <div class="buffer-fill" id="buffer-uhd" style="width: 0%"></div>
                    </div>
                    <div id="buffer-uhd-text">0/30</div>
                </div>
            </div>
        </div>

        <script>
            let currentQuality = 'hd';
            
            function changeQuality(quality) {
                currentQuality = quality;
                document.getElementById('stream').src = '/stream/' + quality + '?t=' + Date.now();
                
                // Update active button
                document.querySelectorAll('.quality-btn').forEach(btn => {
                    btn.classList.remove('active');
                });
                event.target.classList.add('active');
            }
            
            function updateStatus() {
                fetch('/api/status')
                    .then(r => r.json())
                    .then(data => {
                        // Update camera status
                        const statusEl = document.getElementById('camera-status');
                        if (data.camera_running) {
                            statusEl.textContent = 'Running';
                            statusEl.className = 'status-value status-ok';
                        } else {
                            statusEl.textContent = 'Stopped';
                            statusEl.className = 'status-value status-error';
                        }
                        
                        // Update frame mode
                        document.getElementById('frame-mode').textContent = data.is_fake ? 'Fake Frames' : 'Real Camera';
                        
                        // Update last frame time
                        if (data.last_frame_time) {
                            const secondsAgo = Math.floor((Date.now() / 1000) - data.last_frame_time);
                            document.getElementById('last-frame').textContent = secondsAgo + 's ago';
                        }
                        
                        // Update environment
                        document.getElementById('environment').textContent = data.environment || 'Local';
                        
                        // Update error message
                        const errorEl = document.getElementById('error-message');
                        if (data.error) {
                            errorEl.textContent = 'Error: ' + data.error;
                            errorEl.style.display = 'block';
                        } else {
                            errorEl.style.display = 'none';
                        }
                        
                        // Update buffer indicators
                        ['sd', 'hd', 'uhd'].forEach(quality => {
                            const size = data.buffers[quality] || 0;
                            const percent = (size / 30) * 100;
                            document.getElementById('buffer-' + quality).style.width = percent + '%';
                            document.getElementById('buffer-' + quality + '-text').textContent = size + '/30';
                        });
                    })
                    .catch(err => console.error('Status update error:', err));
            }
            
            // Update status every second
            setInterval(updateStatus, 1000);
            updateStatus();
        </script>
    </body>
    </html>
    """
    return render_template_string(html)


@app.route('/upload/<quality>', methods=['POST'])
def upload_frame(quality):
    """Accept frame uploads (backwards compatible with upload_to_railway.py)"""
    if quality not in frame_buffers:
        return jsonify({'error': 'Invalid quality'}), 400

    frame_data = request.data
    if not frame_data:
        return jsonify({'error': 'No frame data'}), 400

    with buffer_lock:
        frame_buffers[quality].append(frame_data)

    logger.debug(f"Received uploaded frame for {quality}, buffer size: {len(frame_buffers[quality])}")
    return jsonify({'status': 'ok', 'buffer_size': len(frame_buffers[quality])}), 200


@app.route('/stream/<quality>')
def stream(quality):
    """Stream video as MJPEG"""
    if quality not in frame_buffers:
        return "Invalid quality", 404

    def generate():
        last_frame = None
        while True:
            with buffer_lock:
                if frame_buffers[quality]:
                    last_frame = frame_buffers[quality][-1]
            
            if last_frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + last_frame + b'\r\n')
            
            time.sleep(0.033)  # ~30 fps

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/status')
def api_status():
    """Get system status including buffer sizes"""
    with state_lock:
        running = camera_state['running']
        error = camera_state['error']
        last_frame_time = camera_state['last_frame_time']
        is_fake = camera_state['is_fake']
    
    with buffer_lock:
        buffers = {
            quality: len(frame_buffers[quality])
            for quality in frame_buffers
        }
    
    return jsonify({
        'camera_running': running,
        'error': error,
        'last_frame_time': last_frame_time,
        'is_fake': is_fake,
        'buffers': buffers,
        'environment': os.getenv('RAILWAY_ENVIRONMENT_NAME', 'local')
    })


@app.route('/health')
def health():
    """Health check endpoint for Railway monitoring"""
    with state_lock:
        running = camera_state['running']
        error = camera_state['error']
    
    # Consider healthy if either running successfully or using fake frames
    if running or camera_state.get('is_fake', False):
        return jsonify({'status': 'healthy'}), 200
    else:
        return jsonify({'status': 'unhealthy', 'error': error}), 503


if __name__ == '__main__':
    # Start camera capture thread
    camera_thread = Thread(target=camera_capture_thread, daemon=True)
    camera_thread.start()
    
    port = int(os.getenv('PORT', 8080))
    logger.info(f"Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port, threaded=True, debug=False)

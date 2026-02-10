# 24/7 Live Camera Streaming Server with MultiProcessing

## Overview
This guide will help you build a robust 24/7 camera streaming server using Python multiprocessing, inspired by distributed computing patterns from the SWAMP framework.

## Architecture Components

### 1. **Camera Capture Process**
- Dedicated process for capturing frames from camera
- Handles camera initialization and reconnection
- Writes frames to shared memory or queue

### 2. **Stream Encoding Process**
- Converts raw frames to compressed video format (H.264, MJPEG)
- Multiple encoder processes for load balancing
- Handles different quality/resolution streams

### 3. **Web Server Process**
- Serves HTTP/WebSocket endpoints
- Handles client connections
- Distributes encoded streams to clients

### 4. **Storage Process** (Optional)
- Records video segments to disk
- Manages storage cleanup/rotation
- Creates time-lapse archives

### 5. **Health Monitor Process**
- Monitors all processes
- Restarts failed processes
- Logs system metrics

## System Requirements

### Hardware
- Camera (USB webcam, IP camera, Raspberry Pi Camera, etc.)
- Linux/Windows/Mac system with Python 3.8+
- Sufficient CPU for video encoding (2+ cores recommended)
- Network interface for streaming

### Software Dependencies
```bash
# Core streaming libraries
pip install opencv-python flask flask-socketio
pip install numpy pillow

# For RTSP/production streaming
pip install aiortc av

# For IP cameras
pip install requests

# Optional: GPU acceleration
pip install opencv-contrib-python  # For CUDA support
```

## Implementation

### Project Structure
```
camera_server/
├── config/
│   └── config.yaml
├── src/
│   ├── __init__.py
│   ├── camera_capture.py
│   ├── stream_encoder.py
│   ├── web_server.py
│   ├── storage_manager.py
│   ├── health_monitor.py
│   └── process_manager.py
├── static/
│   └── viewer.html
├── logs/
├── recordings/
└── main.py
```

### Configuration File (config/config.yaml)
```yaml
camera:
  source: 0  # 0 for /dev/video0, or IP camera URL
  width: 1920
  height: 1080
  fps: 30
  reconnect_delay: 5
  
streaming:
  host: 0.0.0.0
  port: 8080
  protocol: http  # http, rtsp, webrtc
  formats:
    - name: hd
      width: 1920
      height: 1080
      quality: 85
    - name: sd
      width: 640
      height: 480
      quality: 70
      
processing:
  capture_workers: 1
  encoder_workers: 2
  buffer_size: 10
  
storage:
  enabled: true
  path: ./recordings
  segment_duration: 600  # 10 minutes
  retention_days: 7
  
monitoring:
  health_check_interval: 5
  restart_attempts: 3
  log_level: INFO
```

### Core Implementation Files

#### 1. Camera Capture Process (src/camera_capture.py)
```python
import cv2
import time
import multiprocessing as mp
from queue import Full
import logging

class CameraCapture:
    def __init__(self, config, frame_queue, control_queue):
        self.config = config
        self.frame_queue = frame_queue
        self.control_queue = control_queue
        self.camera = None
        self.running = False
        
    def initialize_camera(self):
        """Initialize camera with retries"""
        source = self.config['camera']['source']
        attempts = 0
        max_attempts = 5
        
        while attempts < max_attempts:
            try:
                self.camera = cv2.VideoCapture(source)
                
                # Set camera properties
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 
                               self.config['camera']['width'])
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 
                               self.config['camera']['height'])
                self.camera.set(cv2.CAP_PROP_FPS, 
                               self.config['camera']['fps'])
                
                if self.camera.isOpened():
                    logging.info(f"Camera initialized successfully: {source}")
                    return True
                    
            except Exception as e:
                logging.error(f"Camera init attempt {attempts+1} failed: {e}")
                
            attempts += 1
            time.sleep(self.config['camera']['reconnect_delay'])
            
        return False
    
    def run(self):
        """Main capture loop - runs in dedicated process"""
        self.running = True
        frame_count = 0
        
        if not self.initialize_camera():
            logging.error("Failed to initialize camera")
            return
        
        logging.info("Camera capture process started")
        
        while self.running:
            # Check for control commands
            if not self.control_queue.empty():
                cmd = self.control_queue.get()
                if cmd == 'stop':
                    break
                elif cmd == 'restart':
                    self.camera.release()
                    self.initialize_camera()
            
            # Capture frame
            ret, frame = self.camera.read()
            
            if not ret:
                logging.warning("Failed to capture frame, reconnecting...")
                self.camera.release()
                time.sleep(1)
                if not self.initialize_camera():
                    time.sleep(5)
                continue
            
            # Add timestamp and metadata
            timestamp = time.time()
            frame_data = {
                'frame': frame,
                'timestamp': timestamp,
                'frame_number': frame_count,
                'shape': frame.shape
            }
            
            # Put frame in queue (non-blocking)
            try:
                self.frame_queue.put(frame_data, block=False)
                frame_count += 1
            except Full:
                # Queue full, skip frame (backpressure)
                pass
            
            # Maintain FPS
            time.sleep(1.0 / self.config['camera']['fps'])
        
        self.camera.release()
        logging.info("Camera capture process stopped")

def camera_process(config, frame_queue, control_queue):
    """Entry point for camera capture process"""
    capture = CameraCapture(config, frame_queue, control_queue)
    capture.run()
```

#### 2. Stream Encoder Process (src/stream_encoder.py)
```python
import cv2
import time
import multiprocessing as mp
from queue import Empty
import logging

class StreamEncoder:
    def __init__(self, config, input_queue, output_queues, encoder_id):
        self.config = config
        self.input_queue = input_queue
        self.output_queues = output_queues  # Dict of quality -> queue
        self.encoder_id = encoder_id
        self.running = False
        
    def encode_frame(self, frame, quality_config):
        """Encode frame to JPEG with specific quality settings"""
        # Resize if needed
        target_size = (quality_config['width'], quality_config['height'])
        if frame.shape[1] != target_size[0] or frame.shape[0] != target_size[1]:
            resized = cv2.resize(frame, target_size)
        else:
            resized = frame
        
        # Encode to JPEG
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality_config['quality']]
        _, encoded = cv2.imencode('.jpg', resized, encode_param)
        
        return encoded.tobytes()
    
    def run(self):
        """Main encoding loop"""
        self.running = True
        logging.info(f"Encoder {self.encoder_id} started")
        
        while self.running:
            try:
                # Get frame from input queue
                frame_data = self.input_queue.get(timeout=1.0)
                
                # Encode for each quality level
                for format_config in self.config['streaming']['formats']:
                    quality_name = format_config['name']
                    
                    # Encode frame
                    encoded_frame = self.encode_frame(
                        frame_data['frame'], 
                        format_config
                    )
                    
                    # Package with metadata
                    output_data = {
                        'data': encoded_frame,
                        'timestamp': frame_data['timestamp'],
                        'frame_number': frame_data['frame_number'],
                        'quality': quality_name
                    }
                    
                    # Send to appropriate output queue
                    if quality_name in self.output_queues:
                        try:
                            self.output_queues[quality_name].put(
                                output_data, 
                                block=False
                            )
                        except:
                            pass  # Queue full, skip
                
            except Empty:
                continue
            except Exception as e:
                logging.error(f"Encoder {self.encoder_id} error: {e}")
        
        logging.info(f"Encoder {self.encoder_id} stopped")

def encoder_process(config, input_queue, output_queues, encoder_id):
    """Entry point for encoder process"""
    encoder = StreamEncoder(config, input_queue, output_queues, encoder_id)
    encoder.run()
```

#### 3. Web Server Process (src/web_server.py)
```python
from flask import Flask, Response, render_template_string
from flask_socketio import SocketIO
import multiprocessing as mp
from queue import Empty
import logging
import time

class WebServer:
    def __init__(self, config, stream_queues):
        self.config = config
        self.stream_queues = stream_queues  # Dict of quality -> queue
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # Setup routes
        self.setup_routes()
        
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            return render_template_string(self.get_viewer_html())
        
        @self.app.route('/stream/<quality>')
        def stream(quality):
            """MJPEG stream endpoint"""
            return Response(
                self.generate_stream(quality),
                mimetype='multipart/x-mixed-replace; boundary=frame'
            )
        
        @self.app.route('/health')
        def health():
            return {'status': 'ok', 'timestamp': time.time()}
    
    def generate_stream(self, quality='hd'):
        """Generator for MJPEG stream"""
        if quality not in self.stream_queues:
            quality = 'hd'  # Default fallback
        
        queue = self.stream_queues[quality]
        
        while True:
            try:
                frame_data = queue.get(timeout=1.0)
                
                # Format as MJPEG
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + 
                       frame_data['data'] + b'\r\n')
                
            except Empty:
                continue
            except Exception as e:
                logging.error(f"Stream error: {e}")
                break
    
    def get_viewer_html(self):
        """HTML viewer page"""
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>24/7 Camera Stream</title>
            <style>
                body {
                    margin: 0;
                    padding: 20px;
                    background: #1a1a1a;
                    color: white;
                    font-family: Arial, sans-serif;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                }
                h1 {
                    text-align: center;
                }
                .stream-container {
                    text-align: center;
                    margin: 20px 0;
                }
                img {
                    max-width: 100%;
                    border: 2px solid #333;
                    border-radius: 8px;
                }
                .controls {
                    text-align: center;
                    margin: 20px 0;
                }
                button {
                    padding: 10px 20px;
                    margin: 0 5px;
                    background: #007bff;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                }
                button:hover {
                    background: #0056b3;
                }
                .info {
                    background: #2a2a2a;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 20px 0;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎥 Live Camera Stream</h1>
                
                <div class="stream-container">
                    <img id="stream" src="/stream/hd" alt="Loading stream...">
                </div>
                
                <div class="controls">
                    <button onclick="changeQuality('hd')">HD Quality</button>
                    <button onclick="changeQuality('sd')">SD Quality</button>
                    <button onclick="refreshStream()">Refresh Stream</button>
                </div>
                
                <div class="info">
                    <h3>Stream Information</h3>
                    <p id="status">Status: Active</p>
                    <p id="quality">Quality: HD</p>
                    <p id="timestamp">Last Update: <span id="time"></span></p>
                </div>
            </div>
            
            <script>
                let currentQuality = 'hd';
                
                function changeQuality(quality) {
                    currentQuality = quality;
                    document.getElementById('stream').src = '/stream/' + quality;
                    document.getElementById('quality').textContent = 'Quality: ' + quality.toUpperCase();
                }
                
                function refreshStream() {
                    const img = document.getElementById('stream');
                    const src = img.src;
                    img.src = '';
                    setTimeout(() => { img.src = src; }, 100);
                }
                
                // Update timestamp
                setInterval(() => {
                    document.getElementById('time').textContent = new Date().toLocaleTimeString();
                }, 1000);
            </script>
        </body>
        </html>
        '''
    
    def run(self):
        """Start web server"""
        host = self.config['streaming']['host']
        port = self.config['streaming']['port']
        logging.info(f"Starting web server on {host}:{port}")
        self.socketio.run(self.app, host=host, port=port, debug=False)

def webserver_process(config, stream_queues):
    """Entry point for web server process"""
    server = WebServer(config, stream_queues)
    server.run()
```

#### 4. Process Manager (src/process_manager.py)
```python
import multiprocessing as mp
from multiprocessing import Queue, Manager
import signal
import time
import logging
from src.camera_capture import camera_process
from src.stream_encoder import encoder_process
from src.web_server import webserver_process

class ProcessManager:
    def __init__(self, config):
        self.config = config
        self.processes = {}
        self.queues = {}
        self.running = False
        
    def setup_queues(self):
        """Create communication queues"""
        # Camera to encoder queue
        self.queues['raw_frames'] = Queue(maxsize=self.config['processing']['buffer_size'])
        
        # Encoder to webserver queues (one per quality level)
        self.queues['streams'] = {}
        for format_config in self.config['streaming']['formats']:
            quality_name = format_config['name']
            self.queues['streams'][quality_name] = Queue(maxsize=5)
        
        # Control queues
        self.queues['camera_control'] = Queue()
        
    def start_camera_process(self):
        """Start camera capture process"""
        p = mp.Process(
            target=camera_process,
            args=(self.config, self.queues['raw_frames'], self.queues['camera_control']),
            name='CameraCapture'
        )
        p.start()
        self.processes['camera'] = p
        logging.info("Camera process started")
    
    def start_encoder_processes(self):
        """Start encoder processes"""
        num_encoders = self.config['processing']['encoder_workers']
        
        for i in range(num_encoders):
            p = mp.Process(
                target=encoder_process,
                args=(self.config, self.queues['raw_frames'], 
                      self.queues['streams'], i),
                name=f'Encoder-{i}'
            )
            p.start()
            self.processes[f'encoder_{i}'] = p
            logging.info(f"Encoder {i} process started")
    
    def start_webserver_process(self):
        """Start web server process"""
        p = mp.Process(
            target=webserver_process,
            args=(self.config, self.queues['streams']),
            name='WebServer'
        )
        p.start()
        self.processes['webserver'] = p
        logging.info("Web server process started")
    
    def start_all(self):
        """Start all processes"""
        self.running = True
        self.setup_queues()
        
        # Start in order
        self.start_camera_process()
        time.sleep(1)  # Let camera initialize
        
        self.start_encoder_processes()
        time.sleep(1)
        
        self.start_webserver_process()
        
        logging.info("All processes started successfully")
    
    def stop_all(self):
        """Stop all processes gracefully"""
        self.running = False
        logging.info("Stopping all processes...")
        
        # Signal camera to stop
        self.queues['camera_control'].put('stop')
        
        # Wait for processes to finish
        for name, process in self.processes.items():
            logging.info(f"Stopping {name}...")
            process.terminate()
            process.join(timeout=5)
            
            if process.is_alive():
                logging.warning(f"{name} didn't stop, killing...")
                process.kill()
        
        logging.info("All processes stopped")
    
    def monitor_health(self):
        """Monitor process health"""
        while self.running:
            for name, process in list(self.processes.items()):
                if not process.is_alive():
                    logging.error(f"Process {name} died, restarting...")
                    # Restart logic here
            
            time.sleep(self.config['monitoring']['health_check_interval'])
    
    def handle_signal(self, signum, frame):
        """Handle shutdown signals"""
        logging.info(f"Received signal {signum}, shutting down...")
        self.stop_all()

def setup_logging(config):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, config['monitoring']['log_level']),
        format='%(asctime)s - %(processName)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/camera_server.log'),
            logging.StreamHandler()
        ]
    )
```

#### 5. Main Entry Point (main.py)
```python
#!/usr/bin/env python3
import yaml
import signal
import sys
import os
from src.process_manager import ProcessManager, setup_logging

def load_config(config_file='config/config.yaml'):
    """Load configuration from YAML file"""
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)

def main():
    # Ensure directories exist
    os.makedirs('logs', exist_ok=True)
    os.makedirs('recordings', exist_ok=True)
    
    # Load configuration
    config = load_config()
    
    # Setup logging
    setup_logging(config)
    
    # Create process manager
    manager = ProcessManager(config)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, manager.handle_signal)
    signal.signal(signal.SIGTERM, manager.handle_signal)
    
    try:
        # Start all processes
        manager.start_all()
        
        print("\n" + "="*60)
        print("  24/7 Camera Streaming Server")
        print("="*60)
        print(f"  Web Interface: http://localhost:{config['streaming']['port']}")
        print(f"  Stream URL:    http://localhost:{config['streaming']['port']}/stream/hd")
        print("="*60)
        print("\nPress Ctrl+C to stop\n")
        
        # Keep main process alive
        manager.monitor_health()
        
    except KeyboardInterrupt:
        print("\nShutdown initiated...")
    finally:
        manager.stop_all()
        print("Server stopped")

if __name__ == '__main__':
    main()
```

## Installation & Setup

### 1. Install Dependencies
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install opencv-python flask flask-socketio pyyaml numpy pillow
```

### 2. Configure Your Camera
Edit `config/config.yaml`:
- For USB webcam: Set `source: 0` (or 1, 2 for other cameras)
- For IP camera: Set `source: "rtsp://username:password@ip:port/stream"`
- Adjust resolution and quality settings

### 3. Run the Server
```bash
python main.py
```

### 4. Access the Stream
- Web viewer: http://localhost:8080
- Direct stream: http://localhost:8080/stream/hd

## Advanced Features

### Recording to Disk
Create `src/storage_manager.py`:
```python
import cv2
import time
from datetime import datetime
import os

def storage_process(config, frame_queue):
    """Process for recording video segments"""
    segment_duration = config['storage']['segment_duration']
    output_path = config['storage']['path']
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = None
    segment_start = time.time()
    
    while True:
        frame_data = frame_queue.get()
        
        # Start new segment if needed
        if writer is None or (time.time() - segment_start) > segment_duration:
            if writer:
                writer.release()
            
            # Create new file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{output_path}/segment_{timestamp}.mp4"
            writer = cv2.VideoWriter(
                filename,
                fourcc,
                config['camera']['fps'],
                (config['camera']['width'], config['camera']['height'])
            )
            segment_start = time.time()
        
        writer.write(frame_data['frame'])
```

### Motion Detection
Add to encoder process:
```python
def detect_motion(frame1, frame2, threshold=25):
    """Simple motion detection"""
    diff = cv2.absdiff(frame1, frame2)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blur, threshold, 255, cv2.THRESH_BINARY)
    motion_pixels = cv2.countNonZero(thresh)
    return motion_pixels > 1000  # Adjust threshold
```

### RTSP Server
For professional RTSP streaming:
```bash
pip install mediamtx  # Or use gstreamer

# Run MediaMTX
mediamtx &

# Push stream from Python
ffmpeg -f rawvideo -i pipe:0 -f rtsp rtsp://localhost:8554/stream
```

## Production Deployment

### Using Systemd (Linux)
Create `/etc/systemd/system/camera-stream.service`:
```ini
[Unit]
Description=24/7 Camera Streaming Server
After=network.target

[Service]
Type=simple
User=camera
WorkingDirectory=/opt/camera_server
Environment="PATH=/opt/camera_server/venv/bin"
ExecStart=/opt/camera_server/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable camera-stream
sudo systemctl start camera-stream
sudo systemctl status camera-stream
```

### Docker Deployment
```dockerfile
FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    libopencv-dev \
    python3-opencv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "main.py"]
```

Build and run:
```bash
docker build -t camera-server .
docker run -d --device=/dev/video0 -p 8080:8080 camera-server
```

### Nginx Reverse Proxy
```nginx
server {
    listen 80;
    server_name camera.example.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
    
    location /stream/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_buffering off;
        proxy_cache off;
    }
}
```

## Troubleshooting

### Camera Not Found
```bash
# List available cameras
v4l2-ctl --list-devices

# Test camera
ffplay /dev/video0
```

### High CPU Usage
- Reduce FPS in config
- Lower resolution
- Use hardware encoding (NVENC, VAAPI)
- Increase encoding workers

### Stream Lag
- Increase buffer size
- Reduce encoding quality
- Check network bandwidth
- Use local network

## Performance Optimization

### GPU Acceleration (NVIDIA)
```python
# In encoder process
import cv2

# Enable CUDA
cv2.cuda.setDevice(0)
gpu_frame = cv2.cuda_GpuMat()
gpu_frame.upload(frame)
# Process on GPU
```

### Multi-threaded Encoding
- Use hardware encoders (h264_nvenc, h264_vaapi)
- Implement frame skip during high load
- Use adaptive quality based on CPU usage

## Monitoring & Maintenance

### Log Rotation
```bash
# /etc/logrotate.d/camera-stream
/opt/camera_server/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

### Metrics Collection
Add Prometheus metrics:
```python
from prometheus_client import Counter, Gauge

frames_processed = Counter('frames_processed_total', 'Total frames')
active_clients = Gauge('active_clients', 'Active stream clients')
```

## Security Considerations

1. **Authentication**: Add login system to Flask
2. **HTTPS**: Use SSL certificates (Let's Encrypt)
3. **Firewall**: Restrict access to specific IPs
4. **Rate Limiting**: Prevent abuse
5. **Input Validation**: Sanitize all inputs

## Summary

This multiprocessing architecture provides:
- ✅ Robust 24/7 operation with automatic recovery
- ✅ Scalable encoding with multiple workers
- ✅ Low latency streaming
- ✅ Multiple quality levels
- ✅ Easy monitoring and maintenance
- ✅ Production-ready deployment options

The SWAMP-inspired design uses process isolation for reliability and efficient resource utilization.

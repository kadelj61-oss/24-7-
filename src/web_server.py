from flask import Flask, Response, send_from_directory
import os

class WebServer:
    def __init__(self, config, stream_queues):
        self.config = config
        self.stream_queues = stream_queues
        
        # Set up Flask with static folder
        self.app = Flask(__name__, 
                        static_folder='../static',
                        static_url_path='/static')
        
        self.setup_routes()
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        # Serve index.html as homepage
        @self.app.route('/')
        def index():
            return send_from_directory('../static', 'index.html')
        
        # Serve other static files
        @self.app.route('/static/<path:filename>')
        def static_files(filename):
            return send_from_directory('../static', filename)
        
        # MJPEG stream endpoints
        @self.app.route('/stream/<quality>')
        def stream(quality):
            """MJPEG stream endpoint"""
            return Response(
                self.generate_stream(quality),
                mimetype='multipart/x-mixed-replace; boundary=frame'
            )
        
        # Health check endpoint
        @self.app.route('/health')
        def health():
            return {
                'status': 'ok', 
                'timestamp': time.time(),
                'uptime': time.time() - self.start_time
            }
        
        # API endpoints
        @self.app.route('/api/stats')
        def stats():
            return {
                'fps': 30,
                'bitrate': 4.5,
                'resolution': '1920x1080',
                'viewers': len(self.active_clients)
            }
    
    def generate_stream(self, quality='hd'):
        """Generator for MJPEG stream"""
        if quality not in self.stream_queues:
            quality = 'hd'
        
        queue = self.stream_queues[quality]
        
        while True:
            try:
                frame_data = queue.get(timeout=1.0)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + 
                       frame_data['data'] + b'\r\n')
            except:
                continue
    
    def run(self):
        """Start web server"""
        host = self.config['streaming']['host']
        port = self.config['streaming']['port']
        self.start_time = time.time()
        self.active_clients = set()
        
        logging.info(f"Starting web server on {host}:{port}")
        self.app.run(host=host, port=port, debug=False, threaded=True)

def webserver_process(config, stream_queues):
    """Entry point for web server process"""
    server = WebServer(config, stream_queues)
    server.run()

from flask import Flask, Response, send_from_directory, request, jsonify
from flask_cors import CORS
import time
import logging
import signal
import os
import datetime
from google.cloud import storage
from werkzeug.utils import secure_filename


class WebServer:
    # Allowed file types for uploads
    ALLOWED_MIME_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'video/mp4', 'video/webm']
    
    def __init__(self, config, stream_queues):
        self.config = config
        self.stream_queues = stream_queues
        self.start_time = time.time()
        self.active_clients = set()
        
        # Configure Google Cloud Storage
        self.gcs_bucket_name = os.environ.get('GCS_BUCKET_NAME')
        self.gcs_project_id = os.environ.get('GCS_PROJECT_ID')
        
        # Initialize GCS client if configured
        self.storage_client = None
        if self.gcs_bucket_name and self.gcs_project_id:
            try:
                self.storage_client = storage.Client(project=self.gcs_project_id)
            except Exception as e:
                logging.warning(f"Failed to initialize GCS client: {e}")

        # Set up Flask with static folder
        self.app = Flask(__name__,
                         static_folder='../static',
                         static_url_path='/static')

        # Enable CORS for GitHub Pages and localhost
        CORS(self.app, resources={
            r"/*": {
                "origins": [
                    "https://kadelj61-oss.github.io",
                    r"http://localhost:\d+",
                    r"https://.*\.ngrok\.io",
                    r"https://.*\.ngrok-free\.app"
                ],
                "methods": ["GET", "POST", "OPTIONS"],
                "allow_headers": ["Content-Type"]
            }
        })

        self.setup_routes()

    def _get_timestamp_ms(self):
        """Get current UTC timestamp in milliseconds"""
        return int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)

    def upload_to_gcs(self, file_content, filename, content_type):
        """Upload file to Google Cloud Storage"""
        try:
            if not self.storage_client:
                raise Exception("GCS client not initialized")
            
            bucket = self.storage_client.bucket(self.gcs_bucket_name)
            
            # Create blob with timestamp
            timestamp = self._get_timestamp_ms()
            blob_name = f"recordings/{timestamp}-{filename}"
            blob = bucket.blob(blob_name)
            
            # Upload
            blob.upload_from_string(file_content, content_type=content_type)
            
            # Make public
            blob.make_public()
            
            return {
                'filename': blob_name,
                'url': blob.public_url,
                'size': len(file_content),
                'mimetype': content_type
            }
        except Exception as e:
            raise Exception(f"GCS upload failed: {str(e)}")

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

        # Recordings upload endpoint
        @self.app.route('/recordings', methods=['POST'])
        def upload_recording():
            """Handle photo/video uploads"""
            try:
                if 'recording' not in request.files:
                    return jsonify({'success': False, 'error': 'No file uploaded'}), 400
                
                file = request.files['recording']
                
                if file.filename == '':
                    return jsonify({'success': False, 'error': 'No file selected'}), 400
                
                # Validate file type
                if file.content_type not in self.ALLOWED_MIME_TYPES:
                    return jsonify({
                        'success': False, 
                        'error': f'Invalid file type: {file.content_type}. Allowed: {", ".join(self.ALLOWED_MIME_TYPES)}'
                    }), 400
                
                # Read file content
                file_content = file.read()
                
                # Upload to GCS
                if self.gcs_bucket_name and self.gcs_project_id and self.storage_client:
                    result = self.upload_to_gcs(file_content, file.filename, file.content_type)
                    timestamp = self._get_timestamp_ms()
                    return jsonify({
                        'success': True,
                        'message': 'File uploaded successfully',
                        'data': {
                            'filename': result['filename'],
                            'url': result['url'],
                            'size': result['size'],
                            'mimetype': result['mimetype'],
                            'uploadedAt': datetime.datetime.fromtimestamp(timestamp / 1000, datetime.timezone.utc).isoformat()
                        }
                    }), 201
                else:
                    # Fallback: save locally if GCS not configured
                    upload_folder = 'recordings'
                    os.makedirs(upload_folder, exist_ok=True)
                    timestamp = self._get_timestamp_ms()
                    filename = f"{timestamp}-{secure_filename(file.filename)}"
                    filepath = os.path.join(upload_folder, filename)
                    
                    with open(filepath, 'wb') as f:
                        f.write(file_content)
                    
                    return jsonify({
                        'success': True,
                        'message': 'File saved locally (GCS not configured)',
                        'data': {
                            'filename': filename,
                            'url': f'/recordings/{filename}',
                            'size': len(file_content),
                            'mimetype': file.content_type,
                            'uploadedAt': datetime.datetime.fromtimestamp(timestamp / 1000, datetime.timezone.utc).isoformat()
                        }
                    }), 201
                    
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

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
            except Exception:
                continue

    def run(self):
        """Start web server"""
        host = self.config['streaming']['host']
        port = self.config['streaming']['port']

        logging.info(f"Starting web server on {host}:{port}")
        self.app.run(
            host=host,
            port=port,
            debug=False,
            threaded=True
        )



def webserver_process(config, stream_queues):
    """Entry point for web server process"""
    # Reset signal handlers to default for child process
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    
    server = WebServer(config, stream_queues)
    server.run()

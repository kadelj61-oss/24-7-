import multiprocessing as mp
from multiprocessing import Queue
import signal
import time
import logging
import os
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
        
        # Ensure directories exist
        os.makedirs('logs', exist_ok=True)
        os.makedirs('recordings', exist_ok=True)
        
        # Setup logging
        self.setup_logging()
        
        # Setup queues
        self.setup_queues()
        
        # Setup signal handlers (only in parent process)
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)
        
        # Start in order
        self.start_camera_process()
        time.sleep(1)  # Let camera initialize
        
        self.start_encoder_processes()
        time.sleep(1)
        
        self.start_webserver_process()
        
        logging.info("All processes started successfully")
        
        # Print startup info
        print("\n" + "="*60)
        print("  24/7 Camera Streaming Server")
        print("="*60)
        print(f"  Web Interface: http://localhost:{self.config['streaming']['port']}")
        print(f"  Stream URL:    http://localhost:{self.config['streaming']['port']}/stream/hd")
        print("="*60)
        print("\nPress Ctrl+C to stop\n")
    
    def stop_all(self):
        """Stop all processes gracefully"""
        self.running = False
        logging.info("Stopping all processes...")
        
        # Signal camera to stop
        try:
            self.queues['camera_control'].put('stop')
        except:
            pass
        
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
        health_check_interval = self.config.get('monitoring', {}).get('health_check_interval', 5)
        
        while self.running:
            for name, process in list(self.processes.items()):
                if not process.is_alive():
                    logging.error(f"Process {name} died unexpectedly")
                    # Could implement restart logic here
            
            time.sleep(health_check_interval)
    
    def handle_signal(self, signum, frame):
        """Handle shutdown signals"""
        logging.info(f"Received signal {signum}, shutting down...")
        self.stop_all()
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_format = self.config.get('logging', {}).get('format', 
                                                        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        log_level = self.config.get('logging', {}).get('level', 'INFO')
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format,
            handlers=[
                logging.FileHandler('logs/camera_server.log'),
                logging.StreamHandler()
            ]
        )

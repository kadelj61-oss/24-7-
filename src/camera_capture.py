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
                width, height = self.config['camera']['resolution']
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                self.camera.set(cv2.CAP_PROP_FPS, self.config['camera']['fps'])
                
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

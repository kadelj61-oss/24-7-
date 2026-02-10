import cv2
import time
import multiprocessing as mp
from queue import Empty, Full
import logging
import signal


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
                        except Full:
                            # Queue full, skip frame (backpressure handling)
                            pass
                        except Exception as e:
                            logging.error(f"Encoder {self.encoder_id}: Error putting frame to {quality_name} queue: {e}")
                
            except Empty:
                continue
            except Exception as e:
                logging.error(f"Encoder {self.encoder_id} error: {e}")
        
        logging.info(f"Encoder {self.encoder_id} stopped")


def encoder_process(config, input_queue, output_queues, encoder_id):
    """Entry point for encoder process"""
    # Reset signal handlers to default for child process
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    
    encoder = StreamEncoder(config, input_queue, output_queues, encoder_id)
    encoder.run()

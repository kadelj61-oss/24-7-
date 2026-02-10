import logging
import yaml
import sys
from src.process_manager import ProcessManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Main entry point for the camera streaming server"""
    try:
        # Load configuration
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Start the process manager
        manager = ProcessManager(config)
        manager.start_all()
        
        # Keep running until interrupted
        while True:
            pass
            
    except KeyboardInterrupt:
        logging.info("Shutting down...")
        if 'manager' in locals():
            manager.stop_all()
        sys.exit(0)
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

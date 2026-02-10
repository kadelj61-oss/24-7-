#!/usr/bin/env python3
import logging
import yaml
import sys
import signal
from src.process_manager import ProcessManager


def main():
    """Main entry point for the camera streaming server"""
    try:
        # Load configuration
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Create process manager
        manager = ProcessManager(config)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, manager.handle_signal)
        signal.signal(signal.SIGTERM, manager.handle_signal)
        
        # Start all processes
        manager.start_all()
        
        # Keep main process alive and monitor health
        manager.monitor_health()
            
    except KeyboardInterrupt:
        print("\nShutdown initiated...")
        if 'manager' in locals():
            manager.stop_all()
        sys.exit(0)
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

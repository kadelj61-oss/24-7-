#!/usr/bin/env python3
import logging
import yaml
import sys
import os
from src.process_manager import ProcessManager


def main():
    """Main entry point for the camera streaming server"""
    try:
        # Load configuration
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        # Override port with Railway environment variable if set
        port = int(os.getenv('PORT', config['streaming']['port']))
        config['streaming']['port'] = port
        
        # Setup logging before creating manager
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logging.info(f"Using port: {port}")

        # Create process manager
        manager = ProcessManager(config)

        # Start all processes (signal handlers set up inside)
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
        if 'manager' in locals():
            manager.stop_all()
        sys.exit(1)


if __name__ == "__main__":
    main()

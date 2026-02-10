"""
24/7 Camera Streaming Server

A robust, production-ready 24/7 live camera streaming server built with Python multiprocessing.
Stream from USB webcams or IP cameras with automatic recovery, multiple quality levels, and optional recording.
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__license__ = "MIT"

from .web_server import WebServer, webserver_process

__all__ = ["WebServer", "webserver_process"]

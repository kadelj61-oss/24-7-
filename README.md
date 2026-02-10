# 24/7 Camera Streaming Server

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-production-brightgreen)

A robust, production-ready 24/7 live camera streaming server built with Python multiprocessing. Stream from USB webcams or IP cameras with automatic recovery, multiple quality levels, and optional recording.

## Features

- 🎥 **Multi-camera support** - USB webcams, IP cameras, RTSP streams
- 🔄 **Auto-recovery** - Automatic reconnection and process restart
- 📊 **Multiple qualities** - Serve HD, SD, and custom resolutions simultaneously
- 💾 **Optional recording** - Save video segments to disk
- 🌐 **Web interface** - Browser-based viewer with quality selection
- ⚡ **High performance** - Multiprocessing architecture for efficiency
- 🐳 **Docker ready** - Easy deployment with Docker/Docker Compose
- 📈 **Monitoring** - Health checks and logging built-in

## Quick Start

### Installation
```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/camera-streaming-server.git
cd camera-streaming-server

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Edit `config/config.yaml` to set your camera source:
```yaml
camera:
  source: 0  # 0 for USB webcam, or "rtsp://..." for IP camera
  width: 1920
  height: 1080
  fps: 30
```

### Run
```bash
python main.py
```

Access the stream at: **http://localhost:8080**

## Architecture

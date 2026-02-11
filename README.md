# 24/7 Live Camera Stream

A Raspberry Pi USB camera streaming application that streams video to a static GitHub Pages website via ngrok tunnel.

## Features

### 🎥 Raspberry Pi Camera Streaming
- USB camera support via OpenCV
- MJPEG streaming with quality control (SD/HD/UHD)
- Real-time stats from server
- ngrok tunnel support for remote access
- Auto-reconnect when connection drops
- Persistent connection settings

### 🌐 GitHub Pages Deployment

Live at: `https://kadelj61-oss.github.io/24-7-/`

The website connects to your Raspberry Pi backend via ngrok, allowing you to stream your USB camera from anywhere.

## Architecture

```
┌─────────────────┐         ┌──────────────┐         ┌─────────────────┐
│  Raspberry Pi   │ ◄─────► │    ngrok     │ ◄─────► │  GitHub Pages   │
│  + USB Camera   │         │   Tunnel     │         │    Website      │
│  + Python Flask │         └──────────────┘         └─────────────────┘
└─────────────────┘
```

## Quick Start

### Hardware Requirements
- Raspberry Pi (3B+ or newer recommended)
- USB Camera
- Internet connection
- Power supply

### Software Setup

1. **Clone Repository on Raspberry Pi:**
   ```bash
   git clone https://github.com/kadelj61-oss/24-7-.git
   cd 24-7-
   ```

2. **Install System Dependencies:**
   ```bash
   sudo apt-get update
   sudo apt-get install python3-pip python3-opencv
   ```

3. **Install Python Dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

4. **Install ngrok:**
   ```bash
   # For ARM (Raspberry Pi)
   wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm.tgz
   tar -xvzf ngrok-v3-stable-linux-arm.tgz
   sudo mv ngrok /usr/local/bin/
   
   # Sign up at https://ngrok.com and get your authtoken
   ngrok config add-authtoken YOUR_AUTHTOKEN
   ```

5. **Connect USB Camera:**
   - Plug USB camera into Raspberry Pi
   - Verify camera is detected:
     ```bash
     ls /dev/video*
     # Should show /dev/video0 or similar
     ```

6. **Start the Backend Server:**
   ```bash
   python3 main.py
   ```
   The server will start on `http://localhost:8080`

7. **Start ngrok Tunnel (in another terminal):**
   ```bash
   ngrok http 8080
   ```
   Copy the ngrok URL (e.g., `https://abc123.ngrok.io`)

8. **Connect from GitHub Pages:**
   - Visit `https://kadelj61-oss.github.io/24-7-/`
   - Paste your ngrok URL in the "Backend URL" field
   - Click "Connect"
   - ✅ Your camera stream is now live!

## Configuration

### Camera Settings
Edit `config/config.yaml` to configure camera settings:
- Resolution
- Frame rate
- Quality presets (SD/HD/UHD)
- Buffer size

### CORS Configuration
The backend is pre-configured to accept connections from:
- `https://kadelj61-oss.github.io` (GitHub Pages)
- `http://localhost:*` (local testing)
- `https://*.ngrok.io` (ngrok tunnels)
- `https://*.ngrok-free.app` (ngrok free tier)

## Features in Detail

### Quality Control
- **SD**: 1280x720 @ 30fps (lower bandwidth)
- **HD**: 1920x1080 @ 30fps (default)
- **UHD**: 3840x2160 @ 30fps (if camera supports)

Quality can be changed on-the-fly from the website.

### Connection Status
- 🟢 **Green**: Connected and streaming
- 🟡 **Yellow**: Connecting/Reconnecting
- 🔴 **Red**: Connection failed
- ⚪ **Gray**: Not configured

### Auto-Reconnect
- Automatically reconnects if connection drops
- Exponential backoff (max 5 attempts)
- Health checks every 5 seconds

### Stats Display
Real-time statistics from `/api/stats`:
- Status (Online/Offline)
- Resolution
- FPS (Frames Per Second)
- Bitrate
- Viewers (concurrent connections)

## Development

### Project Structure

```
24-7-/
├── index.html              # Main GitHub Pages entry point
├── static/
│   └── index.html         # Same as root (served by Flask)
├── src/
│   ├── web_server.py      # Flask backend with CORS
│   ├── process_manager.py # Process management
│   └── ...
├── config/
│   └── config.yaml        # Configuration file
├── main.py                # Backend entry point
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

### Local Testing

1. **Test Backend:**
   ```bash
   # Start backend
   python main.py
   
   # In another terminal, test endpoints
   curl http://localhost:8080/health
   curl http://localhost:8080/api/stats
   ```

2. **Test Website Locally:**
   - Open `index.html` in a browser
   - Use `http://localhost:8080` as backend URL
   - Click "Connect"

## Troubleshooting

### Camera Not Detected
```bash
# List video devices
ls /dev/video*

# Check camera with v4l2
v4l2-ctl --list-devices

# Test camera
ffplay /dev/video0
```

### Backend Connection Failed
- Verify backend is running: `curl http://localhost:8080/health`
- Check ngrok tunnel is active: `ngrok http 8080`
- Ensure CORS is configured (flask-cors installed)
- Check browser console for error messages
- Verify firewall isn't blocking port 8080

### Stream Not Loading
- Verify camera is connected and accessible
- Check backend logs for errors
- Try different quality settings
- Ensure adequate bandwidth
- Check if camera supports selected resolution

### CORS Errors
- Ensure `flask-cors` is installed: `pip3 install flask-cors`
- Verify ngrok URL is accessible from browser
- Check browser console for specific CORS errors
- Make sure backend is running with CORS enabled

### ngrok Connection Issues
- Verify ngrok is installed and authenticated
- Check ngrok status: `curl http://localhost:4040/api/tunnels`
- Ensure port 8080 is not already in use
- Try restarting ngrok

## Performance Tips

### Raspberry Pi Optimization
- Use Raspberry Pi 4 for better performance
- Ensure adequate cooling (heatsinks/fan)
- Use quality power supply (5V 3A minimum)
- Close unnecessary applications
- Consider overclocking for 4K streaming

### Network Optimization
- Use wired Ethernet instead of WiFi when possible
- Ensure good upload bandwidth (5+ Mbps for HD)
- Position Pi close to router
- Use QoS settings on router if available

### Camera Tips
- Start with SD quality, upgrade if performance is good
- Ensure good lighting for better image quality
- Use USB 3.0 camera for higher resolutions
- Position camera on stable mount to reduce motion blur

## Running as a Service

To run the backend automatically on boot:

1. **Create systemd service:**
   ```bash
   sudo nano /etc/systemd/system/camera-stream.service
   ```

2. **Add configuration:**
   ```ini
   [Unit]
   Description=24/7 Camera Streaming Service
   After=network.target

   [Service]
   Type=simple
   User=pi
   WorkingDirectory=/home/pi/24-7-
   ExecStart=/usr/bin/python3 /home/pi/24-7-/main.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

3. **Enable and start:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable camera-stream.service
   sudo systemctl start camera-stream.service
   
   # Check status
   sudo systemctl status camera-stream.service
   ```

## Security Notes

- Never commit ngrok URLs or authentication tokens
- Backend URLs are stored in browser localStorage only
- Consider adding authentication to backend for production
- Use HTTPS (ngrok provides this automatically)
- Regularly update dependencies for security patches
- Monitor ngrok dashboard for usage

## Browser Compatibility

- ✅ Chrome/Edge (recommended)
- ✅ Firefox
- ✅ Safari (iOS/macOS)
- ✅ All modern browsers with MJPEG support

## Future Enhancements

- [ ] Recording functionality
- [ ] Snapshot capture to storage
- [ ] Multiple camera support
- [ ] Mobile-optimized UI
- [ ] Stream authentication
- [ ] Motion detection alerts
- [ ] Cloud storage integration

## License

All rights reserved © 2026

## Support

For issues or questions:
- Open an issue on GitHub
- Check troubleshooting section above
- Review browser console and backend logs for errors
- Join the discussions on GitHub

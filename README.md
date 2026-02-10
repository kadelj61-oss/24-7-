# 24/7 Live Camera Stream

A dual-mode camera streaming application that works both as a static GitHub Pages site (using WebRTC for browser camera access) and with a Python backend for USB camera streaming via ngrok.

## Features

### 🎥 Dual Streaming Modes

#### 1. Browser Camera Mode (WebRTC)
- Direct browser camera access using WebRTC
- No backend required - works immediately on GitHub Pages
- Real-time FPS calculation
- Quality selection (HD/SD/UHD)
- Works on any device with a camera

#### 2. Backend Server Mode
- Connect to Python Flask backend running locally
- Support for USB cameras via OpenCV
- ngrok tunnel support for remote access
- MJPEG streaming with quality control
- Real-time stats from server

### 🌐 GitHub Pages Deployment

Live at: `https://kadelj61-oss.github.io/24-7-/`

The site is automatically deployed to GitHub Pages using GitHub Actions. The dual-mode design allows the site to work immediately with browser cameras, while also supporting backend connections via ngrok.

## Quick Start

### Scenario A: Browser Camera (No Setup Required)

1. Visit `https://kadelj61-oss.github.io/24-7-/`
2. Click "Browser Camera" mode (default)
3. Allow camera permissions when prompted
4. ✅ Live stream starts immediately

### Scenario B: Backend Server with ngrok

1. **Clone and Setup Repository:**
   ```bash
   git clone https://github.com/kadelj61-oss/24-7-.git
   cd 24-7-
   pip install -r requirements.txt
   ```

2. **Start Python Backend:**
   ```bash
   python main.py
   ```
   The server will start on `http://localhost:8080`

3. **Setup ngrok Tunnel:**
   ```bash
   # Install ngrok: https://ngrok.com/download
   ngrok http 8080
   ```
   Copy the ngrok URL (e.g., `https://abc123.ngrok.io`)

4. **Connect from GitHub Pages:**
   - Visit `https://kadelj61-oss.github.io/24-7-/`
   - Click "Backend Server" mode
   - Paste your ngrok URL
   - Click "Connect"
   - ✅ Stream from your USB camera!

## Backend CORS Configuration

For the backend to work with GitHub Pages, you need to enable CORS. The Python backend should include:

```python
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": [
            "https://kadelj61-oss.github.io",
            "http://localhost:*",
            "https://*.ngrok.io"
        ]
    }
})
```

Install flask-cors:
```bash
pip install flask-cors
```

## Features in Detail

### Mode Switching
- Toggle between "Browser Camera" and "Backend Server" modes
- Settings persist in localStorage
- Automatic fallback handling

### Quality Control
- **HD**: 1920x1080 @ 30fps
- **SD**: 1280x720 @ 30fps  
- **UHD**: 3840x2160 @ 30fps (if supported)

Quality settings apply to both WebRTC and backend modes.

### Connection Status
- 🟢 **Green**: Connected and streaming
- 🟡 **Yellow**: Connecting...
- 🔴 **Red**: Connection failed
- ⚪ **Gray**: Not configured

### Stats Display
- **WebRTC Mode**: Resolution, FPS (calculated), Status
- **Backend Mode**: Resolution, FPS, Bitrate, Viewers (from `/api/stats`)

## Development

### Local Testing

1. **Test WebRTC Mode:**
   - Open `index.html` in a browser
   - Use browser camera mode
   - Test camera permissions and quality settings

2. **Test Backend Mode:**
   - Start Python backend: `python main.py`
   - Open `index.html` in browser
   - Switch to backend mode
   - Use `http://localhost:8080` as backend URL

### Project Structure

```
24-7-/
├── index.html              # Main GitHub Pages entry point
├── static/
│   └── index.html         # Same as root (served by Flask)
├── src/
│   └── web_server.py      # Flask backend
├── main.py                # Backend entry point
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Troubleshooting

### Camera Permission Denied
- Check browser permissions in settings
- Ensure site is using HTTPS (required for WebRTC)
- Click "Retry" button after granting permissions

### Backend Connection Failed
- Verify backend is running: `curl http://localhost:8080/health`
- Check ngrok tunnel is active
- Ensure CORS is configured correctly
- Check browser console for error messages
- Verify firewall isn't blocking connections

### Stream Not Loading
- **WebRTC**: Check camera permissions and browser compatibility
- **Backend**: Verify camera is connected and accessible
- Try switching quality settings
- Refresh the page

### CORS Errors
When connecting to backend from GitHub Pages:
- Install `flask-cors`: `pip install flask-cors`
- Add CORS configuration to Flask app
- Ensure ngrok URL is accessible
- Check browser console for specific CORS errors

## Browser Compatibility

### WebRTC Mode
- ✅ Chrome/Edge (recommended)
- ✅ Firefox
- ✅ Safari (iOS/macOS)
- ⚠️ Requires HTTPS (GitHub Pages provides this)

### Backend Mode
- ✅ All modern browsers
- Requires backend with CORS enabled

## GitHub Actions

The repository includes two workflows:

1. **`static.yml`**: Deploys to GitHub Pages
2. **`ci.yml`**: Builds Docker image

## Security Notes

- Never commit ngrok URLs or authentication tokens
- Backend URLs are stored in browser localStorage only
- Camera permissions required for WebRTC mode
- Backend should validate all inputs

## Future Enhancements

- [ ] Recording functionality
- [ ] Snapshot capture
- [ ] Multiple camera support
- [ ] Mobile-optimized UI
- [ ] Stream authentication
- [ ] P2P WebRTC mode

## License

All rights reserved © 2026

## Support

For issues or questions:
- Open an issue on GitHub
- Check troubleshooting section above
- Review browser console for errors

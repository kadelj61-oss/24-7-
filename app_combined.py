import os
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=[
    "https://kadelj61-oss.github.io",
    "https://*.up.railway.app"
])

@app.route('/health')
def health():
    return 'OK', 200

@app.route('/api/stats')
def api_stats():
    return jsonify({
        "status": "online",
        "resolution": "1920x1080",
        "fps": 30,
        "bitrate": "3Mbps",
        "viewers": 1
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))   # Railway sets PORT env var!
    app.run(host='0.0.0.0', port=port)

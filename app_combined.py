from flask import Flask, jsonify, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=[
    "https://kadelj61-oss.github.io",
    "https://*.ngrok-free.dev"
])

@app.route('/')
def home():
    return '<h1>Backend is running!</h1>'

@app.route('/health')
def health():
    return 'OK', 200

@app.route('/api/stats')
def api_stats():
    # Demo values
    return jsonify({
        "status": "online",
        "resolution": "1920x1080",
        "fps": 30,
        "bitrate": "3Mbps",
        "viewers": 1
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

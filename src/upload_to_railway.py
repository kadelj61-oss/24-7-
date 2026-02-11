import cv2
import requests
import time

RAILWAY_URL = "https://24-7-production-5c2d.up.railway.app"
QUALITY = "hd"

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

print(f"Uploading to {RAILWAY_URL}/upload/{QUALITY}")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to capture frame")
        time.sleep(1)
        continue
    
    # Encode frame as JPEG
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    
    # Upload to Railway
    try:
        response = requests.post(
            f"{RAILWAY_URL}/upload/{QUALITY}",
            data=buffer.tobytes(),
            headers={'Content-Type': 'image/jpeg'},
            timeout=2
        )
        print(f"Uploaded: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"Upload error: {e}")
    
    time.sleep(0.033)  # ~30fps

cap.release()

import cv2
import requests
from ultralytics import YOLO

# Load trained model
model = YOLO("model/best.pt")

# Replace with your mobile IP
mobile_camera_url = "http://192.0.0.4:8080/video"

def check_camera_url(url, timeout=2):
    try:
        response = requests.get(url, stream=True, timeout=timeout)
        return response.status_code == 200
    except requests.RequestException:
        return False

# Open mobile camera
if check_camera_url(mobile_camera_url):
    cap = cv2.VideoCapture(mobile_camera_url)
else:
    print("❌ Cannot connect to mobile camera. Falling back to webcam 0.")
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("❌ Cannot connect to any camera")
    exit()

print("📱 Camera connected")
while True:
    ret, frame = cap.read()

    if not ret:
        break

    # Run detection
    results = model(frame, conf=0.6)

    annotated_frame = results[0].plot()

    # Show video
    cv2.imshow("Mobile Camera Detection", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
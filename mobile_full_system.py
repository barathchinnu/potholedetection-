import cv2
import folium
import webbrowser

from ultralytics import YOLO

from real_gps import get_real_location
from alert import send_alert

# ================= SETTINGS =================

mobile_ip = "192.0.0.4"

video_url = f"http://{mobile_ip}:8080/video"

# Load model
model = YOLO("model/best.pt")

# ================= MAP FUNCTION =================

def show_live_map(lat, lon):

    m = folium.Map(location=[lat, lon], zoom_start=18)

    folium.Marker(
        [lat, lon],
        popup="Pothole Detected",
        icon=folium.Icon(color="red")
    ).add_to(m)

    file_name = "live_pothole_map.html"

    m.save(file_name)

    print("🗺 Map saved:", file_name)

    webbrowser.open(file_name)


# ================= CAMERA =================
import requests

def check_camera_url(url, timeout=2):
    try:
        response = requests.get(url, stream=True, timeout=timeout)
        return response.status_code == 200
    except requests.RequestException:
        return False

if check_camera_url(video_url):
    cap = cv2.VideoCapture(video_url)
else:
    print("❌ Cannot connect to mobile camera. Falling back to webcam 0.")
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not cap.isOpened():

    print("❌ Cannot connect to any camera")

    exit()

print("📱 Camera Connected")

pothole_found = False

email_sent = False

# ================= MAIN LOOP =================

while True:

    ret, frame = cap.read()

    if not ret:
        break

    results = model(frame, conf=0.6)

    annotated_frame = results[0].plot()

    # Check pothole detection
    if len(results[0].boxes) > 0:

        if not pothole_found:

            pothole_found = True

            print("✅ Pothole Detected!")

            lat, lon = get_real_location()

            print("📍 Location:", lat, lon)

            show_live_map(lat, lon)

            if not email_sent:

                send_alert(lat, lon)

                email_sent = True

    cv2.imshow("Live Mobile Pothole Detection", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()

cv2.destroyAllWindows()

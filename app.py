import cv2
import threading
import requests
import os
from datetime import datetime

from flask import Flask, render_template, Response, jsonify, request
from ultralytics import YOLO
import psycopg2
from psycopg2.extras import RealDictCursor

from real_gps import get_real_location
from alert import send_alert
app = Flask(__name__)
DB_CONFIG = {
    "dbname": "roadwatch",
    "user": "postgres",
    "password": "barath@2007",
    "host": "127.0.0.1",
    "port": "5432"
}

def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn

    except Exception as e:
        print("⚠️ Could not connect to PostgreSQL database:", e)
        return None
    
def init_db():

    conn = get_db_connection()
    if conn:

        with conn.cursor() as cur:

            cur.execute("""
                CREATE TABLE IF NOT EXISTS detections (

                    id SERIAL PRIMARY KEY,

                    lat FLOAT,

                    lon FLOAT,

                    time TEXT,

                    image_path TEXT
                )
            """)

            conn.commit()

        conn.close()

mobile_ip = "192.0.0.4"

video_url = f"http://{mobile_ip}:8080/video"

dashboard_gps = None

try:
    model = YOLO("model/best.pt")

except Exception as e:

    print("⚠️ Could not load YOLO model:", e)

    model = None
email_sent = False

pothole_cooldown = 0
def check_camera_url(url, timeout=2):

    try:

        response = requests.get(url, stream=True, timeout=timeout)

        return response.status_code == 200

    except requests.RequestException:

        return False

def generate_frames():

    global email_sent, pothole_cooldown

    # Mobile camera
    if check_camera_url(video_url):

        cap = cv2.VideoCapture(video_url)

    else:

        print("❌ Cannot connect to mobile camera.")

        print("⚠️ Trying webcam...")

        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not cap.isOpened():

        print("❌ Cannot connect to any camera.")

        return

    frame_skip = 3
    frame_count = 0
    last_annotated_frame = None

    while True:

        success, frame = cap.read()

        if not success:
            break

        # Resize for faster processing
        frame = cv2.resize(frame, (640, 480))
        
        if last_annotated_frame is None:
            last_annotated_frame = frame
            
        frame_count += 1

        if model and frame_count % frame_skip == 0:
            results = model(frame, conf=0.45)

            last_annotated_frame = results[0].plot()
            if len(results[0].boxes) > 0:

                valid_detection = False
                for box in results[0].boxes:

                    x1, y1, x2, y2 = box.xyxy[0]

                    width = x2 - x1
                    height = y2 - y1
                    if width < 80 or height < 80:
                        continue

                    valid_detection = True
                    break


                if valid_detection and pothole_cooldown == 0:

                    print("✅ Pothole Detected!")

                    # GPS
                    lat, lon = get_real_location(mobile_ip)

                    # Fallback GPS
                    if lat is None or lon is None:

                        if dashboard_gps is not None:

                            lat, lon = dashboard_gps

                            print("📍 Using Dashboard GPS")

                        else:

                            lat, lon = (11.2748, 77.5828)

                            print("📍 Using Default GPS")

                    else:

                        print("📍 Using IP Webcam GPS")

                    print("📍 Final Location:", lat, lon)

                    # Time
                    current_time = datetime.now().strftime("%I:%M %p")

                    filename_time = datetime.now().strftime("%Y%m%d_%H%M%S")

                    # Image Name
                    image_filename = f"pothole_{filename_time}.jpg"

                    image_path = os.path.join(
                        "static",
                        "saved_images",
                        image_filename
                    )

                    # Create folder
                    os.makedirs(
                        os.path.join("static", "saved_images"),
                        exist_ok=True
                    )

                    # Save image
                    cv2.imwrite(image_path, last_annotated_frame)

                    print("🖼 Image Saved:", image_filename)

                    # ================= SAVE TO DATABASE =================

                    conn = get_db_connection()

                    if conn:

                        try:

                            with conn.cursor() as cur:

                                cur.execute(
                                    """
                                    INSERT INTO detections
                                    (lat, lon, time, image_path)

                                    VALUES (%s, %s, %s, %s)
                                    """,

                                    (
                                        float(lat),
                                        float(lon),
                                        current_time,
                                        image_filename
                                    )
                                )

                                conn.commit()

                                print("💾 Data Saved to PostgreSQL")

                        except Exception as e:

                            print("❌ Database Insert Error:", e)

                        finally:

                            conn.close()


                    if not email_sent:

                        threading.Thread(
                            target=send_alert,
                            args=(lat, lon),
                            daemon=True
                        ).start()

                        email_sent = True


                    pothole_cooldown = 100
            if pothole_cooldown > 0:

                pothole_cooldown -= 1


        ret, buffer = cv2.imencode('.jpg', last_annotated_frame)

        frame_bytes = buffer.tobytes()

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' +
            frame_bytes +
            b'\r\n'
        )


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ai-detection')
def ai_detection():
    return render_template('ai_detection.html')

@app.route('/analysis')
def analysis():
    return render_template('analysis.html')

@app.route('/authorities')
def authorities():
    return render_template('authorities.html')


@app.route('/video_feed')
def video_feed():

    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/api/detections')
def get_detections():

    conn = get_db_connection()

    if conn:

        try:

            with conn.cursor(
                cursor_factory=RealDictCursor
            ) as cur:

                cur.execute(
                    "SELECT * FROM detections ORDER BY id DESC"
                )

                records = cur.fetchall()

            return jsonify(records)

        except Exception as e:

            print("❌ Database Fetch Error:", e)

            return jsonify([])

        finally:

            conn.close()

    return jsonify([])


@app.route('/api/update_location', methods=['POST'])

def update_location():

    global dashboard_gps

    data = request.json

    if data and 'lat' in data and 'lon' in data:

        dashboard_gps = (
            float(data['lat']),
            float(data['lon'])
        )

        print(f"📡 Dashboard GPS Updated: {dashboard_gps}")

    return jsonify({"status": "success"})


if __name__ == '__main__':

    os.makedirs('templates', exist_ok=True)

    os.makedirs('static/saved_images', exist_ok=True)

    # Create DB table
    init_db()

    # Run Flask
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )
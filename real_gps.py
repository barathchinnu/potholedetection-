import requests

def get_real_location(mobile_ip="192.0.0.4"):
    """
    Attempts to get the real live location.
    1. Try grabbing from IP Webcam phone sensors.
    2. Fallback to IP-based geolocation.
    3. Last resort hardcoded location.
    """
    # Attempt 1: Fetch from IP Webcam GPS sensor endpoint
    try:
        url = f"http://{mobile_ip}:8080/sensors.json"
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            data = response.json()
            # IP Webcam format: {"gps": {"data": [[timestamp, [lat, array, etc], ...]]}}
            # Let's safely extract if available
            if 'gps' in data and 'data' in data['gps']:
                gps_entries = data['gps']['data']
                if len(gps_entries) > 0:
                    last_entry = gps_entries[-1]
                    # last_entry is typically [timestamp, [lat], [lon], ...]
                    lat = last_entry[1][0] if isinstance(last_entry[1], list) else last_entry[1]
                    lon = last_entry[2][0] if isinstance(last_entry[2], list) else last_entry[2]
                    print(f"📍 GPS obtained from mobile sensors: {lat}, {lon}")
                    return float(lat), float(lon)
    except Exception as e:
        print("⚠️ Could not fetch from mobile sensors. Returning None.")
        return None, None
        
    return None, None

if __name__ == "__main__":
    lat, lon = get_real_location()
    print("Test GPS Location:", lat, lon)
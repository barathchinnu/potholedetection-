import smtplib
def send_alert(lat, lon):

    sender_email = "barathchinnu5@gmail.com"
    receiver_email = "barathm.24cse@kongu.edu"
    password = "eekiokilvetliewq"

    subject = "Pothole Detected Alert"

    body = f"""
    ALERT!

    Pothole detected.

    Location:
    Latitude: {lat}
    Longitude: {lon}

    Google Maps:
    https://www.google.com/maps?q={lat},{lon}
    """

    message = f"Subject: {subject}\n\n{body}"

    try:

        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=30)

        server.starttls()

        server.login(sender_email, password)

        server.sendmail(sender_email, receiver_email, message)

        server.quit()

        print("📧 Email Sent!")

    except Exception as e:

        print("❌ Email Failed:", e)
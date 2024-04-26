import cv2
import cvzone
import math
import datetime
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os

from app.utils.async_api import async_api_call
from app.config import VIDEO_IMAGE_STORAGE_BASE_PATH


def send_fire_alert_email(subject, message, to_email, image_path):
    # Email setup
    from_email = "abhiparmar.vmukti@gmail.com"  # your email
    password = "xrtl mdob ukgs vmsc"  # your email password
    
    # Create email message
    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject

    # Add email body
    msg.attach(MIMEText(message, "plain"))

    # Attach image
    if image_path:
        with open(image_path, "rb") as f:
            mime = MIMEBase("image", "jpeg", filename=os.path.basename(image_path))
            mime.add_header("Content-Disposition", "attachment", filename=os.path.basename(image_path))
            mime.add_header("X-Attachment-Id", "0")
            mime.add_header("Content-ID", "<0>")
            mime.set_payload(f.read())
            encoders.encode_base64(mime)
            msg.attach(mime)

    # Send email
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:  # Change SMTP server and port if needed
        server.login(from_email, password)
        server.send_message(msg)
        server.quit()


def process_fire_detection(frame, model, classnames, streamName, customer_id, cameraId, model_name, last_fire_capture_time, min_fire_interval):
    result = model(frame)
    fire_detected = False
    message = 0

    for info in result:
        boxes = info.boxes
        for box in boxes:
            confidence = box.conf[0]
            confidence = math.ceil(confidence * 100)
            Class = int(box.cls[0])
            if confidence >= 90:
                fire_detected = True
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 1)
                cvzone.putTextRect(frame, f'{classnames[Class]} {confidence}%', [x1 + 8, y1 + 100], scale=1.5, thickness=1)

    time_now = datetime.datetime.now()

    if fire_detected and (time_now - last_fire_capture_time) > min_fire_interval:
        last_fire_capture_time = time_now
        image_name = time_now.strftime("%Y-%m-%d-%H:%M:%S") + "_" + streamName + ".jpg"
        image_path = os.path.join(VIDEO_IMAGE_STORAGE_BASE_PATH, image_name)
        
        cv2.imwrite(image_path, frame)
        
        # Call the API asynchronously
        threading.Thread(target=async_api_call, args=(streamName, customer_id, image_name, cameraId, model_name, message)).start()
        print()
        # Send an email alert when fire is detected
        send_fire_alert_email(
            subject="Fire Alert! 🔥",
            message="Fire has been detected. Please take appropriate action.",
            to_email="pragneshkumar.jariwala@eyeqindia.com",
            image_path=image_path,
        )

    return frame, last_fire_capture_time, fire_detected

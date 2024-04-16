import cv2
import cvzone
import math
import datetime
import threading
from app.utils.async_api import async_api_call
from app.config import VIDEO_IMAGE_STORAGE_BASE_PATH
import os
def process_fire_detection(frame, model, classnames, streamName, customer_id, cameraId, model_name, last_fire_capture_time, min_fire_interval):
    result = model(frame)
    fire_detected = False

    for info in result:
        boxes = info.boxes
        for box in boxes:
            confidence = box.conf[0]
            confidence = math.ceil(confidence * 100)
            Class = int(box.cls[0])
            if confidence > 60:
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
        threading.Thread(target=async_api_call, args=(streamName, customer_id, image_name, cameraId, model_name, "fire_detected")).start()

    return frame, last_fire_capture_time, fire_detected

import cv2
import os
import datetime
import threading  # Import threading for asynchronous API calls
from app.utils.async_api import async_api_call
min_interval = datetime.timedelta(seconds=10)

def process_crowd_detection(frame, detections, model_name, time_reference, counter_frame, previous_num_people, last_capture_time, streamName, customer_id, cameraId):
    num_people = 0
    for obj in detections:
        if int(obj[5]) == 0 and obj[4] >= 0.60:  # Check confidence
            xmin, ymin, xmax, ymax = map(int, obj[:4])
            num_people += 1
            cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 0, 255), 1)
            cv2.putText(frame, "person", (xmin, ymin - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)

    time_now = datetime.datetime.now()
    cv2.putText(frame, f'People: {num_people}', (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    if num_people != previous_num_people and (time_now - last_capture_time) > min_interval:
        # Update previous count and last capture time
        previous_num_people = num_people
        last_capture_time = time_now
        image_name = time_now.strftime("%Y-%m-%d-%H:%M:%S") + "_" + streamName + ".jpg"
        image_path = "/home/torqueai/github/torque/organize-app/blobdrive/" + image_name

        cv2.imwrite(image_path, frame)
        # Call the API asynchronously
        threading.Thread(target=async_api_call, args=(streamName, customer_id, image_name, cameraId, model_name, num_people)).start()

    # cv2.putText(frame, f'People: {num_people}', (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # Update frame processing logic
    time_diff = (time_now - time_reference).total_seconds()
    if time_diff >= 1:
        processed_fps = counter_frame
        counter_frame = 0
        time_reference = time_now  # Reset time_reference for FPS calculation
    else:
        counter_frame += 1

    return frame, time_reference, counter_frame, previous_num_people, last_capture_time, streamName, customer_id, cameraId


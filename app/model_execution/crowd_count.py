import os
from app.config import MODEL_BASE_PATH, VIDEO_IMAGE_STORAGE_BASE_PATH
import threading
import cv2
import datetime
import time
from app.utils.async_api import async_api_call
from app.error_warning_handling import update_camera_status_in_database
from app.utils.globals import last_capture_time_crowd_count, min_interval_crowd_count,previous_num_people,counter_frame,processed_fps,time_reference



def process_and_stream_frames_crowd(process,frame,model, model_name, customer_id, cameraId, streamName,width,height):
    global last_capture_time_crowd_count, min_interval_crowd_count,previous_num_people,num_people,processed_fps,counter_frame,time_reference
  

    results = model(frame)
            
    detections = results.xyxy[0].cpu().numpy()  # Get detection results
    time_now = datetime.datetime.now()
    time_diff = (time_now - time_reference).total_seconds()
    num_people = 0
    
    for obj in detections:
        # Class ID for 'person' is assumed to be 0
        if int(obj[5]) == 0 and obj[4] >= 0.60:  # Check confidence
            xmin, ymin, xmax, ymax = map(int, obj[:4])
            num_people += 1
            cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 0, 255), 2)
            cv2.putText(frame, f"person {obj[4]:.2f}", (xmin, ymin - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

    # Update FPS calculation
    
    if time_diff >= 1:
        time_reference = time_now
        processed_fps = counter_frame
        counter_frame = 0
    else:
        counter_frame += 1

    # Display the number of people and FPS on the frame
    cv2.putText(frame, f'People: {num_people}', (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    if num_people != previous_num_people and (time_now - last_capture_time_crowd_count) >= min_interval_crowd_count:
        previous_num_people = num_people # Capture an image every 5 minutes (300 seconds)
        
        streamName = streamName
        image_name = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S") +"_"+ streamName +".jpg"
        image_path = VIDEO_IMAGE_STORAGE_BASE_PATH + image_name
        cv2.imwrite(image_path, frame)
        last_capture_time_crowd_count = time_now
                        # Call the API asynchronously
        threading.Thread(target=async_api_call, args=(streamName, customer_id,image_name,cameraId,model_name,num_people)).start()

    try:
        process.stdin.write(frame.tobytes())
    except BrokenPipeError:
        print("Broken pipe - FFmpeg process may have terminated unexpectedly.")
        update_camera_status_in_database(cameraId, False)
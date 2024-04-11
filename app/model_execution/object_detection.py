import os
from app.config import MODEL_BASE_PATH,VIDEO_IMAGE_STORAGE_BASE_PATH
import threading
import cv2
import datetime
import time
from app.utils.async_api import async_api_call
from app.error_warning_handling import update_camera_status_in_database
import torch
from app.utils.tracking import BasicTracker
from app.utils.globals import frames_since_last_capture,min_interval_object_detection,last_capture_time_object_detection 

def process_and_stream_frames_object_det(frame, model,model_name, time_reference, counter_frame, previous_num_people, last_capture_time, streamName, customer_id, cameraId):
    global frames_since_last_capture,last_capture_time_object_detection
    time_now = datetime.datetime.now()
    customer_id = customer_id
    cameraId = cameraId
    streamName = streamName
   
    tracker = BasicTracker()
    class_counts = {}
    
    # Initialize variables for video recording
    recording_start_time = None
    video_out = None
    recording_duration = 60  # seconds
    
    # Get detection results
    results = model(frame)
    detections = results.xyxy[0].cpu().numpy()
    
    tracked_objects, new_ids = tracker.update(detections)
    
    for obj_id, obj in tracked_objects.items():
        x1, y1, x2, y2 = obj['bbox']
        class_id = int(obj['cls'])
        class_name = model.names[class_id]
        label = f"{model.names[int(obj['cls'])]}"
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 1)
        cv2.putText(frame, label, (int(x1), int(y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 1)
        
        # Check if the object ID is not in the frames_since_last_capture and update accordingly
        if obj_id not in frames_since_last_capture:
            frames_since_last_capture[obj_id] = 0
        
        # Update class counts
        if class_name in class_counts:
            class_counts[class_name] += 1
        else:
            class_counts[class_name] = 1
        
        # Capture image if a new object is detected and enough frames have passed since the last capture
        if obj_id in new_ids and (time_now - last_capture_time_object_detection) >= min_interval_object_detection:
            streamName = streamName
            image_name = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S") + "_" + streamName + ".jpg"
            image_path = VIDEO_IMAGE_STORAGE_BASE_PATH + image_name 

            cv2.imwrite(image_path, frame)
              # Call the API asynchronously
            # threading.Thread(target=async_api_call, args=(streamName, customer_id, image_name, cameraId, model_name, len(class_counts))).start()
            last_capture_time_object_detection=time_now
        #     print("lassst",last_capture_time_object_detection)
        #     # last_capture_time_object_detection = time_now
        #     recording_start_time = datetime.datetime.now()
        #     video_filename = f"{recording_start_time.strftime('%Y-%m-%d-%H-%M-%S')}_{streamName}.avi"
        #     video_path = os.path.join(VIDEO_IMAGE_STORAGE_BASE_PATH, video_filename)
        #     fourcc = cv2.VideoWriter_fourcc(*'XVID')
        #     video_out = cv2.VideoWriter(video_path, fourcc, 30.0, (width, height))
        
        # # Record video if within the 1-minute timeframe
        # if recording_start_time and (datetime.datetime.now() - recording_start_time).seconds <= recording_duration:
        #     video_out.write(frame)
        # elif recording_start_time and (datetime.datetime.now() - recording_start_time).seconds > recording_duration:
        #     # Stop recording after 1 minute
        #     video_out.release()
        #     video_out = None
        #     recording_start_time = None  # Reset recording flag
        
          
        # try:
        #     process.stdin.write(frame.tobytes())
        # except BrokenPipeError:
        #     print("Broken pipe - FFmpeg process may have terminated unexpectedly.")
        #     update_camera_status_in_database(cameraId,False)
        #     break

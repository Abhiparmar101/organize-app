
from app.config import VIDEO_IMAGE_STORAGE_BASE_PATH
import threading
import cv2
import datetime
import os
from app.utils.async_api import async_api_call
from app.error_warning_handling import update_camera_status_in_database
from app.ppe_kit.sort_master.sort import Sort
import math
import numpy as np
from app.utils.email_service import send_email_notification_with_image
from app.utils.globals import min_interval_ppe_kit_det,last_capture_time_ppe_kit_det
####################################################################################



classNames = ['Hardhat', 'Mask', 'NO-Hardhat', 'NO-Mask', 'NO-Safety Vest', 'Person', 'Safety Cone',
                'Safety Vest', 'machinery', 'vehicle']

# Initialize the SORT tracker
mot_tracker = Sort()
tracked_persons = {}
def process_and_stream_frames_ppe_kit_det(process,frame,Model, model_name, customer_id, cameraId, streamName,width,height):
    global min_interval_ppe_kit_det,last_capture_time_ppe_kit_det
    time_now = datetime.datetime.now()
    customer_id = customer_id
    cameraId = cameraId
    streamName = streamName
    frame_objects = []
    
     # Initialize variables for video recording
    recording_start_time = None
    video_out = None
    recording_duration = 60  # seconds
    
    # Get detection results
    results = Model(frame)
  
    
    for r in results:
        boxes = r.boxes
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            conf = math.ceil((box.conf[0] * 100)) / 100
            cls = int(box.cls[0])
            class_name = classNames[cls]
            label = f'{class_name}{conf}'

            if class_name == 'Person':
                if conf > 0.7:
                    frame_objects.append([x1, y1, x2, y2])
                  

            # Draw bounding boxes and labels
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 1)
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    if frame_objects:
       
        # Pass the frame_objects to the SORT tracker
        trackers = mot_tracker.update(np.array(frame_objects))

        for d in trackers:
            x1, y1, x2, y2, track_id = d
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

            if class_name in ['NO-Hardhat', 'NO-Mask', 'NO-Safety Vest', 'Person']:
                # Person detected without safety gear
                if conf > 0.7:
                    
                    # Check if this person has been tracked before
                    if track_id not in tracked_persons:
                        tracked_persons[track_id] = {'detected_safety_gear': False}
                        
                    if not tracked_persons[track_id]['detected_safety_gear'] and  (time_now - last_capture_time_ppe_kit_det) >= min_interval_ppe_kit_det :
                        
                        streamName = streamName
                        image_name = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S") + "_"+streamName +".jpg"
                        image_path = VIDEO_IMAGE_STORAGE_BASE_PATH + image_name 

                        cv2.imwrite(image_path, frame)
                        last_capture_time_ppe_kit_det = time_now
                        threading.Thread(target=async_api_call, args=(streamName, customer_id,image_name,cameraId,model_name,0)).start()
                        email_thread = threading.Thread(target=send_email_notification_with_image,
                                            args=("PERSON WITHOUT PPE!", "A PERSON has been detected without ppe kit. Please take immediate safety action.", image_path))
                        email_thread.start()

                        email_sent_flag = True
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
        

    try:
        process.stdin.write(frame.tobytes())
    except BrokenPipeError:
        print("Broken pipe - FFmpeg process may have terminated unexpectedly.")
        update_camera_status_in_database(cameraId,False)

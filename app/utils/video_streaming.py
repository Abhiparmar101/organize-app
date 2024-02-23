

import threading
from collections import deque
import numpy as np
import os
from app.config import MODEL_BASE_PATH,VIDEO_IMAGE_STORAGE_BASE_PATH
import torch
import cv2
import subprocess as sp
from app.utils.tracking import BasicTracker
from app.utils.async_api import async_api_call
from app.utils.email_service import send_email_notification_with_image
import datetime
import time
from app.utils.globals import stream_processes
from app.error_warning_handling import update_camera_status_in_database
#########################################################################3
selected_model_name = None  # No default model
detected_ids = set() 

frames_since_last_capture = {}
email_sent_flag = False








def process_and_stream_frames(model_name, camera_url, stream_key,customer_id,cameraId,streamName):
    global stream_processes,frames_since_last_capture
    print("cameraaaaa",cameraId)
    rtmp_url = stream_key
    model_path = f'{MODEL_BASE_PATH}/{model_name}.pt'
    model = torch.hub.load('yolov5', 'custom', path=model_path, source='local', force_reload=True, device=0)
    
    # Set the confidence threshold to 0.7
    model.conf = 0.7
    
    video_cap = cv2.VideoCapture(camera_url)
    width = int(video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    command = ['ffmpeg',
               '-f', 'rawvideo',
               '-pix_fmt', 'bgr24',
               '-s', '{}x{}'.format(int(video_cap.get(3)), int(video_cap.get(4))),
               '-r', '5',
               '-i', '-',
               '-c:v', 'libx264',
               '-pix_fmt', 'yuv420p',
               '-f', 'flv',
               rtmp_url]
    process = sp.Popen(command, stdin=sp.PIPE)
    stream_processes[stream_key] = process
    
    tracker = BasicTracker()
    time_reference = datetime.datetime.now()
    counter_frame = 0
    processed_fps = 0
    num_people = 0
    FIRE_CLASS_ID = 1
    customer_id=customer_id
    cameraId=cameraId
    
    streamName=streamName
    previous_num_people = 0
    last_capture_time = datetime.datetime.min  # Initialize with a minimum time

    min_interval = datetime.timedelta(seconds=30)  # Minimum time interval between captures
    class_counts = {}

    last_capture_time = datetime.datetime.now() - datetime.timedelta(seconds=10)
    # Initialize variables for video recording
    recording_start_time = None
    video_out = None
    recording_duration = 60  # seconds
    last_successful_read = time.time()
    timeout_threshold = 30  # Seconds

 
    try:
        while True:
            ret, frame = video_cap.read()
            if not ret:
               
                update_camera_status_in_database(cameraId,False)
                break
         
            results = model(frame)
            
            detections = results.xyxy[0].cpu().numpy()  # Get detection results

            # Update tracker and draw bounding boxes
            tracked_objects, new_ids = tracker.update(detections)
            time_now = datetime.datetime.now()
            time_diff = (time_now - time_reference).total_seconds()
            if model_name == 'crowd':
                   
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
                if num_people != previous_num_people and (time_now - last_capture_time) >= min_interval and recording_start_time is None:
                    previous_num_people = num_people # Capture an image every 5 minutes (300 seconds)
                    last_capture_time = time_now
                    streamName = streamName
                    image_name = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S") +"_"+ streamName +".jpg"
                    image_path = VIDEO_IMAGE_STORAGE_BASE_PATH + image_name
                    cv2.imwrite(image_path, frame)
                    last_capture_time = time_now
                                    # Call the API asynchronously
                    threading.Thread(target=async_api_call, args=(streamName, customer_id,image_name,cameraId,model_name,num_people)).start()
                    recording_start_time = datetime.datetime.now()
                    video_filename = f"{recording_start_time.strftime('%Y-%m-%d-%H-%M-%S')}_{streamName}.avi"
                    video_path = os.path.join(VIDEO_IMAGE_STORAGE_BASE_PATH, video_filename)
                    fourcc = cv2.VideoWriter_fourcc(*'XVID')
                    video_out = cv2.VideoWriter(video_path, fourcc, 30.0, (width, height))

                # Record video if within the 1-minute timeframe
                if recording_start_time and (datetime.datetime.now() - recording_start_time).seconds <= recording_duration:
                    video_out.write(frame)
                elif recording_start_time and (datetime.datetime.now() - recording_start_time).seconds > recording_duration:
                    # Stop recording after 1 minute
                    video_out.release()
                    video_out = None
                    recording_start_time = None  # Reset recording flag
                if model_name == 'fire':
               
                            # # Optionally, save the frame if fire is detected
                    for *xyxy, conf, cls in results.xyxy[0].cpu().numpy():
                        # Assuming fire class ID is 0, adjust according to your model
                        if cls == 0:
                            label = f'Fire {conf:.2f}'
                            cv2.rectangle(frame, (int(xyxy[0]), int(xyxy[1])), (int(xyxy[2]), int(xyxy[3])), (0, 0, 255), 2)
                            cv2.putText(frame, label, (int(xyxy[0]), int(xyxy[1])-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255,255,255), 2)
                                                                                   
                            today_folder = datetime.datetime.now().strftime("%Y-%m-%d")
                            image_folder_path = os.path.join(os.getcwd(), "history", today_folder, model_name)
                            if not os.path.exists(image_folder_path):
                                os.makedirs(image_folder_path)
                            streamName = streamName
                            image_name = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S") + "_"+ streamName +".jpg"
                            image_path = VIDEO_IMAGE_STORAGE_BASE_PATH + image_name 

                            cv2.imwrite(image_path, frame)
                            last_capture_time = time_now
                            recording_start_time = datetime.datetime.now()
                            video_filename = f"{recording_start_time.strftime('%Y-%m-%d-%H-%M-%S')}_{streamName}.avi"
                            video_path = os.path.join(VIDEO_IMAGE_STORAGE_BASE_PATH, video_filename)
                            fourcc = cv2.VideoWriter_fourcc(*'XVID')
                            video_out = cv2.VideoWriter(video_path, fourcc, 30.0, (width, height))

                        # Record video if within the 1-minute timeframe
                        if recording_start_time and (datetime.datetime.now() - recording_start_time).seconds <= recording_duration:
                            video_out.write(frame)
                        elif recording_start_time and (datetime.datetime.now() - recording_start_time).seconds > recording_duration:
                            # Stop recording after 1 minute
                            video_out.release()
                            video_out = None
                            recording_start_time = None  # Reset recording flag
                            # Call the API asynchronously
                            threading.Thread(target=async_api_call, args=(streamName, customer_id,image_name,cameraId,model_name,0)).start()
                         


                            email_thread = threading.Thread(target=send_email_notification_with_image,
                                                            args=("Fire Detected!", "A fire has been detected. Please take immediate action.", image_path))
                            email_thread.start()

                            email_sent_flag = True
            else: 
                     
                        # Render frame with tracked objects
                for obj_id, obj in tracked_objects.items():
                    x1, y1, x2, y2 = obj['bbox']
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    class_id = int(obj['cls'])
                    class_name = model.names[class_id]
                    label = f"{model.names[int(obj['cls'])]}"
                    cv2.putText(frame, label, (int(x1), int(y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

                    # Check if the object ID is not in the frames_since_last_capture and update accordingly
                    if obj_id not in frames_since_last_capture:
                        frames_since_last_capture[obj_id] = 0
                     # Update class counts
                    if class_name in class_counts:
                        class_counts[class_name] += 1
                    else:
                        class_counts[class_name] = 1
                    # Capture image if new object is detected and enough frames have passed since the last capture
                    if obj_id in new_ids and (time_now - last_capture_time) >= min_interval :
                        streamName = streamName
                        image_name = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S") + "_"+streamName +".jpg"
                        image_path = VIDEO_IMAGE_STORAGE_BASE_PATH + image_name 

                        cv2.imwrite(image_path, frame)
                        last_capture_time = time_now
                        recording_start_time = datetime.datetime.now()
                        video_filename = f"{recording_start_time.strftime('%Y-%m-%d-%H-%M-%S')}_{streamName}.avi"
                        video_path = os.path.join(VIDEO_IMAGE_STORAGE_BASE_PATH, video_filename)
                        fourcc = cv2.VideoWriter_fourcc(*'XVID')
                        video_out = cv2.VideoWriter(video_path, fourcc, 30.0, (width, height))

                    # Record video if within the 1-minute timeframe
                    if recording_start_time and (datetime.datetime.now() - recording_start_time).seconds <= recording_duration:
                        video_out.write(frame)
                    elif recording_start_time and (datetime.datetime.now() - recording_start_time).seconds > recording_duration:
                        # Stop recording after 1 minute
                        video_out.release()
                        video_out = None
                        recording_start_time = None  # Reset recording flag
                         # Call the API asynchronously
                        threading.Thread(target=async_api_call, args=(streamName, customer_id,image_name,cameraId,model_name,len(class_counts))).start()
                

            
            try:
                process.stdin.write(frame.tobytes())
            except BrokenPipeError:
                print("Broken pipe - FFmpeg process may have terminated unexpectedly.")
                update_camera_status_in_database(cameraId,False)
                break
    except Exception as e:
        print(f"An error occurred: {e}")
        update_camera_status_in_database(cameraId,False)
    finally:
        if video_out is not None:
            video_out.release()
            update_camera_status_in_database(cameraId, False)
        if process.poll() is None:
            process.terminate()
            process.wait()
        if stream_key in stream_processes:
            del stream_processes[stream_key]
        
        video_cap.release()
        
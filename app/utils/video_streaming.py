
import logging
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
from app.model_execution.crowd_count import process_crowd_detection
import sys
import math
import cvzone
#########################################################################3
selected_model_name = None  # No default model
detected_ids = set() 

frames_since_last_capture = {}
email_sent_flag = False


# Configure logging
logging.basicConfig(filename='logs/video_streaming.log', filemode='a', format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)


def log_subprocess_stderr(process, logger):
    """
    Reads stderr from the subprocess and logs each line.
    
    :param process: The subprocess object.
    :param logger: Logger object for logging messages.
    """
    while True:
        line = process.stderr.readline()
        if not line:
            break
        logger.error(line.decode().strip())

def process_and_stream_frames(model_name, camera_url, stream_key,customer_id,cameraId,streamName):
    global stream_processes,frames_since_last_capture
    print("cameraaaaa",cameraId)
    logging.info(f"Starting camera stream: {cameraId}")
    rtmp_url = stream_key
    video_cap = cv2.VideoCapture(camera_url)
    print(camera_url)
    width = int(video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    # command = ['ffmpeg',
    #         '-f', 'rawvideo',
    #         '-pix_fmt', 'bgr24',
    #         '-s', '{}x{}'.format(int(video_cap.get(3)), int(video_cap.get(4))),
    #         '-r', '30',  # Consider a higher frame rate if bandwidth allows
    #         '-i', '-',
    #         '-c:v', 'libx264',
    #         '-preset', 'ultrafast',  # Faster encoding
    #         '-tune', 'zerolatency',  # Optimized for low latency
    #         '-pix_fmt', 'yuv420p',
    #         '-g', '30',  # Keyframe every second if 30fps
    #         '-f', 'flv',
    #         rtmp_url]
    fps =15
    command = ['ffmpeg',
               '-y',
               '-f', 'rawvideo',
               '-vcodec', 'rawvideo',
               '-pix_fmt', 'bgr24',
               '-s', "{}x{}".format(width, height),
               '-r', str(fps),
               '-i', '-',
               '-pix_fmt', 'yuv420p',
               '-preset', 'superfast',
               '-f', 'flv',
               '-vcodec', 'libx264',
               '-ar', '8k',
               rtmp_url]


    process = sp.Popen(command, stdin=sp.PIPE,stderr=sp.PIPE)
    stream_processes[stream_key] = process
    # After starting the FFmpeg process
    # Start logging stderr in a separate thread
    stderr_thread = threading.Thread(target=log_subprocess_stderr, args=(process, logging))
    stderr_thread.daemon = True  # Ensure thread exits when the main program does
    stderr_thread.start()
    
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

    min_interval = datetime.timedelta(seconds=10)  # Minimum time interval between captures
    class_counts = {}

    last_capture_time = datetime.datetime.now() - datetime.timedelta(seconds=10)
    # Initialize variables for video recording
    recording_start_time = None
    video_out = None
    recording_duration = 60  # seconds
    last_successful_read = time.time()
    timeout_threshold = 30  # Seconds
    min_fire_interval = datetime.timedelta(minutes=2)  # Minimum time interval between fire captures
    fire_detected = False

    if model_name != 'firev8':
        # Load model for other types (e.g., crowd detection)
        model_path = os.path.join(MODEL_BASE_PATH, f'{model_name}.pt')
        model = torch.hub.load('yolov5', 'custom', path=model_path, source='local', force_reload=True, device='cpu')
        model.conf = 0.7  # Set the confidence threshold
    else:
        # Specific setup for fire detection model
        from ultralytics import YOLO  # Import here to ensure it's only needed for fire detection
        model = YOLO(os.path.join(MODEL_BASE_PATH, 'firev8.pt'))
        classnames = ['fire']

    try:
        while True:
            ret, frame = video_cap.read()
            if not ret:
                update_camera_status_in_database(cameraId, False)
                break

            if model_name == 'firev8':
                # Fire detection processing
                result = model(frame)
                
                for info in result:
                    boxes = info.boxes
                    for box in boxes:
                            confidence = box.conf[0]
                            confidence = math.ceil(confidence * 100)
                            Class = int(box.cls[0])
                            if confidence > 50:
                                x1,y1,x2,y2 = box.xyxy[0]
                                x1, y1, x2, y2 = int(x1),int(y1),int(x2),int(y2)
                                cv2.rectangle(frame,(x1,y1),(x2,y2),(0,0,255),1)
                                cvzone.putTextRect(frame, f'{classnames[Class]} {confidence}%', [x1 + 8, y1 + 100],
                                        scale=1.5,thickness=1)
            time_now = datetime.datetime.now()
            
            if fire_detected and (time_now - last_fire_capture_time) > min_fire_interval:
                last_fire_capture_time = time_now
                image_name = time_now.strftime("%Y-%m-%d-%H:%M:%S") + "_" + streamName + ".jpg"
                image_path = os.path.join(VIDEO_IMAGE_STORAGE_BASE_PATH, image_name)
                
                cv2.imwrite(image_path, frame)
                # Call the API asynchronously
                threading.Thread(target=async_api_call, args=(streamName, customer_id, image_name, cameraId, model_name, "fire_detected")).start()
            elif model_name == 'crowd':
                results = model(frame)
            
                detections = results.xyxy[0].cpu().numpy()  # Get detection results
                frame, time_reference, counter_frame, previous_num_people, last_capture_time, streamName,customer_id, cameraId = process_crowd_detection(frame, detections, model_name, time_reference, counter_frame, previous_num_people, last_capture_time, streamName, customer_id, cameraId)   

 
    
            
            try:
                process.stdin.write(frame.tobytes())
               
            except BrokenPipeError:
                print("Broken pipe - FFmpeg process may have terminated unexpectedly.")

                update_camera_status_in_database(cameraId,False)
                logging.error(f"Stream terminated: {stream_key}")
                break
    except Exception as e:
        print(f"An error occurred: {e}")
        update_camera_status_in_database(cameraId,False)
        logging.error(f"An unexpected error occurred: {e}")
    finally:
        if video_out is not None:
            video_out.release()
            update_camera_status_in_database(cameraId, False)
            
        if process.poll() is None:
            process.terminate()
            process.wait()
        if stream_key in stream_processes:
            logging.error(f"Stream stopped: {stream_key}")
            del stream_processes[stream_key]
            
        
        
import os
from app.config import MODEL_BASE_PATH, VIDEO_IMAGE_STORAGE_BASE_PATH
import threading
import cv2
import datetime
import time
from app.utils.async_api import async_api_call
from app.error_warning_handling import update_camera_status_in_database
from app.utils.globals import last_capture_time_crowd_count, min_interval_crowd_count


def process_and_stream_frames_crowd(process, frame, model, model_name, customer_id, cameraId, streamName, width, height, time_reference,previous_num_people,num_people):
    global last_capture_time_crowd_count, min_interval_crowd_count
    counter_frame = 0
    processed_fps = 0
  

    streamName = streamName
    
   
    # Initialize variables for video recording
    recording_start_time = None
    video_out = None
    recording_duration = 60  # seconds
    last_successful_read = time.time()
    timeout_threshold = 30  # Seconds

    results = model(frame)

    detections = results.xyxy[0].cpu().numpy()  # Get detection results

    time_now = datetime.datetime.now()
    time_diff = (time_now - time_reference).total_seconds()

    num_people = 0

    for obj in detections:
        # Class ID for 'person' is assumed to be 0
        if int(obj[5]) == 0 and obj[4] >= 0.60:  # Check confidence
            print("555",obj[5],"444",obj[4])
            xmin, ymin, xmax, ymax = map(int, obj[:4])
            num_people += 1  # Increment num_people for each detected person
            cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 0, 255), 2)
            cv2.putText(frame, f"person {obj[4]:.2f}", (xmin, ymin - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0),
                        2)
            
    # Update FPS calculation

    if time_diff >= 1:
        time_reference = time_now
        processed_fps = counter_frame
        counter_frame = 0
    else:
        counter_frame += 1

    # Display the number of people and FPS on the frame
    cv2.putText(frame, f'People: {num_people}', (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # Rest of your code remains the same
    if num_people != previous_num_people and (time_now - last_capture_time_crowd_count) >= min_interval_crowd_count and recording_start_time is None:
        previous_num_people = num_people  # Update previous_num_people
        
        # Capture and send data only if num_people is different from previous_num_people
        streamName = streamName
        image_name = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S") + "_" + streamName + ".jpg"
        image_path = VIDEO_IMAGE_STORAGE_BASE_PATH + image_name
        cv2.imwrite(image_path, frame)
        last_capture_time_crowd_count = time_now

        # Call the API asynchronously
        threading.Thread(target=async_api_call, args=(streamName, customer_id, image_name, cameraId, model_name, num_people)).start()
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

    try:
        process.stdin.write(frame.tobytes())
    except BrokenPipeError:
        print("Broken pipe - FFmpeg process may have terminated unexpectedly.")
        update_camera_status_in_database(cameraId, False)
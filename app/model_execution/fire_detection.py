
import os
from app.config import MODEL_BASE_PATH,VIDEO_IMAGE_STORAGE_BASE_PATH
import threading
import cv2
import datetime

from app.utils.async_api import async_api_call
from app.utils.email_service import send_email_notification_with_image
from app.error_warning_handling import update_camera_status_in_database

email_sent_flag = False

def process_and_stream_frames_fire_det(process,frame,model, model_name, customer_id, cameraId, streamName,width,height):
    
    customer_id=customer_id
    cameraId=cameraId

    streamName=streamName
  
    # Initialize variables for video recording
    recording_start_time = None
    video_out = None
    recording_duration = 60  # seconds

    time_now = datetime.datetime.now()
   
    results = model(frame)
    
    detections = results.xyxy[0].cpu().numpy()  # Get detection results
    for *xyxy, conf, cls in detections:
        # Assuming fire class ID is 0, adjust according to your model
        if cls == 0:
            label = f'Fire {conf:.2f}'
            cv2.rectangle(frame, (int(xyxy[0]), int(xyxy[1])), (int(xyxy[2]), int(xyxy[3])), (0, 0, 255), 2)
            cv2.putText(frame, label, (int(xyxy[0]), int(xyxy[1])-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255,255,255), 2)
                                                                    
            
           
            image_name = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S") + "_"+ streamName +".jpg"
            image_path = VIDEO_IMAGE_STORAGE_BASE_PATH + image_name 

            cv2.imwrite(image_path, frame)
            threading.Thread(target=async_api_call, args=(streamName, customer_id,image_name,cameraId,model_name,0)).start()
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
        #     # Call the API asynchronously
           
            


            email_thread = threading.Thread(target=send_email_notification_with_image,
                                            args=("Fire Detected!", "A fire has been detected. Please take immediate action.", image_path))
            email_thread.start()

            email_sent_flag = True

    try:
        process.stdin.write(frame.tobytes())
    except BrokenPipeError:
        print("Broken pipe - FFmpeg process may have terminated unexpectedly.")
        update_camera_status_in_database(cameraId,False)
        

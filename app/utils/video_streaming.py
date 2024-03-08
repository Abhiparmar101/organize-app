from app.config import MODEL_BASE_PATH, VIDEO_IMAGE_STORAGE_BASE_PATH
import torch
import cv2
import subprocess as sp
import datetime
import threading
from app.utils.async_api import async_api_call
from app.utils.globals import stream_processes,frames_since_last_capture
from app.error_warning_handling import update_camera_status_in_database
from app.model_execution.crowd_count import process_and_stream_frames_crowd
from app.model_execution.fire_detection import process_and_stream_frames_fire_det
from app.model_execution.object_detection import process_and_stream_frames_object_det
from app.model_execution.ppe_kit_detection import process_and_stream_frames_ppe_kit_det
from app.utils.globals import last_capture_time_crowd_count, min_interval_crowd_count
from ultralytics import YOLO
#########################################################################3
selected_model_name = None  # No default model
detected_ids = set() 





def process_and_stream_frames(model_name, camera_url, stream_key,customer_id,cameraId,streamName):
    global stream_processes,frames_since_last_capture,last_capture_time_crowd_count,min_interval_crowd_count
    print("cameraaaaa",cameraId)
    rtmp_url = stream_key
   
    video_cap = cv2.VideoCapture(camera_url)
    width = int(video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    model_path = f'{MODEL_BASE_PATH}/{model_name}.pt'
    if model_name == "ppe_kit_det":
        Model = YOLO(model_path)
        
    else:
        model = torch.hub.load('yolov5', 'custom', path=model_path, source='local', force_reload=True, device=0)

        # Set the confidence threshold to 0.7
        model.conf = 0.7

    fps =15
    command = ['ffmpeg',
                '-y',
                '-f', 'rawvideo',
                #'-acodec','aac',
                '-vcodec','rawvideo',
                '-pix_fmt', 'bgr24',
                '-s', "{}x{}".format(width, height),
                '-r', str(fps),
                '-i', '-',
                '-pix_fmt', 'yuv420p',
                '-preset' , 'superfast',
                '-f', 'flv',
                '-vcodec','libx264',
                '-ar','8K',
                #'-b:v','180k',
                #'-b:a', '64k', 
                rtmp_url]


    process = sp.Popen(command, stdin=sp.PIPE)
    stream_processes[stream_key] = process
    
    video_out = None
    # last_capture_time = datetime.datetime.min  # Initialize with a minimum time

    


    time_reference = datetime.datetime.now()
   
    counter_frame = 0
    processed_fps = 0
    num_people=0
    previous_num_people=0
    
    #time_diff = (time_now - time_reference).total_seconds()
    try:
        while True:
            ret, frame = video_cap.read()
            if not ret:
                update_camera_status_in_database(cameraId,False)
                break
       
            if model_name == 'crowd':
                process_and_stream_frames_crowd(process,frame,model, model_name, customer_id, cameraId, streamName,width,height)
                # results = model(frame)
            
                # detections = results.xyxy[0].cpu().numpy()  # Get detection results
                # time_now = datetime.datetime.now()
                # time_diff = (time_now - time_reference).total_seconds()
                # num_people = 0
               
                # for obj in detections:
                #     # Class ID for 'person' is assumed to be 0
                #     if int(obj[5]) == 0 and obj[4] >= 0.60:  # Check confidence
                #         xmin, ymin, xmax, ymax = map(int, obj[:4])
                #         num_people += 1
                #         cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 0, 255), 2)
                #         cv2.putText(frame, f"person {obj[4]:.2f}", (xmin, ymin - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

                # # Update FPS calculation
               
                # if time_diff >= 1:
                #     time_reference = time_now
                #     processed_fps = counter_frame
                #     counter_frame = 0
                # else:
                #     counter_frame += 1

                # # Display the number of people and FPS on the frame
                # cv2.putText(frame, f'People: {num_people}', (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                # if num_people != previous_num_people and (time_now - last_capture_time_crowd_count) >= min_interval_crowd_count:
                #     previous_num_people = num_people # Capture an image every 5 minutes (300 seconds)
                   
                #     streamName = streamName
                #     image_name = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S") +"_"+ streamName +".jpg"
                #     image_path = VIDEO_IMAGE_STORAGE_BASE_PATH + image_name
                #     cv2.imwrite(image_path, frame)
                #     last_capture_time_crowd_count = time_now
                #                     # Call the API asynchronously
                #     threading.Thread(target=async_api_call, args=(streamName, customer_id,image_name,cameraId,model_name,num_people)).start()
                    
     
            if model_name == 'fire':
                process_and_stream_frames_fire_det(process,frame,model, model_name, customer_id, cameraId, streamName,width,height)
            if model_name == 'ppe_kit_det':
                process_and_stream_frames_ppe_kit_det(process,frame,Model, model_name, customer_id, cameraId, streamName,width,height)
            else:
                process_and_stream_frames_object_det(process,frame,model, model_name, customer_id, cameraId, streamName,width,height) 
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
        
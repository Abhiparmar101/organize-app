import requests
import datetime
import cv2
import datetime
import os

def async_api_call(streamName, customer_id,image_name,cameraId,model_name,imgcount):
    """
    Asynchronously sends data to the API.
    """
    try:
        image_name = image_name
        img_url= f"https://inferenceimage.blob.core.windows.net/inferenceimages/{image_name}"
        send_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = {
            'cameraid': cameraId, 
            'sendtime': send_time, 
            'imgurl': img_url,
            'modelname': model_name, 
            'ImgCount': int(imgcount),
            'customerid': customer_id,
            'streamname':streamName
        }
        api_url="https://event-app-2-sp4ow.ondigitalocean.app/api/post-analytics"

        response = requests.post(api_url, json=data)
        if response.status_code == 200:
            print("Data sent successfully!", imgcount,"url:",img_url)
        else:
            print("Failed to send data! Response Code:", response.status_code)
    except Exception as e:
        print(f"Error sending data to API: {e}")

class Recorder:
    def __init__(self, base_path, width, height, fps=10.0):
        self.base_path = base_path
        self.width = width
        self.height = height
        self.fps = fps
        self.video_out = None
        self.recording_start_time = None
        self.recording_duration = 30  # seconds

    def start_recording(self, streamName):
        if self.recording_start_time is None:
            self.recording_start_time = datetime.datetime.now()
            video_filename = f"{self.recording_start_time.strftime('%Y-%m-%d-%H-%M-%S')}_{streamName}.avi"
            video_path = os.path.join(self.base_path, video_filename)
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            self.video_out = cv2.VideoWriter(video_path, fourcc, self.fps, (self.width, self.height))
    
    def record_frame(self, frame):
        if self.recording_start_time and (datetime.datetime.now() - self.recording_start_time).seconds <= self.recording_duration:
            self.video_out.write(frame)
        elif self.recording_start_time and (datetime.datetime.now() - self.recording_start_time).seconds > self.recording_duration:
            self.stop_recording()

    def stop_recording(self):
        if self.video_out is not None:
            self.video_out.release()
            self.video_out = None
            self.recording_start_time = None

    def capture_image(self, frame, streamName):
        image_name = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + "_" + streamName + ".jpg"
        image_path = os.path.join(self.base_path, image_name)
        cv2.imwrite(image_path, frame)
        return image_path

    def is_recording(self):
        return self.video_out is not None   
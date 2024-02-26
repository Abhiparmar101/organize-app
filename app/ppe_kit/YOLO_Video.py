from ultralytics import YOLO
import cv2
import math

from flask import current_app
import time
from ppe_kit.sort_master.sort import Sort
import numpy as np
import dlib

# Initialize the YOLO model and class names
model = YOLO("models/ppe_kit_det/ppe_kit_det.pt")
classNames = ['Hardhat', 'Mask', 'NO-Hardhat', 'NO-Mask', 'NO-Safety Vest', 'Person', 'Safety Cone',
             'Safety Vest', 'machinery', 'vehicle']

# Initialize the SORT tracker
mot_tracker = Sort()

# Initialize variables for tracking and unique IDs
tracked_persons = {}
next_person_id = 1

def video_detection(path_x, email):
    video_capture = path_x
    cap = cv2.VideoCapture(video_capture)
    frame_width = int(cap.get(3))
    frame_height = int(cap.get(4))

    while True:
        success, img = cap.read()
        results = model(img, stream=True)

        frame_objects = []

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
                    if conf > 0.5:
                        frame_objects.append([x1, y1, x2, y2])

                # Draw bounding boxes and labels
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        if frame_objects:
            # Pass the frame_objects to the SORT tracker
            trackers = mot_tracker.update(np.array(frame_objects))
            
            for d in trackers:
                x1, y1, x2, y2, track_id = d
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                
                if class_name in ['NO-Hardhat', 'NO-Safety Vest', 'NO-Mask']:
                    # Person detected without safety gear
                    if conf > 0.5:
                        email_subject = "Safety Gear Alert"
                        email_body = f"Person detected without safety gear. Image captured."
                        
                        send_email(recipient="jasmita@ambiplatforms.com", subject=email_subject, body=email_body)
                        for person_id, person_data in tracked_persons.items():
                            if not person_data['detected_safety_gear']:
                                # Capture the image
                                person_data['detected_safety_gear'] = True
                                image_filename = f"person_{person_id}_no_safety_gear.jpg"
                                print(f"Capturing image: {image_filename}")  # Debug statement
                                cv2.imwrite(image_filename, img[y1:y2, x1:x2])

        yield img

cv2.destroyAllWindows()
import cv2
import numpy as np
import datetime
import threading  # Import threading for asynchronous API calls
from app.utils.async_api import async_api_call
from app.config import MODEL_BASE_PATH, VIDEO_IMAGE_STORAGE_BASE_PATH
def process_vehicle_detection(frame, model, last_capture_time,streamName,customer_id, cameraId,time_reference,model_name ):
    class_names = ['Car', 'Motorcycle', 'Truck', 'Bus', 'Bicycle']
    # Perform inference
    results = model(frame)
    
    # Extract predictions
    vehicle_detections = results.xyxy[0].cpu().numpy()  # Ensure numpy array and move data to CPU

    # Current counts for this frame
    current_counts = {name: 0 for name in class_names}
    for det in vehicle_detections:
        xmin, ymin, xmax, ymax, conf, class_id = det[:6]
        class_id = int(class_id)
        class_name = results.names[class_id]
        if class_name in class_names:
            current_counts[class_name] += 1
            # Draw bounding boxes manually if results.render() does not work
            color = (0, 255, 0)  # Green color for bounding box
            cv2.rectangle(frame, (int(xmin), int(ymin)), (int(xmax), int(ymax)), color, 2)
            label = f"{class_name} {conf:.2f}"
            cv2.putText(frame, label, (int(xmin), int(ymin-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    

    
    # Display the vehicle counts on the frame
    display_text = ' | '.join(f"{name}: {current_counts[name]}" for name in class_names)
    total_vehicles = sum(current_counts.values())
    display_text += f" | Total: {total_vehicles}"
    cv2.putText(frame, display_text, (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    # Check if it's time to capture the frame
    current_time = datetime.datetime.now()
    if current_time - last_capture_time > datetime.timedelta(minutes=1) and any(current_counts.values()):
        last_capture_time = current_time
        # Save the current frame
        image_name = time_reference.strftime("%Y-%m-%d-%H:%M:%S") + "_" + streamName + ".jpg"
        image_path = VIDEO_IMAGE_STORAGE_BASE_PATH + image_name

        cv2.imwrite(image_path, frame)
        # Call the API asynchronously
        threading.Thread(target=async_api_call, args=(streamName, customer_id, image_name, cameraId, model_name, total_vehicles)).start()
    return frame, last_capture_time

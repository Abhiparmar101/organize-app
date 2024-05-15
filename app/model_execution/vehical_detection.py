import cv2
import numpy as np

def process_vehicle_detection(frame, model):
    class_names = ['Car', 'Motorcycle', 'Truck', 'Bus', 'Bicycle']
    # Perform inference
    results = model(frame)
    
    # Extract predictions
    vehicle_detections = results.xyxy[0]  # detections in xyxy format

    # Current counts for this frame
    current_counts = {name: 0 for name in class_names}
    for det in vehicle_detections:
        class_id = int(det[5])
        class_name = results.names[class_id]
        if class_name in class_names:
            current_counts[class_name] += 1
            # Draw bounding boxes and labels on the frame
            color = (0, 255, 0)  # Green color for the bounding box
            cv2.rectangle(frame, (int(det[0]), int(det[1])), (int(det[2]), int(det[3])), color, 2)
            label = f"{class_name}: {det[4]:.2f}"
            cv2.putText(frame, label, (int(det[0]), int(det[1] - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # Update and display the counts on the frame
    display_text = ' | '.join(f"{name}: {current_counts[name]}" for name in class_names)
    total_vehicles = sum(current_counts.values())
    display_text += f" | Total: {total_vehicles}"
    cv2.putText(frame, display_text, (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)  # Changed color to white for visibility

    return frame

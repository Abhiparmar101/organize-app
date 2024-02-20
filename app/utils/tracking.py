import datetime
import os
import numpy as np




###################################################################################33
# Additional function for creating nested directories
def create_nested_directories(model_name):
    today_date = datetime.datetime.now().strftime("%Y-%m-%d")
    nested_dir_path = os.path.join(os.getcwd(), "history",today_date, model_name)
    if not os.path.exists(nested_dir_path):
        os.makedirs(nested_dir_path)
    return nested_dir_path

class BasicTracker:
    def __init__(self):
        self.objects = {}
        self.id_count = 1

    def update(self, detections):
        new_objects = {}
        for detection in detections:
            x1, y1, x2, y2, conf, cls = detection[:6]
            centroid = np.array([(x1 + x2) / 2, (y1 + y2) / 2])
            # Simple tracking: assign new ID for each detection, in a real scenario you would match these
            new_objects[self.id_count] = {'centroid': centroid, 'bbox': (x1, y1, x2, y2), 'conf': conf, 'cls': cls}
            self.id_count += 1

        # Determine new detections (simplified logic)
        new_ids = set(new_objects.keys()) - set(self.objects.keys())
        self.objects = new_objects  # Update tracked objects
        return new_objects, new_ids
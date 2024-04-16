import cv2
import numpy as np
from ultralytics import YOLO
from ultralytics.utils.plotting import Annotator, colors
from collections import defaultdict

def process_torquev1_tracking(frame, model, track_history):
    results = model.track(frame, persist=True, verbose=False)
    boxes = results[0].boxes.xyxy.cpu()

    if results[0].boxes.id is not None:
        clss = results[0].boxes.cls.cpu().tolist()
        track_ids = results[0].boxes.id.int().cpu().tolist()

        annotator = Annotator(frame, line_width=1)
        for box, cls, track_id in zip(boxes, clss, track_ids):
            annotator.box_label(box, color=colors(int(cls), True), label=model.model.names[int(cls)])
            track = track_history[track_id]
            track.append((int((box[0] + box[2]) / 2), int((box[1] + box[3]) / 2)))
            if len(track) > 30:
                track.pop(0)

            points = np.array(track, dtype=np.int32).reshape((-1, 1, 2))
            cv2.circle(frame, (track[-1]), 2, colors(int(cls), True), -1)
            cv2.polylines(frame, [points], isClosed=False, color=colors(int(cls), True), thickness=1)

    return frame, track_history

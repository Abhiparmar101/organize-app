import cv2
import os
import datetime
import threading
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.utils.async_api import async_api_call
from app.config import MODEL_BASE_PATH, VIDEO_IMAGE_STORAGE_BASE_PATH

# Database setup
DATABASE_URL = "sqlite:///crowd_count.db"  # You can change this to a different database URL if needed
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# Define the CrowdCount model
class CrowdCount(Base):
    __tablename__ = 'crowd_count'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    stream_name = Column(String, nullable=False)
    customer_id = Column(String, nullable=False)
    image_name = Column(String, nullable=False)
    camera_id = Column(String, nullable=False)
    model_name = Column(String, nullable=False)
    personcount = Column(Integer, nullable=False)

# Create the table if it does not exist
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# Define the minimum interval for capturing images
min_interval = datetime.timedelta(seconds=10)

def process_crowd_detection(frame, detections, model_name, time_reference, counter_frame, previous_num_people, last_capture_time, streamName, customer_id, cameraId):
    # Create a new session for this function call
    session = Session()
    
    num_people = 0
    for obj in detections:
        if int(obj[5]) == 0 and obj[4] >= 0.60:  # Check confidence
            xmin, ymin, xmax, ymax = map(int, obj[:4])
            num_people += 1
            cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 0, 255), 1)
            cv2.putText(frame, "person", (xmin, ymin - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)

    time_now = datetime.datetime.now()
    cv2.putText(frame, f'People: {num_people}', (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    if num_people != previous_num_people and (time_now - last_capture_time) > min_interval:
        # Update previous count and last capture time
        previous_num_people = num_people
        last_capture_time = time_now
        image_name = time_now.strftime("%Y-%m-%d-%H:%M:%S") + "_" + streamName + ".jpg"
        image_path = VIDEO_IMAGE_STORAGE_BASE_PATH + image_name

        cv2.imwrite(image_path, frame)
        # Call the API asynchronously
        threading.Thread(target=async_api_call, args=(streamName, customer_id, image_name, cameraId, model_name, num_people)).start()

        # Save to database
        new_entry = CrowdCount(
            timestamp=time_now,
            stream_name=streamName,
            customer_id=customer_id,
            image_name=image_name,
            camera_id=cameraId,
            model_name=model_name,
            personcount=num_people
        )
        session.add(new_entry)
        session.commit()

    # Update frame processing logic
    time_diff = (time_now - time_reference).total_seconds()
    if time_diff >= 1:
        processed_fps = counter_frame
        counter_frame = 0
        time_reference = time_now  # Reset time_reference for FPS calculation
    else:
        counter_frame += 1

    session.close()  # Close the session after use
    return frame, time_reference, counter_frame, previous_num_people, last_capture_time, streamName, customer_id, cameraId

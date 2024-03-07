import datetime


stream_processes = {}
frames_since_last_capture = {}

# Define separate instances for each model
last_capture_time_object_detection = datetime.datetime.now() - datetime.timedelta(seconds=10)
min_interval_object_detection = datetime.timedelta(seconds=10)

last_capture_time_crowd_count = datetime.datetime.now() - datetime.timedelta(seconds=10)
min_interval_crowd_count = datetime.timedelta(seconds=10)

last_capture_time_ppe_kit_det= datetime.datetime.now() - datetime.timedelta(seconds=10)
min_interval_ppe_kit_det = datetime.timedelta(seconds=10)


global_status = {
    "stream_status": "running",  # Default status
}

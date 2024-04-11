
import requests
import logging


def update_camera_status_in_database(camera_id, live_status):
    database_url = "https://backend.ambicam.com/admin/updateLiveStatus"
    logging.info(f"Updating camera status in database for camera ID: {camera_id} to live status: {live_status}")
    print(camera_id, live_status)
    # Convert boolean to a lowercase string if required by the server
    data = {"cameraid": camera_id, "live_status": str(live_status).lower()}
    try:
        response = requests.post(database_url, json=data)
        if response.status_code == 200:
            # Success logging
            logging.info(f"Successfully updated camera status for camera ID: {camera_id}.")
            print("Successfully updated camera status.")
        else:
            logging.error(f"Failed to update camera status for camera ID: {camera_id}. Status Code: {response.status_code}, Response: {response.text}")
            print(f"Failed to update camera status. Status Code: {response.status_code}, Response: {response.text}")
    except Exception as e:
        logging.error(f"Error updating camera status for camera ID: {camera_id}: {e}")
        print(f"Error updating camera status: {e}")
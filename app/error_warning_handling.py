
import requests



def update_camera_status_in_database(camera_id, live_status):
    database_url = "http://192.168.29.151:443/admin/updateLiveStatus"
    print(camera_id, live_status)
    # Convert boolean to a lowercase string if required by the server
    data = {"cameraid": camera_id, "live_status": str(live_status).lower()}
    try:
        response = requests.post(database_url, json=data)
        if response.status_code == 200:
            print("Successfully updated camera status.")
        else:
            print(f"Failed to update camera status. Status Code: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"Error updating camera status: {e}")
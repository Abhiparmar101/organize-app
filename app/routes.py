from flask import request, jsonify
import re
import threading
from .utils.video_streaming import  process_and_stream_frames
import os
from app.config import MODEL_BASE_PATH
from app.utils.globals import stream_processes
from werkzeug.utils import secure_filename
import logging
import json
import tailer
import requests
import time
logging.basicConfig(filename='logs/video_streaming.log', filemode='a', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#######################################################

# def save_stream_parameters(stream_key, data):
#     """Append the stream parameters and stream_key to a JSON file."""
#     try:
#         # Attempt to read the existing data
#         with open('stream_parameters.json', 'r') as file:
#             all_stream_data = json.load(file)
#     except (FileNotFoundError, json.JSONDecodeError):
#         # If the file doesn't exist or is empty/corrupt, start fresh
#         all_stream_data = {}

#     # Update the data with the new stream
#     all_stream_data[stream_key] = data  # Assign the new data under its stream_key

#     # Write the updated data back to the file
#     with open('stream_parameters.json', 'w') as file:
#         json.dump(all_stream_data, file, indent=4)

def save_stream_parameters(stream_key, data, retrying=False):
    try:
        with open('stream_parameters.json', 'r+') as file:
            all_stream_data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        all_stream_data = {}
    
    data['retrying'] = retrying  # Add retrying status to the data
    all_stream_data[stream_key] = data

    with open('stream_parameters.json', 'w') as file:
        json.dump(all_stream_data, file, indent=4)

def get_api_parameters(stream_key):
    """Retrieve the API parameters for a specific stream key."""
    try:
        with open("/home/torqueai/gituhub/organize-app/stream_parameters.json", 'r') as file:
            all_stream_data = json.load(file)
            return all_stream_data.get(stream_key)
    except FileNotFoundError:
        return None

def trigger_api_call(api_parameters):
    """Trigger the /set_model API call with the provided parameters."""
    
    url = "https://192.168.29.32:5000/set_model"
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, json=api_parameters, headers=headers, verify=False)  # Skipping SSL verification for example
    print(f"API Call Triggered: Status Code {response.status_code}, Response: {response.text}")
   

# def monitor_log_and_trigger_api():
#     for line in tailer.follow(open("/home/torqueai/gituhub/organize-app/logs/video_streaming.log")):
#         if "Stream terminated:" in line or "Failed to read from camera" in line:
#             # Extract the stream URL from the log line
#             stream_url = line.split(": ")[-1].strip()
#             # Generate the stream_key from the URL (ensure this matches the logic used when saving the parameters)
#             # This is a simplified example; adjust the logic to accurately generate the stream_key from the stream_url
#             stream_key = stream_url  # Assuming the stream_key is the last part of the URL

#             api_parameters = get_api_parameters(stream_key)
#             if api_parameters:
#                 print(f"Retrying stream for {stream_key}")
#                 trigger_api_call(api_parameters)
#             else:
#                 print(f"No parameters found for stream_key: {stream_key}")
import time

def monitor_log_and_trigger_api():
  
        for line in tailer.follow(open("/home/torqueai/gituhub/organize-app/logs/video_streaming.log")):
            if "Stream terminated" in line or  "Failed to read from camera" in line:
                stream_url = line.split(": ")[-1].strip()
                stream_key = stream_url  # Assuming stream_key can be derived directly

                # Trigger retry if not already retrying
                try:
                    with open('stream_parameters.json', 'r+') as file:
                        all_stream_data = json.load(file)
                        if stream_key in all_stream_data and not all_stream_data[stream_key].get('retrying', False):
                            print(f"Detected stream failure, attempting to reconnect for {stream_key}")
                            time.sleep(180)
                            trigger_api_call(all_stream_data[stream_key])
                            all_stream_data[stream_key]['retrying'] = True

                            # Save updated status back to file
                            file.seek(0)
                            json.dump(all_stream_data, file, indent=4)
                            file.truncate()  # Ensure file size is adjusted

                            # Wait for a while before retrying to avoid hammering the server
                          
                except FileNotFoundError:
                    print(f"No parameters found for stream_key: {stream_key}")

            elif "Successfully received camera frame" in line:
                stream_url = line.split(": ")[-1].strip()
                stream_key = stream_url

                # Mark stream as successfully receiving frames
                try:
                    with open('stream_parameters.json', 'r+') as file:
                        all_stream_data = json.load(file)
                        if stream_key in all_stream_data and all_stream_data[stream_key].get('retrying', False):
                            print(f"Successfully reconnected for {stream_key}.")
                            all_stream_data[stream_key]['retrying'] = False

                            file.seek(0)
                            json.dump(all_stream_data, file, indent=4)
                            file.truncate()
                except FileNotFoundError:
                    print(f"No stream parameters file found.")

        # Adjust the frequency of log checks to balance responsiveness with resource usage
        time.sleep(1)


   
def get_stream_parameters():
    """Retrieve the last stream parameters from a JSON file."""
    try:
        with open('stream_parameters.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
def configure_routes(app):
    @app.route('/stop_stream', methods=['POST'])
    def stop_stream():
        data = request.get_json()
        stream_key = data.get('stream_key')

        if not stream_key:
            logging.warning("Attempt to stop stream without specifying stream_key")
            return jsonify({'error': 'Stream key is required'}), 400

        # Safely stop the stream if it exists
        if stream_key in stream_processes:
            process = stream_processes[stream_key]
            process.terminate()  # Terminate the FFmpeg process
            process.wait()  # Optional: Wait for the process to terminate
            del stream_processes[stream_key]  # Remove the process from the dictionary
            logging.info(f"Stream stopped successfully for stream_key: {stream_key}")
            return jsonify({'message': 'Streaming stopped successfully'})
        else:
            logging.error(f"Failed to stop stream: Stream not found for stream_key: {stream_key}")
            return jsonify({'error': 'Stream not found'}), 404
        


    @app.route('/set_model', methods=['POST'])
    def set_model_and_stream():
        global stream_process
        data = request.get_json()
        model_name = data.get('model_name')
        camera_url = data.get('camera_url')
        customer_id = data.get('customer_id')
        cameraId = data.get('cameraId')
        stream_name = data.get('streamName')
        if not model_name or not camera_url:
            logging.warning("set_model_and_stream called without model_name or camera_url")
            return jsonify({'error': 'Both model name and camera URL are required'}), 400
        # Replace "media" with "media5" and "dvr" with digits to "live"
        modified_url = re.sub(r'media\d*', 'media5', camera_url)
        modified_url = re.sub(r'dvr\d+', 'live', modified_url)
        
        # Append the model name at the end of the URL, after a slash
        modified_url_with_model = f"{modified_url}_{model_name}"
        print("mooo",modified_url_with_model)
        print("cameraaaaa",cameraId)
        # Unique key to identify the stream (could be refined based on requirements)
        stream_key = modified_url_with_model
        # Save the current parameters for potential future retries
        # In your set_model_and_stream endpoint, adjust the save_stream_parameters call
        save_stream_parameters(stream_key, {
            "model_name": model_name,
            "camera_url": camera_url,
            "customer_id": customer_id,
            "cameraId": cameraId,
            "streamName": stream_name
        })

        # Check if a stream with the same key is already running, terminate if so
        if stream_key in stream_processes:
            stream_processes[stream_key].terminate()
            del stream_processes[stream_key]

        # Start a new stream
        thread = threading.Thread(target=process_and_stream_frames, args=(model_name, camera_url, stream_key,customer_id,cameraId,stream_name))
        thread.start()
        logging.info(f"Streaming started for model_name: {model_name}, camera_url: {camera_url}")
        return jsonify({'message': 'Streaming started', 'rtmp_url':stream_key,'customer_id':customer_id,'cameraId':cameraId,'streamName':stream_name})
    
    

    @app.route('/running_streams', methods=['GET'])
    def get_running_streams():
        # Collect all the stream keys representing the RTMP URLs of running streams
        running_streams = list(stream_processes.keys())
        return jsonify({'running_streams': running_streams})

    ################# model list
    @app.route('/get_models', methods=['GET'])
    def get_models():
        models_dir = MODEL_BASE_PATH
        try:
            # List all files in the models directory
            files = os.listdir(models_dir)
            # Filter out files to only include .pt files
            model_files = [file for file in files if file.endswith('.pt')]
            return jsonify({'models': model_files}), 200
        except Exception as e:
            # Handle errors, such as if the directory does not exist
            return jsonify({'error': str(e)}), 500

    #####upload
    ALLOWED_EXTENSIONS = {'pt'}

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    @app.route('/upload_model', methods=['POST'])
    def upload_model():
        if 'model' not in request.files:
            return jsonify({'error': 'No model file part'}), 400
        file = request.files['model']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(MODEL_BASE_PATH, filename))
            logging.info(f"Model uploaded successfully: {filename}")
            return jsonify({'message': 'Model uploaded successfully'}), 200
        else:
            logging.error(f"Model upload failed: Invalid file type. Only .pt files are allowed")

            return jsonify({'error': 'Invalid file type. Only .pt files are allowed'}), 400
        
    #############rename
    @app.route('/rename_model', methods=['POST'])
    def rename_model():
        data = request.get_json()
        old_name = data.get('old_name')
        new_name = data.get('new_name')
        old_path = os.path.join(MODEL_BASE_PATH, old_name)
        new_path = os.path.join(MODEL_BASE_PATH, new_name)
        if not os.path.exists(old_path):
            return jsonify({'error': 'Old model does not exist'}), 404
        if os.path.exists(new_path):
            return jsonify({'error': 'New model name already exists'}), 409
        os.rename(old_path, new_path)
        return jsonify({'message': 'Model renamed successfully'}), 200
    #########delet
    @app.route('/delete_model', methods=['POST'])
    def delete_model():
        data = request.get_json()
        model_name = data.get('model_name')
        model_path = os.path.join(MODEL_BASE_PATH, model_name)
        if not os.path.exists(model_path):
            return jsonify({'error': 'Model does not exist'}), 404
        os.remove(model_path)
        return jsonify({'message': 'Model deleted successfully'}), 200
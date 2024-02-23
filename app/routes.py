from flask import request, jsonify
import re
import threading
from .utils.video_streaming import  process_and_stream_frames
import os
from app.config import MODEL_BASE_PATH
from app.utils.globals import stream_processes
from werkzeug.utils import secure_filename




#######################################################
def configure_routes(app):
    @app.route('/stop_stream', methods=['POST'])
    def stop_stream():
        data = request.get_json()
        stream_key = data.get('stream_key')

        if not stream_key:
            return jsonify({'error': 'Stream key is required'}), 400

        # Safely stop the stream if it exists
        if stream_key in stream_processes:
            process = stream_processes[stream_key]
            process.terminate()  # Terminate the FFmpeg process
            process.wait()  # Optional: Wait for the process to terminate
            del stream_processes[stream_key]  # Remove the process from the dictionary
            return jsonify({'message': 'Streaming stopped successfully'})
        else:
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
        
        # Check if a stream with the same key is already running, terminate if so
        if stream_key in stream_processes:
            stream_processes[stream_key].terminate()
            del stream_processes[stream_key]

        # Start a new stream
        thread = threading.Thread(target=process_and_stream_frames, args=(model_name, camera_url, stream_key,customer_id,cameraId,stream_name))
        thread.start()

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
            return jsonify({'message': 'Model uploaded successfully'}), 200
        else:
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
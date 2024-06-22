from flask import Flask, request, jsonify
import re
import threading
import os
import logging
import json
import tailer
import requests
import time
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
from werkzeug.utils import secure_filename
from .utils.video_streaming import process_and_stream_frames
from .utils.retrian_model.crowd_retrain_dataset_formation import DatasetProcessor
from app.config import MODEL_BASE_PATH
from app.utils.globals import stream_processes
from app.utils.async_api import async_api_call
import signal
import sys
import requests
import certifi
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

os.environ['OPENCV_FFMPEG_READ_ATTEMPTS'] = '50000000'

# Logging setup
logging.basicConfig(filename='logs/video_streaming.log', filemode='a', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database setup
DATABASE_URL = "sqlite:///stream_parameters.db"
engine = create_engine(DATABASE_URL)
Base = declarative_base()
Session = sessionmaker(bind=engine)


# Define the StreamParameter model
class StreamParameter(Base):
    __tablename__ = 'stream_parameters'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    stream_key = Column(String, unique=True, nullable=False)
    model_name = Column(String, nullable=False)
    camera_url = Column(String, nullable=False)
    customer_id = Column(String, nullable=False)
    camera_id = Column(String, nullable=False)
    stream_name = Column(String, nullable=False)
    status = Column(Boolean, default=True)  # True if running, False if stopped
    retrying = Column(Boolean, default=False)
    aistreamkey = Column(String, nullable=False)


# Create the table if it does not exist
Base.metadata.create_all(engine)


# Function to extract aistreamkey from stream_key
def extract_aistreamkey(stream_key):
    match = re.search(r'live/([^_]+_[^_]+)', stream_key)
    if match:
        return match.group(1)
    return ''


# Function to save stream parameters to the database
def save_stream_parameters(stream_key, data, retrying=False):
    session = Session()
    try:
        aistreamkey = extract_aistreamkey(stream_key)  # Extract the value for aistreamkey
        stream_param = session.query(StreamParameter).filter_by(stream_key=stream_key).first()
        if stream_param:
            stream_param.model_name = data['model_name']
            stream_param.camera_url = data['camera_url']
            stream_param.customer_id = data['customer_id']
            stream_param.camera_id = data['cameraId']
            stream_param.stream_name = data['streamName']
            stream_param.retrying = retrying
            stream_param.status = True  # Mark as running
            stream_param.aistreamkey = aistreamkey
        else:
            stream_param = StreamParameter(
                stream_key=stream_key,
                model_name=data['model_name'],
                camera_url=data['camera_url'],
                customer_id=data['customer_id'],
                camera_id=data['cameraId'],
                stream_name=data['streamName'],
                retrying=retrying,
                status=True,  # Mark as running
                aistreamkey=aistreamkey
            )
            session.add(stream_param)
        session.commit()
    except Exception as e:
        print(f"Error saving stream parameters: {e}")
        session.rollback()
    finally:
        session.close()


def update_stream_status(camera_id, status):
    session = Session()
    try:
        stream_param = session.query(StreamParameter).filter_by(camera_id=camera_id).first()
        if stream_param:
            stream_param.status = status
            session.commit()
    except Exception as e:
        print(f"Error updating stream status for camera_id {camera_id}: {e}")
        session.rollback()
    finally:
        session.close()


def trigger_api_call(api_parameters):
    url = "https://192.168.1.8:6000/set_model"
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, json=api_parameters, headers=headers, verify=False)  # Skipping SSL verification for example
        print(f"API Call Triggered: Status Code {response.status_code}, Response: {response.text}")

        if response.status_code == 404 and "AiCamera not found" in response.text:
            update_stream_status(api_parameters['cameraId'], False)

    except requests.exceptions.RequestException as e:
        print(f"Error sending data to API: {e}")
        update_stream_status(api_parameters['cameraId'], False)


def fetch_api_streams():
    api_url = "https://media5.ambicam.com/api/streams"
    cert_path = ("/home/torqueai/github/organize-app/ambicam.crt", "/home/torqueai/github/organize-app/ambicam.key")
    try:
        response = requests.get(api_url, cert=cert_path, verify=False)
        response.raise_for_status()
        streams = response.json()
        print(f"API Response: {streams}")  # Print the API response for debugging
        return streams
    except requests.exceptions.RequestException as e:
        print(f"Error fetching stream data from API: {e}")
        return []


def check_and_update_stream_status():
    session = Session()
    try:
        api_streams = fetch_api_streams()
        if isinstance(api_streams, list):  # Ensure that the response is a list
            api_stream_keys = {stream['name'] for stream in api_streams}

            streams_to_update = session.query(StreamParameter).all()

            for stream in streams_to_update:
                stream.status = stream.aistreamkey in api_stream_keys

            session.commit()
            print(f"Updated stream statuses based on API data at {datetime.datetime.utcnow()}")
        else:
            print("API response is not a list, cannot update statuses.")
    except Exception as e:
        print(f"Error updating stream statuses: {e}")
        session.rollback()
    finally:
        session.close()


def periodic_stream_check(interval=60):
    while True:
        check_and_update_stream_status()
        time.sleep(interval)


def monitor_log_and_trigger_api():
    session = Session()
    try:
        with open("logs/video_streaming.log") as log_file:
            for line in tailer.follow(log_file):
                if "Stream timeout triggered" in line or "Broken pipe" in line or "AiCamera not found" in line:
                    camera_id = extract_camera_id_from_log(line)
                    if camera_id:
                        update_stream_status(camera_id, False)
                        trigger_api_call(get_api_parameters(camera_id))

                if "Successfully received camera frame" in line:
                    camera_id = extract_camera_id_from_log(line)
                    if camera_id:
                        update_stream_status(camera_id, True)
                time.sleep(1)
    except Exception as e:
        print(f"Error monitoring logs: {e}")
    finally:
        session.close()


def restart_closed_streams(interval=60):
    while True:
        session = Session()
        try:
            closed_streams = session.query(StreamParameter).filter_by(status=False).all()
            for stream in closed_streams:
                print(f"Restarting stream: {stream.stream_key}")
                stream.status = True
                thread = threading.Thread(target=process_and_stream_frames, args=(stream.model_name, stream.camera_url, stream.stream_key, stream.customer_id, stream.camera_id, stream.stream_name))
                thread.start()
                session.commit()
        except Exception as e:
            print(f"Error restarting closed streams: {e}")
            session.rollback()
        finally:
            session.close()
        time.sleep(interval)


def signal_handler(sig, frame):
    print("Caught Ctrl+C, updating stream status and exiting.")
    session = Session()
    try:
        streams = session.query(StreamParameter).filter_by(status=True).all()
        for stream in streams:
            stream.status = False
        session.commit()
    except Exception as e:
        print(f"Error updating stream status: {e}")
        session.rollback()
    finally:
        session.close()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def configure_routes(app):
    @app.route('/stop_stream', methods=['POST'])
    def stop_stream():
        data = request.get_json()
        stream_key = data.get('stream_key')

        if not stream_key:
            logging.warning("Attempt to stop stream without specifying stream_key")
            return jsonify({'error': 'Stream key is required'}), 400

        session = Session()
        try:
            if stream_key in stream_processes:
                process = stream_processes[stream_key]
                process.terminate()  # Terminate the FFmpeg process
                process.wait()  # Optional: Wait for the process to terminate
                del stream_processes[stream_key]  # Remove the process from the dictionary
                logging.info(f"Stream stopped successfully for stream_key: {stream_key}")

                stream_param = session.query(StreamParameter).filter_by(stream_key=stream_key).first()
                if stream_param:
                    stream_param.status = False  # Mark as stopped
                    session.commit()

                return jsonify({'message': 'Streaming stopped successfully'})
            else:
                logging.error(f"Failed to stop stream: Stream not found for stream_key: {stream_key}")
                return jsonify({'error': 'Stream not found'}), 404
        except Exception as e:
            print(f"Error stopping stream: {e}")
            session.rollback()
            return jsonify({'error': 'Internal server error'}), 500
        finally:
            session.close()

    @app.route('/set_model', methods=['POST'])
    def set_model_and_stream():
        data = request.get_json()
        model_name = data.get('model_name')
        camera_url = data.get('camera_url')
        customer_id = data.get('customer_id')
        cameraId = data.get('cameraId')
        stream_name = data.get('streamName')

        if not model_name or not camera_url:
            logging.warning("set_model_and_stream called without model_name or camera_url")
            return jsonify({'error': 'Both model name and camera URL are required'}), 400

        modified_url = re.sub(r'media\d*', 'media5', camera_url)
        modified_url = re.sub(r'dvr\d+', 'live', modified_url)
        modified_url_with_model = f"{modified_url}_{model_name}"
        stream_key = modified_url_with_model

        save_stream_parameters(stream_key, {
            "model_name": model_name,
            "camera_url": camera_url,
            "customer_id": customer_id,
            "cameraId": cameraId,
            "streamName": stream_name
        })

        if stream_key in stream_processes:
            stream_processes[stream_key].terminate()
            del stream_processes[stream_key]

        thread = threading.Thread(target=process_and_stream_frames, args=(model_name, camera_url, stream_key, customer_id, cameraId, stream_name))
        thread.start()
        logging.info(f"Streaming started for model_name: {model_name}, camera_url: {camera_url}")
        return jsonify({'message': 'Streaming started', 'rtmp_url': stream_key, 'customer_id': customer_id, 'cameraId': cameraId, 'streamName': stream_name})

    @app.route('/running_streams', methods=['GET'])
    def get_running_streams():
        running_streams = list(stream_processes.keys())
        return jsonify({'running_streams': running_streams})

    @app.route('/get_models', methods=['GET'])
    def get_models():
        models_dir = MODEL_BASE_PATH
        try:
            files = os.listdir(models_dir)
            model_files = [file for file in files if file.endswith('.pt')]
            return jsonify({'models': model_files}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/get_retrain_models', methods=['POST'])
    def get_retrain_models():
        data = request.get_json()
        customer_id = data.get('customer_id')
        if not customer_id:
            return jsonify({"error": "Customer ID is required"}), 400

        models_list = fetch_models_for_customer(customer_id)
        return jsonify(models_list)

    def fetch_models_for_customer(customer_id):
        base_path = Path(os.getcwd() + "/blobdrive/")
        customer_path = base_path / customer_id / "retrain_models"
        if not customer_path.exists():
            return {"error": f"No models found for customer ID {customer_id}"}

        model_files = [file.name for file in customer_path.glob('*.pt')]
        return {"models": model_files}

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

    @app.route('/delete_model', methods=['POST'])
    def delete_model():
        data = request.get_json()
        model_name = data.get('model_name')
        model_path = os.path.join(MODEL_BASE_PATH, model_name)
        if not os.path.exists(model_path):
            return jsonify({'error': 'Model does not exist'}), 404
        os.remove(model_path)
        return jsonify({'message': 'Model deleted successfully'}), 200

    @app.route('/process_dataset', methods=['POST'])
    def process_dataset():
        data = request.get_json()
        model_name = data.get('model_name')
        image_dir = data.get('image_dir')
        customer_id = data.get('customer_id')
        image_path = os.path.join(os.getcwd() + "/blobdrive/", image_dir)

        model_configs = {
            'crowd': {'number_of_classes': 2, 'labels': ['person', 'head']},
            'vehicle_detection': {'number_of_classes': 5, 'labels': ['Car', 'Motorcycle', 'Truck', 'Bus', 'Bicycle']}
        }

        if model_name in model_configs:
            config = model_configs[model_name]
            processor = DatasetProcessor(model_name, os.getcwd() + '/blobdrive/', customer_id)
            processor.process_dataset(image_path, config['labels'], config['number_of_classes'])
            return jsonify({'message': f'{model_name} model processed successfully'}), 200
        else:
            return jsonify({'error': f'Model {model_name} not supported'}), 400


def extract_camera_id_from_log(log_line):
    log_parts = log_line.split()
    camera_id_index = -2  # Assuming the camera ID is the second last part of the line
    return log_parts[camera_id_index] if len(log_parts) > camera_id_index else None


def get_api_parameters(camera_id):
    session = Session()
    try:
        stream_param = session.query(StreamParameter).filter_by(camera_id=camera_id).first()
        if stream_param:
            return {
                "model_name": stream_param.model_name,
                "camera_url": stream_param.camera_url,
                "customer_id": stream_param.customer_id,
                "cameraId": stream_param.camera_id,
                "streamName": stream_param.stream_name
            }
    finally:
        session.close()
    return None
threading.Thread(target=monitor_log_and_trigger_api, daemon=True).start()
threading.Thread(target=periodic_stream_check, daemon=True).start()
threading.Thread(target=restart_closed_streams, daemon=True).start()

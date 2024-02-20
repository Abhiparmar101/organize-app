
from flask import Flask, jsonify, request
from werkzeug.utils import secure_filename
from app.config import MODEL_BASE_PATH
from run import app
import os
############# Model upload ,delete,rename ###############
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
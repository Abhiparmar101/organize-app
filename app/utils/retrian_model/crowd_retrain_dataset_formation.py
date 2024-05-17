import torch
import cv2
from pathlib import Path
import os, random
import shutil
import glob
import subprocess
import datetime
import re
from shutil import copy2
class DatasetProcessor:
    def __init__(self, model_name, base_path,customer_id):
        self.model_name = model_name
        self.base_path = Path(base_path)
        self.default_model_path = self.base_path/f'm' / f'{model_name}.pt'
        self.model = self.load_model()
        self.customer_id=customer_id

    def load_model(self):
        # Assuming torch.hub.load returns a loaded model
        return   torch.hub.load('yolov5', 'custom', path=self.default_model_path, source='local', force_reload=True)

    def process_dataset(self, image_dir, label):
        try:
            output_dir = self.setup_directories(self.customer_id,image_dir)
            self.process_images(image_dir, output_dir)
            print(output_dir)
            self.split(output_dir)
            self.start_training(output_dir)
        except Exception as e:
            print(f"Cannot start training due to an error in the process: {e}")   

    def setup_directories(self, customer_id,image_dir):
        print("--------create the directories------")
        output_dir = Path(str(image_dir)) # Convert string path to Path object if not already
        
        output_dir.mkdir(parents=True, exist_ok=True)  # Ensure the base directory exists

        # Create subdirectories using the / operator for Path objects
        (self.base_path/f'{customer_id}'/ "retrain_models").mkdir(parents=True, exist_ok=True)
        (output_dir / "data").mkdir(parents=True, exist_ok=True)
        (output_dir / "data" / "images").mkdir(parents=True, exist_ok=True)
        (output_dir / "data" / "labels").mkdir(parents=True, exist_ok=True)
        (output_dir / "data" / "images" / "train").mkdir(parents=True, exist_ok=True)
        (output_dir / "data" / "images" / "valid").mkdir(parents=True, exist_ok=True)
        (output_dir / "data" / "labels" / "train").mkdir(parents=True, exist_ok=True)
        (output_dir / "data" / "labels" / "valid").mkdir(parents=True, exist_ok=True)
        with (output_dir / "data" / 'data.yaml').open('w') as data:
            data.write(f'train: {output_dir}/data/images/train\n')
            data.write(f'val: {output_dir}/data/images/valid\n')
            data.write('\nnc: 2\n')
            data.write("names: ['person', 'head']\n")  # List of class names
            data.write('SAVE_VALID_PREDICTION_IMAGES: True\n')
        print("-------- directories is completed------")
        
        return output_dir

    def process_images(self, image_dir, output_dir):
        print("-------------images is processing-------------")
        image_dir = Path(image_dir)
        output_dir = Path(output_dir)
        print( image_dir,",,,",output_dir)
        for image_path in image_dir.rglob('*.jpg'):
            image = cv2.imread(str(image_path))
            if image is None:
                print(f"Failed to load image {image_path}")
                continue
            results = self.model(image)
            results.print()
            bbox_results = results.pandas().xyxy[0]
            height, width = image.shape[:2]
            with (output_dir / f'{image_path.stem}.txt').open('w') as f:
                for index, row in bbox_results.iterrows():
                    x_center = ((row['xmin'] + row['xmax']) / 2) / width
                    y_center = ((row['ymin'] + row['ymax']) / 2) / height
                    bbox_width = (row['xmax'] - row['xmin']) / width
                    bbox_height = (row['ymax'] - row['ymin']) / height
                    f.write(f"{int(row['class'])} {x_center} {y_center} {bbox_width} {bbox_height}\n")
            print(f"Annotations for {image_path.name} saved to {image_path.stem}.txt")
            print("-------------successfully completed image processing-------------")
        # DatasetProcessor.split(output_dir)

    def split(self,output_dir):
        print("--------dataset is formating-----")
        percentage_test = 20
        p = percentage_test / 100
        output_dir = Path(output_dir)
        for pathAndFilename in glob.iglob(str(output_dir / "*.jpg")):
            title, ext = os.path.splitext(os.path.basename(pathAndFilename))
            if random.random() <= p:
                shutil.copy(pathAndFilename, output_dir / "data/images/train")
                shutil.copy(str(output_dir / f"{title}.txt"), output_dir / "data/labels/train")
            else:
                shutil.copy(pathAndFilename, output_dir / "data/images/valid")
                shutil.copy(str(output_dir / f"{title}.txt"), output_dir / "data/labels/valid")
        print("---------dataset is formated successfully-------- ")
    def fetch_latest_model(self):
        """Fetch the latest version model if available, otherwise use the default model."""
        model_dir =  Path(self.base_path) / self.customer_id/ 'retrain_models'
        model_files = list(model_dir.glob(f'{self.model_name}_v*.pt'))
        if model_files:
            # Extract version numbers and sort files by version
            model_files.sort(key=lambda x: int(re.search(r'_v(\d+)\.pt$', x.name).group(1)), reverse=True)
            latest_model_path = model_files[0]  # Get the most recent version
            print(f"Using latest model version: {latest_model_path}")
            return latest_model_path
        else:
            # If no models are found, return the default model path
            print(f"No retrained models found. Using default model: {self.default_model_path}")
            return self.default_model_path
    def start_training(self,output_dir):
        data_yaml=os.path.join(output_dir,'data/data.yaml')
        current_datetime=datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        retrain_model_name= self.customer_id +"_"+self.model_name+ "_"+current_datetime
        pretrain_model_weight=self.fetch_latest_model()
        command = [
            'python3', os.path.join(os.getcwd(),"yolov5/train.py"),
            '--img', '640',
            '--batch', '16',
            '--epochs', '5',
            '--data',data_yaml,
            
            '--weights',pretrain_model_weight,
            '--name',retrain_model_name
        ]
        
        try:
            result = subprocess.run(command, check=True, text=True, capture_output=True)
            print("Training completed successfully.")
            self.move_model(os.path.join(os.getcwd(),"yolov5/runs/train",retrain_model_name))
            print("Output:", retrain_model_name)
        except subprocess.CalledProcessError as e:
            print("Error during training:", e)
            print("Output:", e.stderr)
            
    def move_model(self, source_directory):
        # target_directory = Path(self.base_path) / self.customer_id/ 'retrain_models'
        # target_directory.mkdir(parents=True, exist_ok=True)  # Create target directory if it doesn't exist
        target_directory = Path(self.base_path) / 'm'
        target_directory.mkdir(parents=True, exist_ok=True)  # Create target directory if it doesn't exist
        latest_version = self.get_latest_model_version(target_directory)
        new_version = f"{self.model_name}_v{latest_version + 1}.pt"  # Increment model version
        
        # Find the latest trained model
        source_model_path = self.find_latest_model_file(source_directory)
        if source_model_path:
            destination_model_path = target_directory / new_version
            copy2(source_model_path, destination_model_path)  # Copy and keep metadata
            print(f"Model moved successfully to {destination_model_path}")
        else:
            print("No model file found to move.")

    def get_latest_model_version(self, directory):
        """Get the latest version number from the models in the directory."""
        version_numbers = []
        for model_file in directory.glob(self.model_name + '_v*.pt'):
            # Extract version number from filenames like 'crowd_v10.pt'
            part = model_file.stem.split('_v')[-1]
            if part.isdigit():
                version_numbers.append(int(part))
        return max(version_numbers, default=0)  # Return 0 if no files found

    def find_latest_model_file(self, directory):
        """Find the latest model file based on modification time."""
        directory = Path(directory)
        models = list(directory.glob('**/*.pt'))  # Change pattern if necessary
        if not models:
            return None
        latest_model = max(models, key=lambda x: x.stat().st_mtime)
        return latest_model


    
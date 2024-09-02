from flask import Flask, request, jsonify, render_template
from flask_mongoengine import MongoEngine
from werkzeug.utils import secure_filename
from PIL import Image
import os
import uuid
import requests
import csv
from datetime import datetime
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from celery import Celery

# Initialize Flask app
app = Flask(__name__)

# MongoDB connection URI
uri = <enter_your_mongo_uri_here>

# MongoEngine configuration
app.config['MONGODB_SETTINGS'] = {
    'host': uri,
    'server_api': ServerApi('1')  # Optional, specifies server API version
}

# Initialize MongoEngine
db = MongoEngine(app)

# Celery configuration for asynchronous task processing
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

# Configurations for file upload
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# Test MongoDB connection
try:
    client = MongoClient(uri, server_api=ServerApi('1'))
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")

# Define the ProcessedImage model
class ProcessedImage(db.Document):
    request_id = db.StringField(required=True)
    serial_number = db.StringField(max_length=20)
    product_name = db.StringField(max_length=100)
    image_path = db.StringField(max_length=200)
    processed_image_path = db.StringField(max_length=200)
    created_at = db.DateTimeField(default=datetime.utcnow)
    updated_at = db.DateTimeField(default=datetime.utcnow)
    status = db.StringField(default="Pending")
    meta = {
        'collection': 'processed_images'
    }

# Function to process images (reduce size by 50%)
def process_image(image_path):
    img = Image.open(image_path)
    img = img.resize((img.width // 2, img.height // 2))  # Reduce size by 50%
    
    processed_filename = f"processed_{os.path.basename(image_path)}"
    processed_image_path = os.path.join(app.config['PROCESSED_FOLDER'], processed_filename)
    img.save(processed_image_path)

    return processed_image_path

@celery.task
def process_images_async(request_id, csv_file_path):
    with open(csv_file_path, 'r') as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            serial_number = row['S.No.']
            product_name = row['Product Name']
            input_urls = row['Input Image Urls'].split(',')

            output_urls = []
            for url in input_urls:
                # Download the image
                image_response = requests.get(url)
                input_image_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f"{uuid.uuid4()}.jpg"))
                with open(input_image_path, 'wb') as img_file:
                    img_file.write(image_response.content)

                # Process the image
                processed_image_path = process_image(input_image_path)

                # Save to MongoDB
                processed_image = ProcessedImage.objects(request_id=request_id).first()
                processed_image.update(
                    serial_number=serial_number,
                    product_name=product_name,
                    image_path=input_image_path,
                    processed_image_path=processed_image_path,
                    updated_at=datetime.utcnow(),
                    status="Completed"
                )

                output_urls.append(processed_image_path)

# Route to upload images and save metadata
@app.route('/upload', methods=['POST'])
def upload_image():
    if 'csv_file' not in request.files:
        return jsonify({"error": "No CSV file part in the request"}), 400

    csv_file = request.files['csv_file']
    
    if csv_file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    csv_file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(csv_file.filename))
    csv_file.save(csv_file_path)

    request_id = 'req_' + str(uuid.uuid4())
    ProcessedImage(
        request_id=request_id,
        status="Processing"
    ).save()

    process_images_async.delay(request_id, csv_file_path)

    return jsonify({"message": "CSV file uploaded successfully", "request_id": request_id}), 201

# Route to check processing status
@app.route('/status/<request_id>', methods=['GET'])
def check_status(request_id):
    processed_image = ProcessedImage.objects(request_id=request_id).first()

    if not processed_image:
        return jsonify({"error": "No data found for the given request ID"}), 404

    return jsonify({"request_id": request_id, "status": processed_image.status}), 200

# Route to fetch image data based on request ID
@app.route('/fetch/<request_id>', methods=['GET'])
def fetch_image(request_id):
    processed_images = ProcessedImage.objects(request_id=request_id)

    if not processed_images:
        return jsonify({"error": "No data found for the given request ID"}), 404

    response_data = []
    for image in processed_images:
        response_data.append({
            "serial_number": image.serial_number,
            "product_name": image.product_name,
            "image_path": image.image_path,
            "processed_image_path": image.processed_image_path,
            "created_at": image.created_at,
            "updated_at": image.updated_at
        })

    return jsonify(response_data), 200

# Serve the frontend
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)

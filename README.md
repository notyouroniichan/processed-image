# Getting started :
* Start Redis : In your terminal run the command
  ```
  redis-server
  ```
* Start Celery worker : In another terminal navigate to your project folder and run the command
  ```
  celery -A app.celery worker --loglevel=info
  ```
* Start Flask app : In your another terminal(third) navigate to your project folder and run the command
  ```
  flask run
  ```
This will run the project and a very basic frontend will be availbale at ``` http://127.0.0.1:5000 ```

## Key Features:
* Image Processing: The process_image function reduces the image size by 50% and saves the processed image in a local folder (processed).
* CSV Handling: The ```/upload``` route accepts a CSV file, processes the images, and generates a new CSV file containing the output image URLs.
* MongoDB Storage: Metadata, including the processed image paths and timestamps for creation and updates, is stored in MongoDB.
* Fetching Data: The ```/fetch/<request_id>``` route allows retrieving the image processing details based on the request_id.

## Documentation : 
#### Function Summaries :
* ```process_image(image_path)```:
      Resizes the input image to 50% of its original dimensions and saves it in the 'processed' directory. The function returns the file path of the processed image.
* ```process_images_async(request_id, csv_file_path)```:
      An asynchronous task that processes images listed in a CSV file. It downloads each image, resizes it using process_image, and updates the MongoDB document with the processed image paths.
* ```upload_image()```:
      Handles the upload of a CSV file containing image URLs. The file is saved, a unique request ID is generated, and an asynchronous image processing task is initiated. Returns the request ID.
* ```check_status(request_id)```:
      Retrieves the processing status of the images associated with the provided request ID from the MongoDB collection and returns it as JSON.
* ```fetch_image(request_id)``` :
      Fetches and returns details of the processed images, including paths and timestamps, for a given request ID.
* ```index()```:
      Serves the HTML template for the frontend, providing an interface for users to interact with the application.

#### Step-by-Step Guide to Test API Calls on Postman : 
* Upload CSV File :
In Postman, create a <mark>POST</mark> request to ```http://localhost:5000/upload```. Under the "Body" tab, select "form-data," add a key named csv_file, and upload your CSV file. Send the request to receive a request_id.
* Check Processing Status :
Use the <mark>GET</mark> request to ```http://localhost:5000/status/<request_id>```, replacing <request_id> with the ID received in step 1. This returns the current status of the image processing task.
* Fetch Processed Images :
Once processing is complete, send a <mark>GET</mark> request to ```http://localhost:5000/fetch/<request_id>``` to retrieve details of the processed images, including file paths and timestamps.

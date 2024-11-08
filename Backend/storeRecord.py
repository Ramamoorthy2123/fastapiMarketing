# from fastapi import FastAPI, UploadFile, File, Form, HTTPException
# from pydantic import BaseModel
# from typing import Optional
# from pymongo import MongoClient
# from fastapi import APIRouter
# import firebase_admin
# from firebase_admin import credentials, storage
# import io


# router = APIRouter()

# # MongoDB connection setup
# client = MongoClient('mongodb+srv://nani:Nani@cluster0.p71g0.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
# db = client["Marketing_DB"]
# collection = db["Record"]

# # Firebase setup
# cred = credentials.Certificate('Backend/marketing-neuro-labs.json')
# firebase_admin.initialize_app(cred, {
#     'storageBucket': 'neuro-labs-image.appspot.com' 
# })

# bucket = storage.bucket()

# # Define a Pydantic model for data validation
# class FormData(BaseModel):
#     user_name: str
#     company_name: str
#     address: str
#     contact_person: str
#     website_url: Optional[str] = ''
#     purpose: str
#     status: str
#     upload_time: str
#     location: Optional[str] = ''
#     serial_number: Optional[int] = None

# @router.post("/submit_form/")
# async def submit_form(
#     user_name: str = Form(...),
#     company_name: str = Form(...),
#     address: str = Form(...),
#     contact_person: str = Form(...),
#     website_url: Optional[str] = Form(''),
#     purpose: str = Form(...),
#     status: str = Form(...),
#     upload_time: str = Form(...),
#     location: Optional[str] = Form(''),
#     image_upload: UploadFile = File(...),
#     visiting_card: Optional[UploadFile] = File(None)
# ):
#     try:
#         last_record = collection.find_one(sort=[("serial_number", -1)])
#         serial_number = last_record["serial_number"] + 1 if last_record else 1

#         form_data = {
#             "user_name": user_name,
#             "company_name": company_name,
#             "address": address,
#             "contact_person": contact_person,
#             "website_url": website_url,
#             "purpose": purpose,
#             "status": status,
#             "upload_time": upload_time,
#             "location": location,
#             "serial_number": serial_number,
#         }

#         # Save the image to Firebase Storage
#         image_path = None
#         if image_upload:
#             image_path = await upload_to_firebase(image_upload, "images/")
#             form_data["image_path"] = image_path

#         # Save the visiting card to Firebase Storage
#         visiting_card_path = None
#         if visiting_card:
#             visiting_card_path = await upload_to_firebase(visiting_card, "visiting_cards/")
#             form_data["visiting_card_path"] = visiting_card_path

#         # Insert data into MongoDB
#         result = collection.insert_one(form_data)

#         return {
#             "status": "success",
#             "data_id": str(result.inserted_id),
#             "serial_number": serial_number,
#             "image_path": image_path,
#             "visiting_card_path": visiting_card_path
#         }

#     except Exception as e:
#         print(f"Error submitting form: {str(e)}")  # Print error to console
#         raise HTTPException(status_code=500, detail="An error occurred while processing the request.")

# async def upload_to_firebase(file: UploadFile, folder: str):
#     try:
#         blob = bucket.blob(f"{folder}{file.filename}")
#         file_content = io.BytesIO(await file.read())
#         blob.upload_from_file(file_content, content_type=file.content_type)
#         blob.make_public()  # Make the file publicly accessible
#         return blob.public_url

#     except Exception as e:
#         print(f"Error uploading file to Firebase: {str(e)}")  # Print error to console
#         raise HTTPException(status_code=500, detail="Failed to upload file to Firebase.")

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional
from pymongo import MongoClient
from fastapi import APIRouter
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload  # Required for uploading files to Google Drive
import os
import io

router = APIRouter()

# MongoDB connection setup
client = MongoClient('mongodb+srv://nani:Nani@cluster0.p71g0.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client["Marketing_DB"]
collection = db["Record"]

# Google Drive setup
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CLIENT_SECRET_FILE = 'Backend/gdriveOAuth.json'
API_NAME = 'drive'
API_VERSION = 'v3'

# Initialize the Google Drive API client
def authenticate_google_drive():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is created automatically when the authorization flow completes for the first time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    # Build the Drive service
    drive_service = build(API_NAME, API_VERSION, credentials=creds)
    return drive_service

# Upload file to Google Drive in a specific folder (async)
async def upload_file_to_drive(file: UploadFile, folder_id: str):
    try:
        drive_service = authenticate_google_drive()
        file_content = io.BytesIO(await file.read())  # Use await to read the file asynchronously
        
        # Create file metadata
        file_metadata = {
            'name': file.filename,
            'parents': [folder_id]
        }
        
        media = MediaIoBaseUpload(file_content, mimetype=file.content_type)
        
        # Upload file to Google Drive
        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return f'https://drive.google.com/file/d/{file["id"]}/view'
    except Exception as e:
        print(f"Error uploading file to Google Drive: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload file to Google Drive.")

# Define a Pydantic model for data validation
class FormData(BaseModel):
    user_name: str
    company_name: str
    address: str
    contact_person: str
    website_url: Optional[str] = ''
    purpose: str
    status: str
    upload_time: str
    location: Optional[str] = ''
    serial_number: Optional[int] = None

# Define your API endpoint to handle form submission
@router.post("/submit_form/")
async def submit_form(
    user_name: str = Form(...),
    company_name: str = Form(...),
    address: str = Form(...),
    contact_person: str = Form(...),
    website_url: Optional[str] = Form(''),
    purpose: str = Form(...),
    status: str = Form(...),
    upload_time: str = Form(...),
    location: Optional[str] = Form(''),
    image_upload: UploadFile = File(...),
    visiting_card: Optional[UploadFile] = File(None)
):
    try:
        # Get the last record to generate a new serial number
        last_record = collection.find_one(sort=[("serial_number", -1)])
        serial_number = last_record["serial_number"] + 1 if last_record else 1

        # Prepare form data
        form_data = {
            "user_name": user_name,
            "company_name": company_name,
            "address": address,
            "contact_person": contact_person,
            "website_url": website_url,
            "purpose": purpose,
            "status": status,
            "upload_time": upload_time,
            "location": location,
            "serial_number": serial_number,
        }

        # Define the folder IDs for image and visiting card directories in Google Drive
        images_folder_id = '1sB6sdwStY_lSIYFzrep8sa8NDX62AsWQ'
        visiting_card_folder_id = '1_1FYzjXPemXA9A-bEMmd8miQjtJ8_y6-'

        # Upload the image
        image_path = None
        if image_upload:
            image_path = await upload_file_to_drive(image_upload, images_folder_id)
            form_data["image_path"] = image_path

        # Upload the visiting card
        visiting_card_path = None
        if visiting_card:
            visiting_card_path = await upload_file_to_drive(visiting_card, visiting_card_folder_id)
            form_data["visiting_card_path"] = visiting_card_path

        # Insert form data into MongoDB
        result = collection.insert_one(form_data)

        return {
            "status": "success",
            "data_id": str(result.inserted_id),
            "serial_number": serial_number,
            "image_path": image_path,
            "visiting_card_path": visiting_card_path
        }

    except Exception as e:
        print(f"Error submitting form: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the request.")


from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient  # Use Motor for async MongoDB operations
from fastapi import APIRouter
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload  # Required for uploading files to Google Drive
import os
import io

router = APIRouter()

# MongoDB connection setup using Motor (async)
client = AsyncIOMotorClient('mongodb+srv://nani:Nani@cluster0.p71g0.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client["Marketing_DB"]
collection = db["Record"]

# Google Drive setup using Service Account
SCOPES = ['https://www.googleapis.com/auth/drive.file']
SERVICE_ACCOUNT_FILE = 'Backend/marketing-neuro-labs-bpo.json'  # Path to your service account credentials file
API_NAME = 'drive'
API_VERSION = 'v3'

# Initialize the Google Drive API client using Service Account
def authenticate_google_drive():
    creds = None
    try:
        # Authenticate using service account credentials
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        
        # Build the Google Drive service
        drive_service = build(API_NAME, API_VERSION, credentials=creds)
        return drive_service

    except Exception as e:
        print(f"Error authenticating with Google Drive: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to authenticate with Google Drive.")

# Upload file to Google Drive in a specific folder (async)
async def upload_file_to_drive(file: UploadFile, folder_id: str):
    try:
        drive_service = authenticate_google_drive()
        file_content = io.BytesIO(await file.read())  # Use await to read the file asynchronously
        
        # Create file metadata
        file_metadata = {
            'name': file.filename,
            'parents': [folder_id]
        }
        
        media = MediaIoBaseUpload(file_content, mimetype=file.content_type)
        
        # Upload file to Google Drive
        uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return f'https://drive.google.com/file/d/{uploaded_file["id"]}/view'
    except Exception as e:
        print(f"Error uploading file to Google Drive: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload file to Google Drive.")

# Define a Pydantic model for data validation
class FormData(BaseModel):
    user_name: str
    company_name: str
    address: str
    contact_person: str
    website_url: Optional[str] = ''
    purpose: str
    status: str
    upload_time: str
    location: Optional[str] = ''
    serial_number: Optional[int] = None

# Define your API endpoint to handle form submission
@router.post("/submit_form/")
async def submit_form(
    user_name: str = Form(...),
    company_name: str = Form(...),
    address: str = Form(...),
    contact_person: str = Form(...),
    website_url: Optional[str] = Form(''),
    purpose: str = Form(...),
    status: str = Form(...),
    upload_time: str = Form(...),
    location: Optional[str] = Form(''),
    image_upload: UploadFile = File(...),
    visiting_card: Optional[UploadFile] = File(None)
):
    try:
        # Get the last record to generate a new serial number (asynchronous)
        last_record = await collection.find_one(sort=[("serial_number", -1)])
        serial_number = last_record["serial_number"] + 1 if last_record else 1

        # Prepare form data
        form_data = {
            "user_name": user_name,
            "company_name": company_name,
            "address": address,
            "contact_person": contact_person,
            "website_url": website_url,
            "purpose": purpose,
            "status": status,
            "upload_time": upload_time,
            "location": location,
            "serial_number": serial_number,
        }

        # Define the folder IDs for image and visiting card directories in Google Drive
        images_folder_id = '1sB6sdwStY_lSIYFzrep8sa8NDX62AsWQ'
        visiting_card_folder_id = '1_1FYzjXPemXA9A-bEMmd8miQjtJ8_y6-'

        # Upload the image
        image_path = None
        if image_upload:
            image_path = await upload_file_to_drive(image_upload, images_folder_id)
            form_data["image_path"] = image_path

        # Upload the visiting card
        visiting_card_path = None
        if visiting_card:
            visiting_card_path = await upload_file_to_drive(visiting_card, visiting_card_folder_id)
            form_data["visiting_card_path"] = visiting_card_path

        # Insert form data into MongoDB asynchronously
        result = await collection.insert_one(form_data)

        return {
            "status": "success",
            "data_id": str(result.inserted_id),
            "serial_number": serial_number,
            "image_path": image_path,
            "visiting_card_path": visiting_card_path
        }

    except Exception as e:
        print(f"Error submitting form: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the request.")

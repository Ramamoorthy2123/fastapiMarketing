import os
import io
import base64
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import APIRouter
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.auth.exceptions import GoogleAuthError

router = APIRouter()

# MongoDB connection setup using Motor (async)
client = AsyncIOMotorClient('mongodb+srv://nani:Nani@cluster0.p71g0.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client["Marketing_DB"]
collection = db["Record"]

# Google Drive setup using Service Account
SCOPES = ['https://www.googleapis.com/auth/drive.file']
API_NAME = 'drive'
API_VERSION = 'v3'

# Initialize the Google Drive API client using Service Account
def authenticate_google_drive():
    creds = None
    try:
        # Get the Base64 encoded service account key from the environment variable
        base64_encoded_key = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
        if not base64_encoded_key:
            raise HTTPException(status_code=500, detail="Service account key not found in environment variables.")
        
        # Decode the Base64 string back to the original JSON content
        service_account_json = base64.b64decode(base64_encoded_key).decode('utf-8')

        # Save the decoded content to a temporary file (optional: you can store it in memory as well)
        with open("/tmp/service-account.json", "w") as f:
            f.write(service_account_json)

        # Authenticate using the service account credentials
        creds = service_account.Credentials.from_service_account_file(
            "/tmp/service-account.json", scopes=SCOPES)

        # Build the Google Drive service
        drive_service = build(API_NAME, API_VERSION, credentials=creds)
        return drive_service

    except GoogleAuthError as e:
        # This will catch authentication-related errors, including JWT signature issues
        print(f"Google authentication error: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    except Exception as e:
        # This will catch other exceptions (e.g., file handling, missing key, etc.)
        print(f"Error authenticating with Google Drive: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to authenticate with Google Drive: {str(e)}")

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
    
    except GoogleAuthError as e:
        print(f"Google authentication error while uploading file: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Authentication failed during file upload: {str(e)}")
    except Exception as e:
        print(f"Error uploading file to Google Drive: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file to Google Drive: {str(e)}")

# Define a Pydantic model for data validation
class FormData(BaseModel):
    user_name: str
    company_name: str
    address: str
    contact_person: str
    contact_number: str
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
    contact_number: str = Form(...),
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
            "contact_number": contact_number,
            "website_url": website_url,
            "purpose": purpose,
            "status": status,
            "upload_time": upload_time,
            "location": location,
            "serial_number": serial_number,
        }

        # Define the folder IDs for image and visiting card directories in Google Drive
        images_folder_id = '1L6gIpKC7HzbnRBwBePhgghdgmj79y0Ab'
        visiting_card_folder_id = '1xo-qtqxk2k_jlVGmkRDLUfwHg0G3mDE2'

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
            "visiting_card_path": visiting_card_path,
            "contact_number":contact_number
        }

    except Exception as e:
        print(f"Error submitting form: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred while processing the request: {str(e)}")

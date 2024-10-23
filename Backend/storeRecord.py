from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional
from pymongo import MongoClient
from fastapi import APIRouter
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# app = FastAPI()
router = APIRouter()

# MongoDB connection setup
client = MongoClient('mongodb+srv://nani:Nani@cluster0.p71g0.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client["Marketing_DB"]
collection = db["Record"]

# Google Drive setup
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'Backend/marketing.json'
folder_id = "1MTmA352jDO7UzilJr-vCPAkf6shFbhO9"
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)


drive_service = build('drive', 'v3', credentials=credentials)

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
        last_record = collection.find_one(sort=[("serial_number", -1)])
        serial_number = last_record["serial_number"] + 1 if last_record else 1

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

        # Save the image to Google Drive
        image_path = None
        if image_upload:
            image_path = await upload_to_drive(image_upload, "images")
            form_data["image_path"] = image_path

        # Save the visiting card to Google Drive
        visiting_card_path = None
        if visiting_card:
            visiting_card_path = await upload_to_drive(visiting_card, "visiting_cards")
            form_data["visiting_card_path"] = visiting_card_path

        # Insert data into MongoDB
        result = collection.insert_one(form_data)

        return {
            "status": "success",
            "data_id": str(result.inserted_id),
            "serial_number": serial_number,
            "image_path": image_path,
            "visiting_card_path": visiting_card_path
        }

    except Exception as e:
        print(f"Error submitting form: {str(e)}")  # Print error to console
        raise HTTPException(status_code=500, detail="An error occurred while processing the request.")

async def upload_to_drive(file: UploadFile, folder_id: str):
    try:
        file_metadata = {
            'name': file.filename,
            'parents': [folder_id]
        }

        file_content = io.BytesIO(await file.read())
        media = MediaIoBaseUpload(file_content, mimetype=file.content_type)

        uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        file_id = uploaded_file.get('id')

        # Set permissions to make it publicly accessible, if necessary
        drive_service.permissions().create(
            fileId=file_id,
            body={'role': 'reader', 'type': 'anyone'}
        ).execute()

        return f"https://drive.google.com/uc?id={file_id}"

    except Exception as e:
        print(f"Error uploading file to Google Drive: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload file to Google Drive.")


def create_or_get_folder(folder_name: str):
    # Check if folder exists
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}'"
    results = drive_service.files().list(q=query, fields="files(id)").execute()
    items = results.get('files', [])
    
    if items:
        return items[0]['id']
    
    # Create folder if it does not exist
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    folder = drive_service.files().create(body=file_metadata, fields='id').execute()
    return folder.get('id')

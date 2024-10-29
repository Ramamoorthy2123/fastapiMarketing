from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional
from pymongo import MongoClient
from fastapi import APIRouter
import firebase_admin
from firebase_admin import credentials, storage
import io
import os

router = APIRouter()

# MongoDB connection setup
client = MongoClient('mongodb+srv://nani:Nani@cluster0.p71g0.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client["Marketing_DB"]
collection = db["Record"]

# Firebase setup
cred = credentials.Certificate(os.path.join('Backend', 'marketing-neuro-labs.json'))
firebase_admin.initialize_app(cred, {
    'storageBucket': 'neuro-labs-image.appspot.com'  # Correctly formatted
})

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

async def upload_to_firebase(file: UploadFile, folder: str):
    bucket = storage.bucket()
    blob = bucket.blob(f"{folder}/{file.filename}")  # Use folder path for upload

    try:
        file_content = io.BytesIO(await file.read())
        blob.upload_from_file(file_content, content_type=file.content_type)
        blob.make_public()  # Make the file publicly accessible
        return blob.public_url

    except Exception as e:
        print(f"Error uploading file to Firebase Storage: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload file to Firebase Storage.")

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

        # Save the image to Firebase Storage in 'images' folder
        image_path = None
        if image_upload:
            image_path = await upload_to_firebase(image_upload, "images")  # Specify folder
            form_data["image_path"] = image_path

        # Save the visiting card to Firebase Storage in 'visiting_cards' folder
        visiting_card_path = None
        if visiting_card:
            visiting_card_path = await upload_to_firebase(visiting_card, "visiting_cards")  # Specify folder
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



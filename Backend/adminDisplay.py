import certifi
from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorClient  # Import AsyncIOMotorClient for async MongoDB operations
from bson import ObjectId
from datetime import datetime
from starlette.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# MongoDB configuration using Motor (Async)
client = AsyncIOMotorClient('mongodb+srv://neurolabsinnovationsdocs:Neurolabs%40123@cluster0.elyma.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0', tls=True, tlsCAFile=certifi.where())
db = client["Marketing_DB"]
collection = db["Record"]

# Define models
class RecordResponse(BaseModel):
    serial_number: int
    user_name: str
    address: str
    website_url: str
    contact_person: str
    contact_number: str
    company_name: str
    status: str
    purpose: str
    date_created: str
    image_url: Optional[str] = ""  # URL for the image
    visiting_card_url: Optional[str] = ""  # URL for the visiting card
    location: Optional[str] = ""  # Include location

    class Config:
        orm_mode = True

# Ensure directories exist
def ensure_directories_exist():
    os.makedirs("uploads/images", exist_ok=True)
    os.makedirs("uploads/visiting_cards", exist_ok=True)
    logger.info("Ensured that upload directories exist.")

# Call the function to create directories
ensure_directories_exist()

@router.get("/records/", response_model=List[RecordResponse])
async def get_records():
    try:
        # Asynchronously fetch records and sort by serial_number in ascending order
        records = await collection.find().sort("serial_number", -1).to_list(length=100)  # Sort by serial_number (ascending)
        response_data = []

        for record in records:
            record_data = {
                "serial_number": record["serial_number"],  # Use the serial_number from the record
                "user_name": record.get('user_name', ''),
                "company_name": record.get('company_name', ''),
                "status": record.get('status', ''),
                "purpose": record.get('purpose', ''),
                "date_created": record.get('upload_time', datetime.utcnow().isoformat()),
                "image_url": record.get('image_path', ''),  # Use the direct MongoDB path
                "visiting_card_url": record.get('visiting_card_path', ''),  # Use the direct MongoDB path
                "location": record.get('location', '')
            }
            response_data.append(record_data)
        
        return JSONResponse(content=response_data)

    except Exception as e:
        logger.error(f"Failed to fetch records: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/records/{serial_number}", response_model=RecordResponse)
async def get_record(serial_number: int):
    try:
        # Asynchronously fetch a single record by serial_number
        record = await collection.find_one({"serial_number": serial_number})
        if record:
            return {
                "serial_number": record["serial_number"],
                "user_name": record["user_name"],
                "company_name": record["company_name"],
                "address": record["address"], 
                "contact_person": record["contact_person"], 
                "contact_number": record["contact_number"], 
                "website_url": record["website_url"], 
                "status": record["status"],
                "purpose": record["purpose"],
                "upload_time": record["upload_time"],  # Assuming this field exists
                "date_created": record.get('upload_time', datetime.utcnow().isoformat()),
                "location": record["location"],
                "image_url": record.get('image_path', ''),  # Use the direct MongoDB path
                "visiting_card_url": record.get('visiting_card_path', ''),  # Use the direct MongoDB path
            }
        else:
            logger.warning(f"Record not found for serial_number: {serial_number}")
            raise HTTPException(status_code=404, detail="Record not found")
    
    except Exception as e:
        logger.error(f"Failed to fetch record with serial_number {serial_number}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

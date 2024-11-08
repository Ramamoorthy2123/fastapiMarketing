from fastapi import APIRouter, HTTPException
from pymongo import MongoClient
from pydantic import BaseModel,EmailStr
from passlib.context import CryptContext
import logging
from typing import Optional
from bson import ObjectId
from email_validator import validate_email, EmailNotValidError
import uvicorn
import random
import string

router = APIRouter()

# MongoDB setup
client = MongoClient('mongodb+srv://nani:Nani@cluster0.p71g0.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client["Marketing_DB"]
admin_collection = db["Admin_credentials"]


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Pydantic models
class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetUpdate(BaseModel):
    token: str
    new_password: str

# Helper functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def generate_token(length: int = 32) -> str:
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

@router.post("/resetpassword")
async def reset_password(request: PasswordResetRequest):
    # Check if the email exists
    user = admin_collection.find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=404, detail="Email not found")

    # Generate a reset token (you should send this token to user's email in a real application)
    reset_token = generate_token()
    admin_collection.update_one({"email": request.email}, {"$set": {"reset_token": reset_token}})
    
    return {"message": "Password reset link sent. Please check your email."}

@router.post("/updatepassword")
async def update_password(update_request: PasswordResetUpdate):
    # Find user by reset token
    user = admin_collection.find_one({"reset_token": update_request.token})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    # Update the password
    hashed_password = hash_password(update_request.new_password)
    admin_collection.update_one({"reset_token": update_request.token}, {"$set": {"password": hashed_password, "reset_token": None}})
    
    return {"message": "Password updated successfully"}
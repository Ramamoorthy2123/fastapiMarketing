from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
from passlib.context import CryptContext
from motor.motor_asyncio import AsyncIOMotorClient
import logging


router = APIRouter()

# MongoDB connection setup
client = AsyncIOMotorClient('mongodb+srv://neurolabsinnovationsdocs:Neurolabs%40123@cluster0.elyma.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client["Marketing_DB"]
admin_collection = db["Admin_credentials"]

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Pydantic models
class AdminSignUpRequest(BaseModel):
    email: str
    username: str
    password: str

# Helper function to hash passwords
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# Admin sign-up endpoint
@router.post("/adminsignup", status_code=201)
async def admin_signup(signup_request: AdminSignUpRequest):
    # Check if the email or username already exists
    existing_admin = await admin_collection.find_one({"$or": [{"email": signup_request.email}, {"username": signup_request.username}]})
    
    if existing_admin:
        if existing_admin['email'] == signup_request.email:
            raise HTTPException(status_code=400, detail="Email already registered")
        if existing_admin['username'] == signup_request.username:
            raise HTTPException(status_code=400, detail="Username already taken")

    # Create a new admin record
    new_admin = {
        "email": signup_request.email,
        "username": signup_request.username,
        "password": hash_password(signup_request.password)
    }
    
    await admin_collection.insert_one(new_admin)
    return {"message": "Admin account created successfully"}

# Admin login request model
class AdminLoginRequest(BaseModel):
    email: str
    password: str

# Helper function to verify password
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Admin login endpoint
@router.post("/adminlogin")
async def admin_login(login: AdminLoginRequest):
    try:
        admin = await admin_collection.find_one({"email": login.email})
        
        # Check if the admin exists
        if not admin:
            logger.warning(f"Login attempt with non-existent email: {login.email}")
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Verify the password
        if not verify_password(login.password, admin['password']):
            logger.warning(f"Login attempt with incorrect password for email: {login.email}")
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # If successful, return a success message
        return {"message": "Login successful"}
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")



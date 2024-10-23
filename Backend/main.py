
from fastapi import FastAPI, HTTPException,Request,Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,EmailStr
from pymongo import MongoClient
from passlib.context import CryptContext
import logging
from typing import Optional
from bson import ObjectId
from email_validator import validate_email, EmailNotValidError
import uvicorn
import random
import string
from . import admin,resetPassword,storeRecord,user,adminDisplay


app = FastAPI()
app.include_router(admin.router)
app.include_router(resetPassword.router)
app.include_router(user.router)
app.include_router(storeRecord.router)
app.include_router(adminDisplay.router)

client = MongoClient('mongodb+srv://nani:Nani@cluster0.p71g0.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client["Marketing_DB"]
admin_collection = db["Admin_credentials"]

# Add CORS middleware
origins = [
    "http://localhost:5173", 
    "http://marketing.neuro-labs.in" 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow specific origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (POST, GET, etc.)
    allow_headers=["*"],  # Allow all headers
)


# Refuse:-

@app.get('/')
def display():
    return {'message':"Marketing"}

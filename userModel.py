from pydantic import BaseModel, Field
from bson import ObjectId
from typing import Optional
from pymongo import MongoClient

class UserModel(BaseModel):
    userId: str = Field(..., unique=True)
    privateKey: str
    publicKey: str

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "private_key": "private_key_123",
                "public_key": "public_key_123"
            }
        }

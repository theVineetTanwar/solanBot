from pydantic import BaseModel, Field
from bson import ObjectId
from typing import Optional
import base64
from pymongo import MongoClient
from pydantic import BaseModel, Field, field_validator # v2 needed


class UserModel(BaseModel):
    userId: int = Field(..., unique=True)
    privateKey: str
    publicKey: str
    keypair: str
    
    @field_validator('privateKey')
    def check_base64(cls, v):
        try:
            base64.b64decode(v)
            return v
        except Exception as e:
            raise ValueError("Invalid base64 encoded key")

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "userId": "3234323432",
                "privateKey": base64.b64encode(b'some_private_key').decode('utf-8'),
                "publicKey": "ptgjndf985544",
                "keypair": "sdfbsd8y8dsiu44",
            }
        }
        



class UserModule():
    def __init__(
        self,
        wallet_collection
    ):
        """Init API client."""
        super().__init__()
        self.wallet_collection =  wallet_collection
        

        
    async def insert_user(self, user_data: UserModel):
        try:
            # convert the Pydantic model to a dictionary
            wallet_dict = user_data.dict(by_alias=True)
            result = self.wallet_collection.insert_one(wallet_dict)
            print(f'User inserted with id: {result.inserted_id}')
        except Exception as e:
            print(f'Error inserting user: {e}')
            

    async def get_user_by_userId(self, userId: int) -> Optional[UserModel]:
        try:
            wallet_dict = self.wallet_collection.find_one({"userId": userId})
            print('walleteddddd',wallet_dict)
            if wallet_dict:
                return UserModel(**wallet_dict)
        except Exception as e:
            print(f'Error getting user: {e}')
        return None

    def get_users(self) -> list[UserModel]:
        try:
            users = []
            for user_dict in self.wallet_collection.find():
                users.append(UserModel(**user_dict))
            return users
        except Exception as e:
            print(f'Error getting all users: {e}')
            return []

    async def update_user(self, userId: int, update_data: dict):
        try:
            result = await self.wallet_collection.update_one({"userId": userId}, {"$set": update_data})
            print('update_user result',result)
            if result.modified_count:
                print(f'User updated')
            else:
                print(f'No user found with userId: {userId}')
        except Exception as e:
            print(f'Error updating user: {e}')

    def delete_user(self, userId: str):
        try:
            result = self.wallet_collection.delete_one({"userId": userId})
            if result.deleted_count:
                print(f'User deleted')
            else:
                print(f'No user found with userId: {userId}')
        except Exception as e:
            print(f'Error deleting user: {e}')


    
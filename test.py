import asyncio
import os
import re
import requests
import base64
import json
import math  

from requests.auth import HTTPDigestAuth
from typing import Final
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.api import Client
from solders.hash import Hash
from solana.transaction import Transaction
from solders.system_program import TransferParams, transfer

from pydantic import BaseModel, Field, field_validator # v2 needed
from bson import ObjectId
from typing import Optional, List
from pymongo import MongoClient


# custom module
from solanaHelper import SolanaHelper
from jupiter import JupiterHelper
from decimal import Decimal



class Bot():
    def __init__(
        self,
    ):
        """Init API client."""
        super().__init__()
        self.one_sol_in_lamports = 1000000000
        self.sol_address = "So11111111111111111111111111111111111111112"
        self.helper = SolanaHelper()
        
    
    def get_dict_from_instance(self, instance):
        if hasattr(instance, '__dict__'):
            return instance.__dict__
        else:
            # Manually create a dictionary if __dict__ is not available
            # Adjust this according to the actual attributes of the instance
            return {attr: getattr(instance, attr) for attr in dir(instance) if not attr.startswith('_') and not callable(getattr(instance, attr))}

    def custom_serializer(self, obj):
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        elif isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        else:
            return str(obj)  # Convert non-serializable objects to string


    def main(self):
        accInfo = self.helper.getAccountInfo(Pubkey.from_string('GG8wobQdj46EX5SSdTFyD1F2DmgbWhRNLzpaxYDMvE6Q'))
        tokens = accInfo.value
        
        formatted_tokens = []
        for token in tokens:
            print(token)
            lamports = token.account.lamports
            print("lamports",lamports)
            parsedData = token.account.data.to_json()
            print("----",parsedData)
            
            print("parsed",token.account.data.parsed)
            info = token.account.data.parsed.get('info')
            print("info",info)
            
            mint = info.get('mint')
            ui_amount = info.get('tokenAmount', {}).get('uiAmount')

            if lamports is not None and mint and ui_amount is not None:
                formatted_tokens.append(f"Token: {mint}\nAmount: {ui_amount:.6f} (UI Amount)\nLamports: {lamports}")
                
            message = "\n\n".join(formatted_tokens)
            print('message',message)
      


    




if __name__ == '__main__':
    bot = Bot()
    bot.main()
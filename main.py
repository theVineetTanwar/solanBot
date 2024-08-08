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
from swap.solanaSwap import SolanaSwapModule
import constant

load_dotenv()

dbURI = os.getenv("dbURI")
TOKEN = os.getenv("TOKEN")
# SHYFT_API_KEY = os.getenv("SHYFT_API_KEY")
print('TOKEN>>>>>>>>>>', TOKEN)
mongoClient = MongoClient(dbURI)
db = mongoClient.telegram 
wallet_collection = db.wallet 

BOT_NAME: Final = '@crypto737263_bot'
chain_id = "solana"  # Change to the appropriate chain ID


main_keyboard = [
    [
        {"text": "Buy Tokens", "callback_data": "buy_token"},
        {"text": "Positions", "callback_data": "positions"}
    ],
    [
        {"text": "Wallet", "callback_data": "wallet"},
        {"text": "Settings", "callback_data": "settings"},
    ],
    [
        {"text": "Transfer Token", "callback_data": "transfer_token"},
    ],
    [
        {"text": "List tokens", "callback_data": "list_token"},
    ],
]

submenu_keyboard = [
    [
        InlineKeyboardButton("Generate Wallet", callback_data='generate_wallet'),
    ],
    [
        InlineKeyboardButton("Export Private Key", callback_data='export_private_key'),
        InlineKeyboardButton("Check Balance", callback_data='get_balance'),
    ],
    [
        InlineKeyboardButton("Withdraw SOL", callback_data='withdraw_sol'),
        InlineKeyboardButton("Send SOL", callback_data='send_sol'),
    ],
    [
        InlineKeyboardButton("Back", callback_data='back_to_main'),
    ]
]



class Bot():
    def __init__(
        self,
    ):
        """Init API client."""
        super().__init__()
        self.one_sol_in_lamports = 1000000000
        self.sol_address = "So11111111111111111111111111111111111111112"
        self.helper = SolanaHelper()
        self.jupiterHelper = JupiterHelper()
        self.solanaSwapModule = SolanaSwapModule(constant.solanaTrackerURL, constant.input_mint)

    
    
    def main(self):
        print('started bot')
        app = Application.builder().token(TOKEN).build()

        app.add_handler(CommandHandler('main', self.main_command))
        app.add_handler(CallbackQueryHandler(self.button_click_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        solanaConnected = self.helper.client.is_connected()
        if(solanaConnected):
            print('solana Connected')
        else:
            print('failed solana Connecttion')
            
        print('polling---')
        app.run_polling(poll_interval=3)


    

    async def main_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        reply_markup = InlineKeyboardMarkup(main_keyboard)
        await update.message.reply_text('Hello! This is Crypto Bot.', reply_markup=reply_markup)



    def getBalance(self, publicKey):
        response = self.helper.getBalance(Pubkey.from_string(publicKey))
        sol_bal = math.ceil((response.value / self.one_sol_in_lamports) * 100) / 100
            
        sol_price_response = requests.get('https://api.raydium.io/v2/main/price')
        sol_price_response.raise_for_status()  # Check for HTTP errors
        data = sol_price_response.json()
        sol_price = data[self.sol_address]
        usd_bal =  math.ceil((sol_bal * sol_price) * 100) / 100
        return {"sol_bal":sol_bal, "usd_bal":usd_bal}


    async def button_click_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        chat_id = query.from_user.id
        await query.answer()
        callback_data = query.data
        tmpCallBackType = context.chat_data.get("callbackType", '') or ""
        tmpPubkey = context.chat_data.get("pubKey", '') or ""


        if callback_data == 'wallet':
            submenu_reply_markup = InlineKeyboardMarkup(submenu_keyboard)
            context.chat_data["callbackType"] = callback_data
            await query.edit_message_text(text="Manage Wallet", reply_markup=submenu_reply_markup)

        elif callback_data == 'buy_token':
            context.chat_data["callbackType"] = callback_data
            await query.edit_message_text(text="Enter client address to continue:")
        elif callback_data == 'transfer_token':
            context.chat_data["callbackType"] = callback_data
            await query.edit_message_text(text="Enter token address to continue:")
        elif callback_data == 'positions':
            await query.edit_message_text(text="You clicked positions")
        elif callback_data == 'list_token':
            retrieved_user = await get_user_by_userId(int(chat_id))
            accInfo = self.helper.getAccountInfo(Pubkey.from_string(retrieved_user.publicKey))
            tokens = accInfo.value
            
            formatted_message = []
            formatted_message.append(f"<u><b>Manage your tokens</b></u>\nWallet: <code>{retrieved_user.publicKey}</code>\n")
            
            show_bal = True
            message = " No information found for tokens"
            for token in tokens:
                if(show_bal):
                    res = self.getBalance(retrieved_user.publicKey)
                    formatted_message.append(f"Balance: {res.get('sol_bal')} SOL (${res.get('usd_bal')})\n")
                show_bal = False
    
                info = token.account.data.parsed.get('info')
                ui_amount = info.get('tokenAmount', {}).get('uiAmount')
                mint = info.get('mint')
                token_info = self.get_token_info(mint)
           
                formatted_message.append(f"<b>{token_info['name']}</b> - {token_info['symbol']}")
                formatted_message.append(f"<code>{mint}</code>")
                formatted_message.append(f"Amount: {ui_amount:.6f}\n")
                message = "\n".join(formatted_message)
            await self.send_message(chat_id, message, context, None, "", "", ParseMode.HTML)
        elif callback_data == 'back_to_main':
            main_reply_markup = InlineKeyboardMarkup(main_keyboard)
            await query.edit_message_text(text="Hello! This is Crypto Bot, how can I help.", reply_markup=main_reply_markup)
        elif callback_data == 'generate_wallet':

            retrieved_user = await get_user_by_userId(int(chat_id))
            if (retrieved_user == None):
                keypair = Keypair()
                # private_key = str(keypair.secret())
                private_key = self.encode_key(keypair.secret())
                public_key = str(keypair.pubkey())
                keypairStr = str(keypair)
                
                new_user = UserModel(userId=chat_id, privateKey=private_key, publicKey=public_key, keypair = keypairStr)
                await insert_user(new_user)
                await self.send_message(chat_id, f"🎉 Wallet generated\n*Public Key*: _`{public_key}`_ \\(Tap to copy\\)", context)
            else:
                print('wallet already exist')
                await self.send_message(chat_id, f"A wallet is already created with your account\\.\nCurrently we support only one wallet per user\nYour *Public Key*: _`{retrieved_user.publicKey}`_ \\(Tap to copy\\)", context)
        elif callback_data == 'export_private_key':
            retrieved_user = await get_user_by_userId(int(chat_id))
            if(retrieved_user):
                # pk = self.decode_key(str(retrieved_user.privateKey))
                print('retrieved_user',retrieved_user)
                print('private key',retrieved_user.keypair)
                await self.send_message(chat_id, f"*Private Key*: _`{retrieved_user.keypair}`_ \\(Tap to copy\\)", context)
            else:
                await self.send_message(chat_id, f"You don\\'t have any wallet", context)
        elif callback_data == 'get_balance':
            retrieved_user = await get_user_by_userId(int(chat_id))
            if(retrieved_user):
                try:
                    res = self.getBalance(retrieved_user.publicKey)
                    
                    message = (
                        f"*Wallet Balance*\n"
                        f"`{retrieved_user.publicKey}` _\\(Tap to copy\\)_ \n"
                        f"Balance: {self.escape_dots(res.get('sol_bal'))} SOL  \\(💲{self.escape_dots(res.get('usd_bal'))}\\)"
                    )
                    await self.send_message(chat_id, message, context)
                except requests.exceptions.HTTPError as http_err:
                    print(f"HTTP error occurred: {http_err}")
                except Exception as err:
                    print(f"Other error occurred: {err}")
            else:
                await self.send_message(chat_id, f"You don\\'t have any wallet", context)
        elif callback_data == 'send_sol':
            await self.send_message(chat_id, f"Enter receiver\\'s public key to send SOL to", context, None, callback_data)    
        elif callback_data == 'buy_0.1_sol':
            await self.buyToken(chat_id, context, tmpPubkey, tmpCallBackType, 0.1)   
        elif callback_data == 'buy_0.5_sol':
            await self.buyToken(chat_id, context, tmpPubkey, tmpCallBackType, 0.5)   
        elif callback_data == 'buy_1_sol':
            await self.buyToken(chat_id, context, tmpPubkey, tmpCallBackType, 1)
        elif callback_data == 'buy_x_sol':
            await self.send_message(chat_id, f"Please enter the amount of SOL you want to swap:", context, None, tmpCallBackType, tmpPubkey)    
        elif callback_data == 'sell_x_percent':
            await self.send_message(chat_id, f"Please enter the percentage you want to sell:", context)    



    def get_token_info(self, token_address):
        try:
            api_url = f"https://api.dexscreener.io/latest/dex/tokens/{token_address}"
            response = requests.get(api_url)
            response.raise_for_status()  # Check for HTTP errors
            data = response.json()
            if data['pairs']:
                token_info = data['pairs'][0]  # Get the first pair information
                return {
                    "name": token_info['baseToken']['name'],
                    "symbol": token_info['baseToken']['symbol'],
                    "price_usd": token_info.get('priceUsd', 'N/A'),
                    "liquidity_usd": token_info.get('liquidity', {}).get('usd', 'N/A'),
                    "fdv": token_info.get('fdv', 'N/A')
                }
            else:
                return None
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except Exception as err:
            print(f"Other error occurred: {err}")


    def escape_dots(self, value):
        value_str = str(value)
        escaped_str = re.sub(r'\.', r'\\.', value_str)
        return escaped_str


    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        response = f"{text}"
        chat_type = update.message.chat.type
        chat_id = update.message.chat.id
        tmpCallBackType = context.chat_data.get("callbackType", '') or ""
        tmpPubkey = context.chat_data.get("pubKey", '') or ""
        
        if chat_type == "private":
            # Capture any word over 32 characters
            token_addresses = re.findall(r'\b\w{33,}\b', text)
            print('token_addresses-', token_addresses)
            
            # Regex to capture Solana public keys
            public_key_match = re.findall(r'\b[A-HJ-NP-Za-km-z1-9]{44}\b', text)
            print('public_key_match-', public_key_match)

            if public_key_match:
                public_key = public_key_match[0]
                print('-public_key', public_key)

                if(tmpCallBackType == "transfer_token"):
                    await self.send_message(chat_id, f"Enter amount to proceed for token:" + public_key, context, None, tmpCallBackType, public_key)
                
                elif(tmpCallBackType == "buy_token"):
                    
                    token_address = token_addresses[0]
                    print('-address', token_address)
                    token_info = self.get_token_info(token_address)
                    # print('token_info>>>>>>>>>>>>>>>>>', token_info, "public_key>>>>>>>>>", public_key)
                    if token_info:
                        await self.send_token_info_and_swap_menu(chat_id, token_info, token_address, context, message_id=update.message.message_id, callBackType = tmpCallBackType, publicKey = public_key)
                    else:
                        await self.send_message(chat_id, f"Token information not found for address: {token_address}", context)


                else:
                    await self.send_message(chat_id, f"You have not selected transaction type for the specified pubkey:"+public_key, context, None, "", "")
                


            elif re.match(r'^\d*\.?\d+$', text):
                inputAmount = float(text)

                if(not(tmpCallBackType == "buy_token" or tmpCallBackType == "transfer_token")):
                    await self.send_message(chat_id, f"You have not selected transaction type for the transaction" , context, None, tmpCallBackType, tmpPubkey)
                    return
                
                if(not(re.findall(r'\b[A-HJ-NP-Za-km-z1-9]{44}\b', tmpPubkey) )):
                    await self.send_message(chat_id, f"No public key has been setup for txn" + tmpPubkey, context, None, tmpCallBackType, tmpPubkey)
                    return



                if(tmpPubkey is not None):
                    await self.buyToken(chat_id, context, tmpPubkey, tmpCallBackType, inputAmount)
                else:
                    await self.send_message(chat_id, f"Enter receiver\\'s public key", context)
            elif re.match(r'^\d+(\.\d+)?%$', text):
                percentage = float(text.strip('%'))
                print('percentage-', percentage)
                await self.send_message(chat_id, f"Percentage set to {self.escape_dots(percentage)}\\% SOL", context)
            else:
                print('private chat replyback')
                msg = await self.send_message(chat_id, response, context, message_id=update.message.message_id)
                # await asyncio.sleep(0.5)
                # await self.edit_message_text(text="text updated by vineet",chat_id = chat_id,  message_id = msg.message_id,  context = context, )
                # await update.edit_message(text="Manage Wallet updatd string here vineet", )
        else:
            print('-group replyback')
            await update.message.reply_text(response)


    async def send_message(self, chat_id, message, context: ContextTypes.DEFAULT_TYPE, reply_keyboard=None, callbackType="", userFilledPubkey="", parseMode="", message_id=None):
        print('-sendmsg chatId', chat_id,)
        tmpParseMode = parseMode or 'MarkdownV2'

        context.chat_data["callbackType"] = callbackType
        context.chat_data["pubKey"] = userFilledPubkey
        return await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_keyboard, disable_web_page_preview=True, parse_mode=tmpParseMode, reply_to_message_id = message_id)


    async def edit_message_text(self,chat_id, text, message_id, context: ContextTypes.DEFAULT_TYPE,  parseMode=""):
        tmpParseMode = parseMode or 'MarkdownV2'
        return await context.bot.edit_message_text(text=text,chat_id = chat_id,  message_id=message_id, parse_mode=tmpParseMode)


    async def send_token_info_and_swap_menu(self, chat_id, token_info, token_address, context: ContextTypes.DEFAULT_TYPE, message_id=None, callBackType = "", publicKey = ""):
        # global buy_flag
        buy_button_text = "----BUY ✅----" # if buy_flag else "BUY"
        sell_button_text = "----SELL 🔴----" # if not buy_flag else "SELL"

        # selected_option.setdefault(chat_id, {"buy": None, "sell": None})

        buy_0_1_sol_text = "0.1 SOL" # if selected_option[chat_id]["buy"] == "0.1_sol" else "0.1 SOL"
        buy_0_5_sol_text = "0.5 SOL" # if selected_option[chat_id]["buy"] == "0.5_sol" else "0.5 SOL"
        buy_1_sol_text = "1 SOL" # if selected_option[chat_id]["buy"] == "1_sol" else "1 SOL"

        sell_50_text = "Sell 50%" #if selected_option[chat_id]["sell"] == "50" else "Sell 50%"
        sell_100_text = "Sell 100%" #if selected_option[chat_id]["sell"] == "100" else "Sell 100%"
        sell_25_text = "Sell 25%" #if selected_option[chat_id]["sell"] == "25" else "Sell 25%"

        token_info_message = (
            f"Buy {token_info['symbol']} \\- {token_info['name']} [📈](https://dexscreener.com/{chain_id}/{token_address})\n"
            f"`{token_address}` _\\(Tap to copy\\)_ \n\n"
            f"*Price \\(USD\\):* {self.escape_dots(token_info['price_usd'])}\n"
            f"*Liquidity \\(USD\\):* {self.escape_dots(token_info['liquidity_usd'])}\n"
            # f"*Liquidity \\(USD\\):* {escape_dots(token_info['liquidity_usd'])}\n"
            f"*FDV:* {token_info['fdv']}\n"
            # f"__Choose an action__\\:"
        )

        reply_keyboard = InlineKeyboardMarkup([
            [
                {"text": buy_button_text, "callback_data": "toggle_buy_mode"}
            ],
            [
                {"text": buy_0_1_sol_text, "callback_data": "buy_0.1_sol"},
                {"text": buy_0_5_sol_text, "callback_data": "buy_0.5_sol"},
            ],
            [
                {"text": buy_1_sol_text, "callback_data": "buy_1_sol"},
                {"text": "Buy with X SOL", "callback_data": "buy_x_sol"}
            ],
            # [
            #     {"text": sell_button_text, "callback_data": "toggle_sell_mode"}
            # ],
            # [
            #     {"text": sell_25_text, "callback_data": "sell_25_percent"},
            #     {"text": sell_50_text, "callback_data": "sell_50_percent"},
            # ],
            # [
            #     {"text": sell_100_text, "callback_data": "sell_100_percent"},
            #     {"text": "Sell X%", "callback_data": "sell_x_percent"}
            # ],
            # [
            #     {"text": "Execute", "callback_data": "execute_trade"}
            # ]
        ])

        await self.send_message(chat_id, token_info_message, context, reply_keyboard,callbackType = callBackType,userFilledPubkey = publicKey, message_id = message_id)




    def encode_key(key: bytes) -> str:
        return base64.b64encode(key).decode('utf-8')

    def decode_key(encoded_key: str) -> bytes:
        return base64.b64decode(encoded_key)
    
    
    async def buyToken(self, chat_id, context, tmpPubkey, tmpCallBackType, inputAmount):
        amount = int(inputAmount * self.one_sol_in_lamports)
        retrieved_user = await get_user_by_userId(int(chat_id))
        if(retrieved_user):
            sender = Keypair.from_base58_string(retrieved_user.keypair)
            receiver = Pubkey.from_string(tmpPubkey)
            if(tmpCallBackType == "transfer_token"):
                txn = self.helper.transactionFun(sender, receiver, amount)
                if(txn):
                    print('txn:-',txn)
                    await self.send_message(chat_id, f"[SOL](https://solscan.io/tx/{txn}?cluster=devnet) sent successfully", context)
                else:
                    await self.send_message(chat_id, f"🔴 Insufficient Balance", context)
            elif(tmpCallBackType == "buy_token"):
                # need to work from here 

                # tmpJupiterHel = self.jupiterHelper.initializeJup(sender)
                self.solanaSwapModule.initializeTracker(sender)
                slippage = 100  # 1% slippage in basis points
                jup_txn_id = await self.solanaSwapModule.execute_swap(tmpPubkey, inputAmount, slippage, sender)
                # jup_txn_id = await self.jupiterHelper.execute_swap(tmpPubkey, amount, slippage, sender)
                if not jup_txn_id:
                    print('txn failed>>>>>>')
                    await self.send_message(chat_id, f"There is some technical issue while buying the token", context)
                else:
                    await self.send_message(chat_id, f"[SOL](https://solscan.io/tx/{jup_txn_id}) buy successfully", context)
                

        else:
            await self.send_message(chat_id, f"You don\'t have any wallet to send SOL", context)












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
        

async def insert_user(user_data: UserModel):
    try:
        # convert the Pydantic model to a dictionary
        wallet_dict = user_data.dict(by_alias=True)
        result = wallet_collection.insert_one(wallet_dict)
        print(f'User inserted with id: {result.inserted_id}')
    except Exception as e:
        print(f'Error inserting user: {e}')
        

async def get_user_by_userId(userId: int) -> Optional[UserModel]:
    try:
        wallet_dict = wallet_collection.find_one({"userId": userId})
        print('walleteddddd',wallet_dict)
        if wallet_dict:
            return UserModel(**wallet_dict)
    except Exception as e:
        print(f'Error getting user: {e}')
    return None

def get_users() -> list[UserModel]:
    try:
        users = []
        for user_dict in wallet_collection.find():
            users.append(UserModel(**user_dict))
        return users
    except Exception as e:
        print(f'Error getting all users: {e}')
        return []

async def update_user(userId: int, update_data: dict):
    try:
        result = await wallet_collection.update_one({"userId": userId}, {"$set": update_data})
        print('update_user result',result)
        if result.modified_count:
            print(f'User updated')
        else:
            print(f'No user found with userId: {userId}')
    except Exception as e:
        print(f'Error updating user: {e}')

def delete_user(userId: str):
    try:
        result = wallet_collection.delete_one({"userId": userId})
        if result.deleted_count:
            print(f'User deleted')
        else:
            print(f'No user found with userId: {userId}')
    except Exception as e:
        print(f'Error deleting user: {e}')





if __name__ == '__main__':
    bot = Bot()
    bot.main()
#     main()

import asyncio
import os
import requests
import re
from typing import Final
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from solders.keypair import Keypair
from solders.pubkey import Pubkey

import base64
from pydantic import BaseModel, Field, field_validator # v2 needed
from bson import ObjectId
from typing import Optional, List
from pymongo import MongoClient
from transferSol import transfer_sol


load_dotenv()

dbURI = os.getenv("dbURI")
TOKEN = os.getenv("TOKEN")
SHYFT_API_KEY = os.getenv("SHYFT_API_KEY")
client = MongoClient(dbURI)
db = client.telegram 
wallet_collection = db.wallet 
# print('wallet_collection',wallet_collection)



BOT_NAME: Final = '@crypto737263_bot'
SHYFT_API_KEY = 'GlJ737ibT8z26T3f'
chain_id = "solana"  # Change to the appropriate chain ID

main_keyboard = [
    [
        {"text": "Buy/Sell", "callback_data": "buy_sell"},
        {"text": "Positions", "callback_data": "positions"}
    ],
    [
        {"text": "Wallet", "callback_data": "wallet"},
        {"text": "Settings", "callback_data": "settings"},
    ]
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
        InlineKeyboardButton("Back", callback_data='back_to_main'),
    ]
]



class UserModel(BaseModel):
    userId: int = Field(..., unique=True)
    privateKey: str
    publicKey: str
    keypair: str

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "userId": "3234323432",
                "privateKey": "fgfgu47574u34433",
                "publicKey": "ptgjndf985544",
                "keypair": "sdfbsd8y8dsiu44",
            }
        }
        


def encode_key(key: bytes) -> str:
    return base64.b64encode(key).decode('utf-8')

def decode_key(encoded_key: str) -> bytes:
    return base64.b64decode(encoded_key)

def pubkey_to_bytes(pubkey: Pubkey) -> bytes:
    return bytes(pubkey)

def keypair_to_bytes(keypair: Keypair) -> bytes:
    return keypair.secret()




async def insert_user(user_data: UserModel):
    try:
        # convert the Pydantic model to a dictionary
        wallet_dict = user_data.dict(by_alias=True)
        print('wallet_dict',wallet_dict)
        result = wallet_collection.insert_one(wallet_dict)
        print(f'User inserted with id: {result.inserted_id}')
    except Exception as e:
        print(f'Error inserting user: {e}')
        

async def get_user_by_userId(userId: int) -> Optional[UserModel]:
    print('uid',userId)
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

def update_user(userId: int, update_data: dict):
    try:
        result = wallet_collection.update_one({"userId": userId}, {"$set": update_data})
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



# Get all users
# all_users = get_users()
# for user in all_users:
#     print(user)

async def main_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = InlineKeyboardMarkup(main_keyboard)
    await update.message.reply_text('Hello! This is Crypto Bot.', reply_markup=reply_markup)


async def button_click_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    print('-update',update)
    print('-query',query)
    chat_id = query.from_user.id
    await query.answer()
    callback_data = query.data

    if callback_data == 'wallet':
        submenu_reply_markup = InlineKeyboardMarkup(submenu_keyboard)
        await query.edit_message_text(text="Manage Wallet", reply_markup=submenu_reply_markup)
    elif callback_data == 'buy_sell':
        await query.edit_message_text(text="Enter client address to continue:")
    elif callback_data == 'positions':
        await query.edit_message_text(text="You clicked positions")
    elif callback_data == 'settings':
        await query.edit_message_text(text="You clicked settings")
    elif callback_data == 'back_to_main':
        main_reply_markup = InlineKeyboardMarkup(main_keyboard)
        await query.edit_message_text(text="Hello! This is Crypto Bot, how can I help.", reply_markup=main_reply_markup)
    elif callback_data == 'generate_wallet':
        print('generating wallet with chat id-',chat_id)
        print('type of chatid',type(chat_id))

        retrieved_user = await get_user_by_userId(int(chat_id))
        print('retrieved_user',retrieved_user)
        if (retrieved_user == None):
            keypair = Keypair()
            private_key = str(keypair.secret())
            public_key = str(keypair.pubkey())
            keypairStr = str(keypair)
            
            new_user = UserModel(userId=chat_id, privateKey=private_key, publicKey=public_key, keypair = keypairStr)
            await insert_user(new_user)
            await send_message(chat_id, f"🎉 Wallet generated\n*Public Key*: _`{public_key}`_ \\(Tap to copy\\)", context)
        else:
            print('wallet already exist')
            await send_message(chat_id, f"A wallet is already created with your account\\.\nCurrently we support only one wallet per user\nYour *Public Key*: _`{retrieved_user.publicKey}`_ \\(Tap to copy\\)", context)
    elif callback_data == 'export_private_key':
        retrieved_user = await get_user_by_userId(int(chat_id))
        print('retrieved_user',retrieved_user)
        print('private key',retrieved_user.privateKey)
        await send_message(chat_id, f"*Private Key*: _`{retrieved_user.privateKey}`_ \\(Tap to copy\\)", context)
    elif callback_data == 'get_balance':
        retrieved_user = await get_user_by_userId(int(chat_id))
        if(retrieved_user):
            try:
                wallet_address = retrieved_user.publicKey
                url = f"https://api.shyft.to/sol/v1/wallet/balance?network=devnet&wallet={wallet_address}"
                headers = {
                    "x-api-key": SHYFT_API_KEY
                }
                response = requests.get(url, headers=headers)
                response.raise_for_status()  # Check for HTTP errors
                res = response.json()  # Parse the JSON response
                print("---res",res)
                
                balance = res["result"]["balance"]
                message = (
                    f"*Wallet Balance*\n"
                    f"`{wallet_address}` _\\(Tap to copy\\)_ \n"
                    f"Balance: {balance} \\(\\${escape_dots(balance)}\\)"
                )
                await send_message(chat_id, message, context)
            except requests.exceptions.HTTPError as http_err:
                print(f"HTTP error occurred: {http_err}")
            except Exception as err:
                print(f"Other error occurred: {err}")
        else:
            await send_message(chat_id, f"You don\\'t have any wallet", context)
    elif callback_data == 'buy_0.1_sol':
        await send_message(chat_id, f"Buying 0\\.1 SOL", context)
    elif callback_data == 'buy_x_sol':
        await send_message(chat_id, f"Please enter the amount of SOL you want to swap:", context)    
    elif callback_data == 'sell_x_percent':
        await send_message(chat_id, f"Please enter the percentage you want to sell:", context)    


def get_token_info(token_address):
    api_url = f"https://api.dexscreener.io/latest/dex/tokens/{token_address}"
    response = requests.get(api_url)
    response.raise_for_status()  # Check for HTTP errors
    data = response.json()
    print('getTokenData',data)

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


def escape_dots(value):
    value_str = str(value)
    escaped_str = re.sub(r'\.', r'\\.', value_str)
    return escaped_str


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("update", update)
    text = update.message.text
    response = f"{text}"
    chat_type = update.message.chat.type
    chat_id = update.message.chat.id

    print('chat_type', chat_type)

    if chat_type == "private":
        # Capture any word over 32 characters
        token_addresses = re.findall(r'\b\w{33,}\b', text)
        print('token_addresses-', token_addresses)
        if token_addresses:
            token_address = token_addresses[0]
            print('-address', token_address)
            token_info = get_token_info(token_address)
            print('tokenInfo', token_info)
            if token_info:
                await send_token_info_and_swap_menu(chat_id, token_info, token_address, context)
            else:
                await send_message(chat_id, f"Token information not found for address: {token_address}", context)
        elif re.match(r'^\d+(\.\d+)?$', text):
            amount = float(text)
            print('-amount', amount)
            # pending_amount[chat_id] = amount
            await send_message(chat_id, f"Buying amount set to {escape_dots(amount)} SOL", context)
        elif re.match(r'^\d+(\.\d+)?%$', text):
            percentage = float(text.strip('%'))
            print('percentage-', percentage)
            await send_message(chat_id, f"Percentage set to {escape_dots(percentage)}\\% SOL", context)
            # asyncio.run(handle_sell(chat_id, percentage))
        else:
            print('private chat replyback')
            await send_message(chat_id, response, context)
            # await update.message.reply_text(response)
    else:
        print('-group replyback')
        await update.message.reply_text(response)


async def send_message(chat_id, message, context: ContextTypes.DEFAULT_TYPE, reply_keyboard=None):
    print('-sendmsg chatId', chat_id)
    print('-sendmsg text', message)
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_keyboard, disable_web_page_preview=True, parse_mode='MarkdownV2')


async def send_token_info_and_swap_menu(chat_id, token_info, token_address, context: ContextTypes.DEFAULT_TYPE):
    # print('send swap', chat_id, token_info, token_address)
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
        f"{token_info['symbol']} \\- {token_info['name']} [📈](https://dexscreener.com/{chain_id}/{token_address})\n"
        f"`{token_address}` _\\(Tap to copy\\)_ \n\n"
        f"*Price \\(USD\\):* {escape_dots(token_info['price_usd'])}\n"
        f"*Liquidity \\(USD\\):* {escape_dots(token_info['liquidity_usd'])}\n"
        # f"*FDV:* {token_info['fdv']}\n\n"
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
        [
            {"text": sell_button_text, "callback_data": "toggle_sell_mode"}
        ],
        [
            {"text": sell_25_text, "callback_data": "sell_25_percent"},
            {"text": sell_50_text, "callback_data": "sell_50_percent"},
        ],
        [
            {"text": sell_100_text, "callback_data": "sell_100_percent"},
            {"text": "Sell X%", "callback_data": "sell_x_percent"}
        ],
        # [
        #     {"text": "Execute", "callback_data": "execute_trade"}
        # ]
    ])

    await send_message(chat_id, token_info_message, context, reply_keyboard)


async def insert(chat_id):
    retrieved_user = await get_user_by_userId(int(chat_id))
    print('retrieved_user',retrieved_user)
    
    if(retrieved_user==None):
        print('------creating new user')
        keypair = Keypair()
        private_key = str(keypair.secret())
        public_key = str(keypair.pubkey())
        keypairStr = str(keypair)
        new_user = UserModel(userId=int(123456789), privateKey=private_key, publicKey=public_key, keypair=keypairStr)
        await insert_user(new_user)
    else:
        print('------userrrr already exist')
    
async def getAllUsers():    
    all_users = get_users()
    for user in all_users:
        print(user)

async def getUser(uid):    
    # uid=894489141
    retrieved_user = await get_user_by_userId(int(uid))
    print('retrieved_user',retrieved_user)
    
     
def main():
    print('started bot')

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler('main', main_command))
    app.add_handler(CallbackQueryHandler(button_click_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # asyncio.run(insert(123456789))
    # asyncio.run(getUser(123456789))
    # asyncio.run(getAllUsers())
        
    print('polling---')
    app.run_polling(poll_interval=3)



if __name__ == '__main__':
    main()

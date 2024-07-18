# import asyncio
import os
import requests
import re
from typing import Final
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from solders.keypair import Keypair

from pydantic import BaseModel, Field
from bson import ObjectId
from typing import Optional
from pymongo import MongoClient
from userModel import UserModel


load_dotenv()

dbURI = os.getenv("dbURI")
client = MongoClient(dbURI)
db = client.telegram 
wallet_collection = db.wallet 
# print('wallet_collection',wallet_collection)



TOKEN: Final = ''
BOT_NAME: Final = ''
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
        InlineKeyboardButton("Export Private Key", callback_data='export_private_key'),
    ],
    [
        InlineKeyboardButton("Withdraw SOL", callback_data='withdraw_sol'),
        InlineKeyboardButton("Back", callback_data='back_to_main'),
    ]
]



def insert_user(user_data: UserModel):
    try:
        # convert the Pydantic model to a dictionary
        wallet_dict = user_data.dict(by_alias=True)
        print('wallet_dict',wallet_dict)
        result = wallet_collection.insert_one(wallet_dict)
        print(f'User inserted with id: {result.inserted_id}')
    except Exception as e:
        print(f'Error inserting user: {e}')

def get_user_by_userId(userId: str) -> Optional[UserModel]:
    try:
        wallet_dict = wallet_collection.find_one({"userId": userId})
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

def update_user(userId: str, update_data: dict):
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

# Create a new user
    # new_user = UserModel(userId="user123", privateKey="private_key_123", publicKey="public_key_12333333")
    # # Insert the new user
    # insert_user(new_user)


# Get all users
all_users = get_users()
for user in all_users:
    print(user)

async def main_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = InlineKeyboardMarkup(main_keyboard)
    await update.message.reply_text('Hello! This is Crypto Bot.', reply_markup=reply_markup)


async def button_click_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.from_user.id
    await query.answer()
    callback_data = query.data

    if callback_data == 'wallet':
        submenu_reply_markup = InlineKeyboardMarkup(submenu_keyboard)
        await query.edit_message_text(text="Manage Wallet", reply_markup=submenu_reply_markup)
    elif callback_data == 'buy_sell':
        await query.edit_message_text(text="You clicked buy sell")
    elif callback_data == 'positions':
        await query.edit_message_text(text="You clicked positions")
    elif callback_data == 'settings':
        await query.edit_message_text(text="You clicked settings")
    elif callback_data == 'back_to_main':
        main_reply_markup = InlineKeyboardMarkup(main_keyboard)
        await query.edit_message_text(text="Hello! This is Crypto Bot, how can I help.", reply_markup=main_reply_markup)
    elif callback_data == 'generate_wallet':
        print('generating wallet')
        keypair = Keypair()
        public_key = keypair.pubkey()
        private_key = keypair.secret()
        await send_message(chat_id, f"**Private Key**: [{private_key}](tg://copy?text={private_key})\n **Public Key**: [{public_key}](tg://copy?text={public_key})", context)



def get_token_info(token_address):
    api_url = f"https://api.dexscreener.io/latest/dex/tokens/{token_address}"
    response = requests.get(api_url)
    data = response.json()
    # print('getTokenData',data)

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


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("update", update)
    text = update.message.text
    response = f"You said: {text}"
    chat_type = update.message.chat.type
    chat_id = update.message.chat.id

    print('chat_type', chat_type)

    if chat_type == "private":
        # Capture any word over 32 characters
        token_addresses = re.findall(r'\b\w{33,}\b', text)
        print('token_addresses-', token_addresses)
        if token_addresses:
            token_address = token_addresses[0]
            token_info = get_token_info(token_address)
            print('tokenInfo', token_info)
            if token_info:
                await send_token_info_and_swap_menu(chat_id, token_info, token_address, context)
            else:
                await send_message(chat_id, f"Token information not found for address: {token_address}", context)
        elif re.match(r'^\d+(\.\d+)?$', text):
            print('-amount', amount)
            amount = float(text)
            # pending_amount[chat_id] = amount
            await send_message(chat_id, f"Amount set to {amount} SOL. Press 'Execute' to proceed.", context)
        elif re.match(r'^\d+(\.\d+)?%$', text):
            percentage = float(text.strip('%'))
            print('percentage-', percentage)
            await send_message(chat_id, f"Percentage set to {percentage} SOL. Press 'Execute' to proceed.", context)
            # asyncio.run(handle_sell(chat_id, percentage))
        else:
            print('private chat replyback')
            await send_message(chat_id, response, context)
            # await update.message.reply_text(response)
    else:
        print('-group replyback')
        await update.message.reply_text(response)


async def send_message(chat_id, message, context: ContextTypes.DEFAULT_TYPE):
    print('-sendmsg chatId', chat_id)
    print('-sendmsg text', message)
    await context.bot.send_message(chat_id=chat_id, text=message)


async def send_token_info_and_swap_menu(chat_id, token_info, token_address, context: ContextTypes.DEFAULT_TYPE):
    print('send swap', chat_id, token_info, token_address)
    # global buy_flag
    # buy_button_text = "BUY ✅" if buy_flag else "BUY"
    # sell_button_text = "SELL ✅" if not buy_flag else "SELL"

    # selected_option.setdefault(chat_id, {"buy": None, "sell": None})

    # buy_0_1_sol_text = "0.1 SOL ✅" if selected_option[chat_id]["buy"] == "0.1_sol" else "0.1 SOL"
    # buy_0_5_sol_text = "0.5 SOL ✅" if selected_option[chat_id]["buy"] == "0.5_sol" else "0.5 SOL"
    # buy_1_sol_text = "1 SOL ✅" if selected_option[chat_id]["buy"] == "1_sol" else "1 SOL"

    # sell_25_text = "Sell 25% ✅" if selected_option[chat_id]["sell"] == "25" else "Sell 25%"
    # sell_50_text = "Sell 50% ✅" if selected_option[chat_id]["sell"] == "50" else "Sell 50%"
    # sell_100_text = "Sell 100% ✅" if selected_option[chat_id]["sell"] == "100" else "Sell 100%"

    token_info_message = (
        f"{token_info['symbol']} - {token_info['name']} [📈](https://dexscreener.com/{chain_id}/{token_address}\u200b)\n"
        f"`{token_address}`\n\n"
        f"**Price (USD):** {token_info['price_usd']}\n"
        f"**Liquidity (USD):** {token_info['liquidity_usd']}\n"
        f"**FDV:** {token_info['fdv']}\n\n"
        f"Choose an action:"
    )

    await send_message(chat_id, token_info_message, context)

    # keyboard = {
    #     "inline_keyboard": [
    #         [
    #             {"text": buy_button_text, "callback_data": "toggle_buy_mode"}
    #         ],
    #         [
    #             {"text": buy_0_1_sol_text, "callback_data": "buy_0.1_sol"},
    #             {"text": buy_0_5_sol_text, "callback_data": "buy_0.5_sol"},
    #             {"text": buy_1_sol_text, "callback_data": "buy_1_sol"}
    #         ],
    #         [
    #             {"text": "Buy with X SOL", "callback_data": "buy_x_sol"}
    #         ],
    #         [
    #             {"text": sell_button_text, "callback_data": "toggle_sell_mode"}
    #         ],
    #         [
    #             {"text": sell_25_text, "callback_data": "sell_25_percent"},
    #             {"text": sell_50_text, "callback_data": "sell_50_percent"},
    #             {"text": sell_100_text, "callback_data": "sell_100_percent"}
    #         ],
    #         [
    #             {"text": "Sell X%", "callback_data": "sell_x_percent"}
    #         ],
    #         [
    #             {"text": "Execute", "callback_data": "execute_trade"}
    #         ]
    #     ]
    # }

    # parameters = {
    #     "chat_id": chat_id,
    #     "text": token_info_message,
    #     "reply_markup": json.dumps(keyboard),
    #     "parse_mode": "Markdown"
    # }

    # resp = requests.post(send_message_url, data=parameters)
    # print(resp.text)


if __name__ == '__main__':
    print('started bot')

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler('main', main_command))
    app.add_handler(CallbackQueryHandler(button_click_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print('polling---')

    app.run_polling(poll_interval=3)
import asyncio
import os
import re
import requests
import base64
import json
import math  
import locale

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
from userModel import UserModule , UserModel

load_dotenv()

dbURI = os.getenv("dbURI")
TOKEN = os.getenv("TOKEN")
# SHYFT_API_KEY = os.getenv("SHYFT_API_KEY")
mongoClient = MongoClient(dbURI)
db = mongoClient.telegram 
wallet_collection = db.wallet 


chain_id = "solana"  # Change to the appropriate chain ID
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8') 


main_keyboard = [
    [
        {"text": "Buy", "callback_data": "buy_token"},
        {"text": "Sell", "callback_data": "sell_token"},
    ],
    [
        {"text": "Wallet", "callback_data": "wallet"},
        {"text": "Positions", "callback_data": "list_token"}
    ],
    [
        {"text": "Transfer Token", "callback_data": "transfer_token"},
    ],
    [
        {"text": "Settings", "callback_data": "settings"},
    ],
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
        self.solanaSwapModule = SolanaSwapModule(constant.solanaTrackerURL)
        self.userModule = UserModule(wallet_collection)

    
    
    def main(self):
        print('started bot')
        app = Application.builder().token(TOKEN).build()

        app.add_handler(CommandHandler('sell', self.sell_command))
        app.add_handler(CommandHandler('position', self.position_command))
        app.add_handler(CommandHandler('start', self.start_command))
        app.add_handler(CommandHandler('orders', self.order_command))
        app.add_handler(CallbackQueryHandler(self.button_click_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        solanaConnected = self.helper.client.is_connected()
        if(solanaConnected):
            print('solana Connected')
        else:
            print('failed solana Connecttion')
            
        print('polling---')
        app.run_polling(poll_interval=3)


    
    async def sell_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.message.chat.id
        await self.sellTokenFunc(chat_id, context, 'sell_token')
    
    async def position_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.message.chat.id
        await self.listToken(chat_id, context)


    async def order_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.message.chat.id
        await self.listOrders(chat_id, context)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # reply_markup = InlineKeyboardMarkup(main_keyboard)
        text = update.message.text
        chat_id = update.message.chat.id
        message_id = update.message.message_id
        
        parts = text.split()
        if(parts and not len(parts) == 1):
            cb_type = parts[1].split('-')[0]
            token_to_sell = parts[1].split('-')[1]
            
            # print("Type:", cb_type)
            # print("Token Code:", token_to_sell)
            if(cb_type == "sellToken"):
                token_info = self.get_token_info(token_to_sell)
                if token_info:
                    await self.sell_swap_menu(chat_id, token_info, token_to_sell, context, message_id=update.message.message_id, callBackType="sell_token")
                else:
                    await self.send_message(chat_id, f"Token information not found for address: {token_to_sell}", context)
            
            elif(cb_type == "cancelOrder"):
                try:
                    retrieved_user = await self.userModule.get_user_by_userId(int(chat_id))
                    if(retrieved_user):
                        sender = Keypair.from_base58_string(retrieved_user.keypair)
                        tmpJupiterHel = JupiterHelper(sender)
                        # tmpData = tmpJupiterHel.cancel_orders([token_to_sell], sender)
                except Exception as err:
                    tmpData = "error"
                await self.send_message(chat_id, f"cancel order functionality in process:", context)
            await self.delete_message(chat_id, message_id , context)
            # await update.message.reply_text('Hello! This is Crypto Bot.', reply_markup=reply_markup)
        else:
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
        message_id = query.message.message_id
        await query.answer()
        callback_data = query.data
        tmpCallBackType = context.chat_data.get("callbackType", '') or ""
        tmpPubkey = context.chat_data.get("pubKey", '') or ""

        print("tmpCallBackType in btn click callback----",context.chat_data)

        if callback_data == 'wallet':
            tmp_menu = await self.getSubmenuKeyboard(chat_id)
            submenu_reply_markup = InlineKeyboardMarkup(tmp_menu)
            context.chat_data["callbackType"] = callback_data
            await query.edit_message_text(text="Manage Your Wallet", reply_markup=submenu_reply_markup)
        elif callback_data == 'buy_token':
            context.chat_data["callbackType"] = callback_data
            await query.edit_message_text(text="Enter token address to continue:")
        elif callback_data == 'sell_token':
            await self.sellTokenFunc(chat_id, context, callback_data)
        elif callback_data == 'transfer_token':
            context.chat_data["callbackType"] = callback_data
            await query.edit_message_text(text="Enter receiver\'s address to continue:")
        elif callback_data == 'positions':
            await query.edit_message_text(text="You clicked positions")
        elif callback_data == 'list_token':
            await self.listToken(chat_id, context)
        elif callback_data == 'back_to_main':
            main_reply_markup = InlineKeyboardMarkup(main_keyboard)
            await query.edit_message_text(text="Hello! This is Crypto Bot, how can I help.", reply_markup=main_reply_markup)
        elif callback_data == 'generate_wallet':
            retrieved_user = await self.userModule.get_user_by_userId(int(chat_id))
            if (retrieved_user == None):
                keypair = Keypair()
                # private_key = str(keypair.secret())
                private_key = self.encode_key(keypair.secret())
                public_key = str(keypair.pubkey())
                keypairStr = str(keypair)
                
                new_user = UserModel(userId=chat_id, privateKey=private_key, publicKey=public_key, keypair = keypairStr)
                await self.userModule.insert_user(new_user)
                await self.send_message(chat_id, f"🎉 Wallet generated\n*Public Key*: _`{public_key}`_ \\(Tap to copy\\)", context)
            else:
                print('wallet already exist')
                await self.send_message(chat_id, f"Your *Public Key*: _`{retrieved_user.publicKey}`_ \\(Tap to copy\\)", context)
        elif callback_data == 'export_private_key':
            retrieved_user = await self.userModule.get_user_by_userId(int(chat_id))
            if(retrieved_user):
                # pk = self.decode_key(str(retrieved_user.privateKey))
                print('retrieved_user',retrieved_user)
                print('private key',retrieved_user.keypair)
                await self.send_message(chat_id, f"*Private Key*: _`{retrieved_user.keypair}`_ \\(Tap to copy\\)", context)
            else:
                await self.send_message(chat_id, f"You don\\'t have any wallet", context)
        elif callback_data == 'get_balance':
            retrieved_user = await self.userModule.get_user_by_userId(int(chat_id))
            if(retrieved_user):
                try:
                    res = self.getBalance(retrieved_user.publicKey)
                    
                    message = (
                        f"*Wallet Balance*\n"
                        f"`{retrieved_user.publicKey}` _\\(Tap to copy\\)_ \n"
                        f"Balance: *{self.escape_dots(res.get('sol_bal'))} SOL  \\(${self.escape_dots(res.get('usd_bal'))}*\\)"
                    )
                    await self.send_message(chat_id, message, context)
                except requests.exceptions.HTTPError as http_err:
                    print(f"HTTP error occurred: {http_err}")
                except Exception as err:
                    print(f"Other error occurred: {err}")
            else:
                await self.send_message(chat_id, f"You don\\'t have any wallet", context)
        elif callback_data == 'buy_0.1_sol':
            await self.buyToken(chat_id, context, tmpPubkey, tmpCallBackType, 0.1)   
        elif callback_data == 'buy_0.5_sol':
            await self.buyToken(chat_id, context, tmpPubkey, tmpCallBackType, 0.5)   
        elif callback_data == 'buy_1_sol':
            await self.buyToken(chat_id, context, tmpPubkey, tmpCallBackType, 1)
        elif callback_data == 'buy_x_sol':
            await self.send_message(chat_id, f"Please enter the amount of SOL you want to swap:", context, None, tmpCallBackType, tmpPubkey)    
        elif callback_data == 'sell_25_percent':
            print('sell_25_percent',tmpCallBackType, tmpPubkey)
            await self.sellToken(chat_id, context, tmpPubkey, 0.25)   
        elif callback_data == 'sell_50_percent':
            await self.sellToken(chat_id, context, tmpPubkey, 0.50)   
        elif callback_data == 'sell_100_percent':
            await self.sellToken(chat_id, context, tmpPubkey, 1)
        elif callback_data == 'sell_x_percent':
            print('sell_x_percent',tmpCallBackType)
            await self.send_message(chat_id, f"Please enter the percentage you want to sell:", context, None, tmpCallBackType, tmpPubkey)
        elif callback_data == 'toggle_swap_mode':
            context.chat_data["callbackType"] = 'buy_token'
            print('toggle_swap_mode',tmpCallBackType)
            markup = query.message.reply_markup
            updated_markup = self.getUpdatedBuyKeyboard(markup.inline_keyboard, True)
            # print("updatedMessage",updated_markup)
            await self.edit_message_text(text=query.message.text, chat_id = chat_id, message_id = message_id, context = context, parseMode=ParseMode.HTML, reply_keyboard=updated_markup)
        elif callback_data == 'toggle_limit_mode':
            print('toggle_limit_mode',tmpCallBackType)
            context.chat_data["callbackType"] = 'buy_with_limit'
            markup = query.message.reply_markup
            updated_markup = self.getUpdatedBuyKeyboard(markup.inline_keyboard, False)
            await self.edit_message_text(text=query.message.text, chat_id = chat_id, message_id = message_id, context = context, parseMode=ParseMode.HTML, reply_keyboard=updated_markup)
        elif callback_data == 'trigger_at':
            context.chat_data["callbackType"] = 'trigger_at'
            tmpCallBackType = context.chat_data.get("callbackType", '') or ""
            print('trigger_at',tmpCallBackType)
            await self.send_message(chat_id, f"Please enter the percentage you want to trigger at:", context, None, tmpCallBackType, tmpPubkey)
        elif callback_data == 'create_order':
            print('create_order',tmpCallBackType)
            limitAmount = context.chat_data.get("limitAmount", '') or 0
            triggerAt = context.chat_data.get("triggerAt", '') or 0
            await self.buyWithLimit(chat_id, context, tmpPubkey, tmpCallBackType, limitAmount, triggerAt)



    def getUpdatedBuyKeyboard(self, keyboard, toggleSwap):
        new_buttons = []
        for row in keyboard:
            new_row = []
            for button in row:
                if button.callback_data == 'toggle_swap_mode' or button.callback_data == 'toggle_limit_mode':                
                    if button.callback_data == 'toggle_swap_mode':
                        new_row.append(InlineKeyboardButton(
                            text='Swap' + (' ✅' if toggleSwap else ''),
                            callback_data='toggle_swap_mode'
                        ))
                    if button.callback_data == 'toggle_limit_mode':
                        new_row.append(InlineKeyboardButton(
                            text='Limit' + (' ✅' if not(toggleSwap) else ''),
                            callback_data='toggle_limit_mode'
                        ))
                else:
                    # Keep other buttons unchanged
                    if not(button.callback_data == 'trigger_at' or button.callback_data == 'create_order'):
                        new_row.append(button)
            new_buttons.append(new_row)
        
        if not(toggleSwap):
            trigger_btn = [InlineKeyboardButton(
                text='Trigger at:',
                callback_data='trigger_at'
            )]
            
            execute_btn = [InlineKeyboardButton(
                text='CREATE ORDER',
                callback_data='create_order'
            )]
            new_buttons.append(trigger_btn)
            new_buttons.append(execute_btn)
            
        updated_markup = InlineKeyboardMarkup(new_buttons) 
        return updated_markup



    def get_token_info(self, token_address):
        try:
            api_url = f"https://api.dexscreener.io/latest/dex/tokens/{token_address}"
            response = requests.get(api_url)
            response.raise_for_status()  # Check for HTTP errors
            data = response.json()
            # return None
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
        print('-handleMessage: tmpCallBackType',tmpCallBackType)
        
        if chat_type == "private":
            # Capture any word over 32 characters
            token_addresses = re.findall(r'\b\w{33,}\b', text)
            # print('token_addresses-', token_addresses)
            
            # Regex to capture Solana public keys
            public_key_match = re.findall(r'\b[A-HJ-NP-Za-km-z1-9]{44}\b', text)
            # print('public_key_match-', public_key_match)

            if public_key_match:
                public_key = public_key_match[0]
                print('-public_key', public_key)

                if(tmpCallBackType == "transfer_token"):
                    await self.send_message(chat_id, f"Enter amount to proceed for token: \n_{public_key}_", context, None, tmpCallBackType, public_key)
                
                else:                 
                    token_address = token_addresses[0]
                    print('-address', token_address)
                    token_info = self.get_token_info(token_address)
                    # print('token_info>>>>>>>>>>>>>>>>>', token_info, "public_key>>>>>>>>>", public_key)
                    if token_info:
                        await self.buy_swap_menu(chat_id, token_info, token_address, context, message_id=update.message.message_id, callBackType = tmpCallBackType, publicKey = public_key)
                    else:
                        await self.send_message(chat_id, f"Token information not found for address: {token_address}", context)


            elif re.match(r'^\d*\.?\d+$', text):
                inputAmount = float(text)

                if(not(tmpCallBackType == "buy_token" or tmpCallBackType == "transfer_token" or tmpCallBackType == "sell_token" or tmpCallBackType == "buy_with_limit" or tmpCallBackType == "trigger_at")):
                    await self.send_message(chat_id, f"You have not selected transaction type for the transaction" , context, None, tmpCallBackType, tmpPubkey)
                    return
                
                if(not(re.findall(r'\b[A-HJ-NP-Za-km-z1-9]{44}\b', tmpPubkey) )):
                    await self.send_message(chat_id, f"No public key has been setup for txn" + tmpPubkey, context, None, tmpCallBackType, tmpPubkey)
                    return
                
                if(tmpPubkey is not None and tmpCallBackType == "sell_token"):
                    await self.sellToken(chat_id, context, tmpPubkey, inputAmount)
                    return
                
                if(tmpPubkey is not None and tmpCallBackType == "trigger_at"):
                    context.chat_data["triggerAt"] = inputAmount #  for percentage input amount should be calculated in usd
                    return
                
                if(tmpPubkey is not None and tmpCallBackType == "buy_with_limit"):
                    context.chat_data["limitAmount"] = inputAmount
                    # await self.buyWithLimit(chat_id, context, tmpPubkey, tmpCallBackType, inputAmount)
                    return

                if(tmpPubkey is not None and tmpCallBackType == "buy_token"):
                    await self.buyToken(chat_id, context, tmpPubkey, tmpCallBackType, inputAmount)
                else:
                    print('---else',context)
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
        print('-sendmsg chatId', chat_id, callbackType)
        tmpParseMode = parseMode or 'MarkdownV2'

        context.chat_data["callbackType"] = callbackType
        context.chat_data["pubKey"] = userFilledPubkey
        return await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_keyboard, disable_web_page_preview=True, parse_mode=tmpParseMode, reply_to_message_id = message_id)


    async def edit_message_text(self, chat_id, text, message_id, context: ContextTypes.DEFAULT_TYPE,  parseMode="", reply_keyboard=None):
        try:
            tmpParseMode = parseMode or 'MarkdownV2'
            return await context.bot.edit_message_text(text=text,chat_id = chat_id, disable_web_page_preview=True, message_id=message_id, parse_mode=tmpParseMode, reply_markup=reply_keyboard)
        except Exception as err:
            print(f"Other error occurred: {err}")


    async def delete_message(self, chat_id, message_id, context: ContextTypes.DEFAULT_TYPE):
        return await context.bot.delete_message(chat_id = chat_id, message_id=message_id)


    async def buy_swap_menu(self, chat_id, token_info, token_address, context: ContextTypes.DEFAULT_TYPE, message_id=None, callBackType = "", publicKey = ""):
        buy_button_text = "Swap ✅" # if buy_flag else "BUY"
        limit_button_text = "Limit" # if buy_flag else "BUY"

        buy_0_1_sol_text = "0.1 SOL" # if selected_option[chat_id]["buy"] == "0.1_sol" else "0.1 SOL"
        buy_0_5_sol_text = "0.5 SOL" # if selected_option[chat_id]["buy"] == "0.5_sol" else "0.5 SOL"
        buy_1_sol_text = "1 SOL" # if selected_option[chat_id]["buy"] == "1_sol" else "1 SOL"

        token_info_message = (
            f"Buy *{token_info['symbol']}* \\- {token_info['name']} [📈](https://dexscreener.com/{chain_id}/{token_address})\n"
            f"`{token_address}` _\\(Tap to copy\\)_ \n\n"
            f"Price: *${self.escape_dots(token_info['price_usd'])}*\n"
            f"Liquidity: *{self.escape_dots(locale.currency(token_info['liquidity_usd'], grouping=True))}*\n"
            f"FDV: *{self.escape_dots(locale.currency(token_info['fdv'], grouping=True))}*\n"
        )
        
        reply_keyboard = InlineKeyboardMarkup([
            [
                {"text": buy_button_text, "callback_data": "toggle_swap_mode"},
                {"text": limit_button_text, "callback_data": "toggle_limit_mode"}
            ],
            [
                {"text": buy_0_1_sol_text, "callback_data": "buy_0.1_sol"},
                {"text": buy_0_5_sol_text, "callback_data": "buy_0.5_sol"},
            ],
            [
                {"text": buy_1_sol_text, "callback_data": "buy_1_sol"},
                {"text": "Buy with X SOL ✏️", "callback_data": "buy_x_sol"}
            ],
        ])

        await self.send_message(chat_id, token_info_message, context, reply_keyboard,callbackType = callBackType,userFilledPubkey = publicKey, message_id = message_id)



    async def sell_swap_menu(self, chat_id, token_info, token_address, context: ContextTypes.DEFAULT_TYPE, message_id=None, callBackType = ""):
        sell_button_text = "----SELL 🔴----" # if not buy_flag else "SELL"

        sell_25_text = "Sell 25%" #if selected_option[chat_id]["sell"] == "25" else "Sell 25%"
        sell_50_text = "Sell 50%" #if selected_option[chat_id]["sell"] == "50" else "Sell 50%"
        sell_100_text = "Sell 100%" #if selected_option[chat_id]["sell"] == "100" else "Sell 100%"
        sell_x_text = "Sell X % ✏️" #if selected_option[chat_id]["sell"] == "100" else "Sell 100%"
        
        
        retrieved_user = await self.userModule.get_user_by_userId(int(chat_id))
        accInfo = self.helper.getAccountInfo(Pubkey.from_string(retrieved_user.publicKey))
        tokens = accInfo.value
        
        balance = 0
        for token in tokens:   
            info = token.account.data.parsed.get('info')
            ui_amount = info.get('tokenAmount', {}).get('uiAmount')
            mint = info.get('mint')
            if(mint == token_address):
                balance = ui_amount
        

        token_info_message = (
            f"Sell *{token_info['symbol']}* \\- {token_info['name']} [📈](https://dexscreener.com/{chain_id}/{token_address})\n"
            f"`{token_address}` _\\(Tap to copy\\)_ \n\n"
            f"Balance: *{self.escape_dots(balance)} {token_info['symbol'].upper()}*\n"
            f"Price: *${self.escape_dots(token_info['price_usd'])}*\n"
            f"Liquidity: *{self.escape_dots(locale.currency(token_info['liquidity_usd'], grouping=True))}*\n"
            f"FDV: *{self.escape_dots(locale.currency(token_info['fdv'], grouping=True))}*\n"
            # f"__Choose an action__\\:"
        )

        reply_keyboard = InlineKeyboardMarkup([
            [
                {"text": sell_button_text, "callback_data": "toggle_sell_mode"}
            ],
            [
                {"text": sell_25_text, "callback_data": "sell_25_percent"},
                {"text": sell_50_text, "callback_data": "sell_50_percent"},
            ],
            [
                {"text": sell_100_text, "callback_data": "sell_100_percent"},
                {"text": sell_x_text, "callback_data": "sell_x_percent"}
            ],

        ])

        await self.send_message(chat_id, token_info_message, context, reply_keyboard,callbackType = callBackType,userFilledPubkey = token_address)



    def encode_key(self, key: bytes) -> str:
        return base64.b64encode(key).decode('utf-8')

    def decode_key(self, encoded_key: str) -> bytes:
        return base64.b64decode(encoded_key)
    
    
    
    async def buyWithLimit(self, chat_id, context, tmpPubkey, tmpCallBackType, inputAmount, triggerAt):
        # --- buy with limit func 915114249 2orqxJdCqDLdya8AwNHti4LUt16ysojKW2UMKuYZpump buy_with_limit 0.0366262
        print('--- buy with limit func---', chat_id, tmpPubkey, tmpCallBackType, inputAmount, triggerAt)
        if not(inputAmount):
            await self.send_message(chat_id, f"__You need to enter amount to proceed__", context, None, tmpCallBackType, tmpPubkey)
            return
        if not(triggerAt):
            await self.send_message(chat_id, f"__You need to enter trigger price to proceed__", context, None, tmpCallBackType, tmpPubkey)
            return
        
        await self.send_message(chat_id, f"__OK__", context)
        return
        amount = int(inputAmount * self.one_sol_in_lamports)
        retrieved_user = await self.userModule.get_user_by_userId(int(chat_id))
        if(retrieved_user):
            sender = Keypair.from_base58_string(retrieved_user.keypair)
            if(tmpCallBackType == "transfer_token"):
                receiver =   Pubkey.from_string(tmpPubkey)
                txn = self.helper.transactionFun(sender, receiver, amount)
                msg = await self.send_message(chat_id, f"__Transferring SOL__", context)
                # await asyncio.sleep(3)
                if(txn):
                    print('txn:-',txn)
                    message = []
                    message.append(f"✅<b><a href='https://solscan.io/tx/{txn}?cluster=devnet'>SOL</a></b> transferred Successfully\n")
                    message.append(f"<b>Sender</b>: <i><code>{sender.pubkey()}</code></i>\n")
                    message.append(f"<b>Receiver</b>: <i><code>{receiver}</code></i>\n")
                    message.append(f"Amount: <b>{inputAmount} SOL</b>\n")
                    formatted_message = "\n".join(message)
                    await self.edit_message_text(text=formatted_message, chat_id = chat_id, message_id = msg.message_id, context = context, parseMode=ParseMode.HTML)
                else:
                    await self.send_message(chat_id, f"🔴 Insufficient Balance", context)
            elif(tmpCallBackType == "buy_token"):
                msg = await self.send_message(chat_id, f"__Processing swap__", context)

                # tmpJupiterHel = self.jupiterHelper.initializeJup(sender)
                self.solanaSwapModule.initializeTracker(sender)
                slippage = 100  # 1% slippage in basis points
                jup_txn_id = await self.solanaSwapModule.execute_swap(tmpPubkey, inputAmount, slippage, sender, constant.input_mint)
                # jup_txn_id = await self.solanaSwapModule.execute_swap(tmpPubkey, inputAmount, slippage, sender, constant.input_mint)
                # jup_txn_id = await self.jupiterHelper.execute_swap(tmpPubkey, amount, slippage, sender)
                if not jup_txn_id:
                    print('txn failed>>>>>>')
                    await self.edit_message_text(text=f"There is some technical issue while buying the token", chat_id = chat_id, message_id = msg.message_id, context = context)
                else:
                    await self.edit_message_text(text=f"_🟢 Buy Success\\!_ [View on Solscan](https://solscan.io/tx/{jup_txn_id})", chat_id = chat_id, message_id = msg.message_id, context = context)
            
        else:
            await self.send_message(chat_id, f"You don\'t have any wallet to send SOL", context)

    
    async def buyToken(self, chat_id, context, tmpPubkey, tmpCallBackType, inputAmount):
        amount = int(inputAmount * self.one_sol_in_lamports)
        retrieved_user = await self.userModule.get_user_by_userId(int(chat_id))
        if(retrieved_user):
            sender = Keypair.from_base58_string(retrieved_user.keypair)
            if(tmpCallBackType == "transfer_token"):
                receiver =   Pubkey.from_string(tmpPubkey)
                txn = self.helper.transactionFun(sender, receiver, amount)
                msg = await self.send_message(chat_id, f"__Transferring SOL__", context)
                # await asyncio.sleep(3)
                if(txn):
                    print('txn:-',txn)
                    message = []
                    message.append(f"✅<b><a href='https://solscan.io/tx/{txn}?cluster=devnet'>SOL</a></b> transferred Successfully\n")
                    message.append(f"<b>Sender</b>: <i><code>{sender.pubkey()}</code></i>\n")
                    message.append(f"<b>Receiver</b>: <i><code>{receiver}</code></i>\n")
                    message.append(f"Amount: <b>{inputAmount} SOL</b>\n")
                    formatted_message = "\n".join(message)
                    await self.edit_message_text(text=formatted_message, chat_id = chat_id, message_id = msg.message_id, context = context, parseMode=ParseMode.HTML)
                else:
                    await self.send_message(chat_id, f"🔴 Insufficient Balance", context)
            # elif(tmpCallBackType == "buy_token"):
            else:
                msg = await self.send_message(chat_id, f"__Processing swap__", context)

                # tmpJupiterHel = self.jupiterHelper.initializeJup(sender)
                self.solanaSwapModule.initializeTracker(sender)
                slippage = 100  # 1% slippage in basis points
                jup_txn_id = await self.solanaSwapModule.execute_swap(tmpPubkey, inputAmount, slippage, sender, constant.input_mint)
                # jup_txn_id = await self.solanaSwapModule.execute_swap(tmpPubkey, inputAmount, slippage, sender, constant.input_mint)
                # jup_txn_id = await self.jupiterHelper.execute_swap(tmpPubkey, amount, slippage, sender)
                if not jup_txn_id:
                    print('txn failed>>>>>>')
                    await self.edit_message_text(text=f"There is some technical issue while buying the token", chat_id = chat_id, message_id = msg.message_id, context = context)
                else:
                    await self.edit_message_text(text=f"_🟢 Buy Success\\!_ [View on Solscan](https://solscan.io/tx/{jup_txn_id})", chat_id = chat_id, message_id = msg.message_id, context = context)
                

        else:
            await self.send_message(chat_id, f"You don\'t have any wallet to send SOL", context)

    async def sellTokenFunc(self, chat_id, context, callback_data):
        context.chat_data["callbackType"] = callback_data
        msg = await self.send_message(chat_id, f"_Fetching your tokens\\.\\.\\._", context)
        retrieved_user = await self.userModule.get_user_by_userId(int(chat_id))
        accInfo = self.helper.getAccountInfo(Pubkey.from_string(retrieved_user.publicKey))
        tokens = accInfo.value
        
        formatted_message = []
        formatted_message.append(f"<b>Select a token to sell</b>")
        
        message = "You don't have any token"
        for token in tokens:   
            info = token.account.data.parsed.get('info')
            token_amount = info.get('tokenAmount', {}).get('amount')
            if int(token_amount) > 0:
                ui_amount = info.get('tokenAmount', {}).get('uiAmount')
                mint = info.get('mint')
                token_info = self.get_token_info(mint) # need to find another way to get token Symbol
                if token_info: 
                    response = requests.get('https://api.raydium.io/v2/main/price')
                    response.raise_for_status()  # Check for HTTP errors
                    price_list = response.json()
                    sol_curr_price = price_list[self.sol_address]
                    curr_price_of_token = price_list.get(mint, None)
                    
                    if(curr_price_of_token == None):
                        curr_price_of_token = token_info['price_usd']
                    
                    price_of_owned_token = float(curr_price_of_token) * float(ui_amount)
                    rounded_price_of_owned_token = round(price_of_owned_token, 6)
                
                    qty_in_sol = rounded_price_of_owned_token / sol_curr_price
                    
                    formatted_message.append(f"<b><a href='https://t.me/{constant.bot_name}?start=sellToken-{mint}'>{str(token_info['symbol']).upper()}</a> ➖</b> {qty_in_sol:.6f} SOL - (${rounded_price_of_owned_token:.2f})")
    
                            
        # print('total_owned_sol',total_owned_sol,toatl_owned_sol_price)
        res = self.getBalance(retrieved_user.publicKey)
        formatted_message.insert(1, f"Balance: <b>{res.get('sol_bal')} SOL (${res.get('usd_bal')})</b>\n")
        message = "\n".join(formatted_message)

        await self.edit_message_text(text=message, chat_id = chat_id, message_id = msg.message_id, context = context, parseMode=ParseMode.HTML)

    async def getSubmenuKeyboard(self, chat_id):
        retrieved_user = await self.userModule.get_user_by_userId(int(chat_id))
        
        appended_submenu_keyboard = [
            [
                InlineKeyboardButton("Export Private Key", callback_data='export_private_key')
            ],
            [
                InlineKeyboardButton("Check Balance", callback_data='get_balance'),
                InlineKeyboardButton("Withdraw SOL", callback_data='withdraw_sol'),
            ],
        ]

        if (retrieved_user == None):
            submenu_keyboard = [
                [
                    InlineKeyboardButton("Generate Wallet", callback_data='generate_wallet'),
                    InlineKeyboardButton("Back", callback_data='back_to_main')
                ]
            ]

        else:
            submenu_keyboard = [
                [
                    InlineKeyboardButton("View Wallet", callback_data='generate_wallet'),
                    InlineKeyboardButton("Back", callback_data='back_to_main'),
                ],
            ]
        appended_submenu_keyboard.extend(submenu_keyboard)
        return appended_submenu_keyboard


    async def sellToken(self, chat_id, context, token_to_sell, sellPercent):        
        print("SELLLLLTOKEN", sellPercent, token_to_sell)

        retrieved_user = await self.userModule.get_user_by_userId(int(chat_id))
        if(retrieved_user):
            accInfo = self.helper.getAccountInfo(Pubkey.from_string(retrieved_user.publicKey))
            tokens = accInfo.value
            
            balance = 0
            for token in tokens:   
                info = token.account.data.parsed.get('info')
                mint = info.get('mint')
                if(mint == token_to_sell):
                    balance = info.get('tokenAmount', {}).get('uiAmount')
            
            sender = Keypair.from_base58_string(retrieved_user.keypair)
            msg = await self.send_message(chat_id, f"__Processing swap__", context)
            
            amount = float(balance * sellPercent)
            # tmpJupiterHel = self.jupiterHelper.initializeJup(sender)
            self.solanaSwapModule.initializeTracker(sender)
            slippage = 100  # 1% slippage in basis points
            jup_txn_id = await self.solanaSwapModule.execute_swap(constant.input_mint, amount, slippage, sender, token_to_sell) # first param is TO token , last param is FROM token
            
            # jup_txn_id = await self.jupiterHelper.execute_swap(tmpPubkey, amount, slippage, sender)
            if not jup_txn_id:
                print('txn failed>>>>>>')
                await self.edit_message_text(text=f"There is some technical issue while selling the token", chat_id = chat_id, message_id = msg.message_id, context = context)
            else:
                await self.edit_message_text(text=f"_🟢 Sell Success\\!_ [View on Solscan](https://solscan.io/tx/{jup_txn_id})", chat_id = chat_id, message_id = msg.message_id, context = context)
            

        else:
            await self.send_message(chat_id, f"You don\'t have any wallet to send SOL", context)

    async def listToken(self, chat_id, context):    

        msg = await self.send_message(chat_id, f"_Fetching your positions\\.\\.\\._", context)
        
        retrieved_user = await self.userModule.get_user_by_userId(int(chat_id))
        # retrieved_user = await self.userModule.get_user_by_userId(int(922898192))
        accInfo = self.helper.getAccountInfo(Pubkey.from_string(retrieved_user.publicKey))
        print('accInfo',accInfo)
        tokens = accInfo.value
        
        formatted_message = []
        formatted_message.append(f"<b>Manage your tokens</b>\nWallet: <code>{retrieved_user.publicKey}</code>\n")
        
        message = "No information found for tokens"
        total_owned_sol = 0
        toatl_owned_sol_price = 0
        for token in tokens:   
            info = token.account.data.parsed.get('info')
            token_amount = info.get('tokenAmount', {}).get('amount')
            if int(token_amount) > 0:
                ui_amount = info.get('tokenAmount', {}).get('uiAmount')
                mint = info.get('mint')
                token_info = self.get_token_info(mint)
                if token_info: 
                    response = requests.get('https://api.raydium.io/v2/main/price')
                    response.raise_for_status()  # Check for HTTP errors
                    price_list = response.json()
                    sol_curr_price = price_list[self.sol_address]
                    curr_price_of_token = price_list.get(mint, None)
                    
                    if(curr_price_of_token == None):
                        curr_price_of_token = token_info['price_usd']
                    
                    price_of_owned_token = float(curr_price_of_token) * float(ui_amount)
                    rounded_price_of_owned_token = round(price_of_owned_token, 6)
                    
                    qty_in_sol = rounded_price_of_owned_token / sol_curr_price
                    total_owned_sol = total_owned_sol + qty_in_sol
                    toatl_owned_sol_price = toatl_owned_sol_price + rounded_price_of_owned_token
                    
                    formatted_message.append(f"<b><a href='https://t.me/{constant.bot_name}?start=sellToken-{mint}'>{str(token_info['symbol']).upper()} - 📈</a></b> {qty_in_sol:.6f} SOL - (${rounded_price_of_owned_token:.2f})")
                    formatted_message.append(f"<code>{mint}</code>")
                    formatted_message.append(f"● Price: <b>${token_info['price_usd']}</b>")
                    formatted_message.append(f"● Amount (owned): <b>{ui_amount:.6f}</b> {str(token_info['symbol']).upper()}\n")
                                
        res = self.getBalance(retrieved_user.publicKey)
        formatted_message.insert(1, f"Balance: <b>{res.get('sol_bal')} SOL (${res.get('usd_bal')})</b>")
        formatted_message.insert(2, f"Positions: <b>{total_owned_sol:.6f} SOL (${toatl_owned_sol_price:.2f})</b>\n")
        message = "\n".join(formatted_message)
        
        await self.edit_message_text(text=message, chat_id = chat_id, message_id = msg.message_id, context = context, parseMode=ParseMode.HTML)


    async def listOrders(self, chat_id, context):    

        msg = await self.send_message(chat_id, f"_Fetching your orders\\.\\.\\._", context)
        
        retrieved_user = await self.userModule.get_user_by_userId(int(chat_id))
        if(retrieved_user):
            sender = Keypair.from_base58_string(retrieved_user.keypair)
            self.jupiterHelper.initializeJup(sender)
            orderList = await self.jupiterHelper.query_orders_history(retrieved_user.publicKey)
            # tokens = orderList.value
            
            formatted_message = []
            
            message = "No order found for the token"
            for order in orderList:   
                account = order.get('account')
                token_public_key = order.get('publicKey')
                # print("account>>>>>>>>>>>>>>>>>>>", account)
                # token_amount = info.get('tokenAmount', {}).get('amount')
                token_mint = account["inputMint"]
                orderType = "Sell "
                sol_amount = float(int(account["oriOutAmount"]) / self.one_sol_in_lamports)
                token_amount = account["oriInAmount"]
                if (account["inputMint"]  == self.sol_address ):
                    # print('order is buy type')
                    # global token_mint
                    token_mint = account["outputMint"]
                    orderType = "Buy "
                    sol_amount = float(int(account["oriInAmount"]) / self.one_sol_in_lamports)
                    token_amount = account["oriOutAmount"]
                    
                # else:
                #     print('order is sell type')


                # ui_amount = info.get('tokenAmount', {}).get('uiAmount')
                # mint = info.get('mint')
                token_info = self.get_token_info(token_mint)
                if token_info: 
                    response = requests.get('https://api.raydium.io/v2/main/price')
                    response.raise_for_status()  # Check for HTTP errors
                    price_list = response.json()
                    # sol_curr_price = price_list[self.sol_address]
                    curr_price_of_token = price_list.get(token_mint, None)
                    
                    if(curr_price_of_token == None):
                        curr_price_of_token = token_info['price_usd']
                    
                    tmp_decimal = self.jupiterHelper.get_token_decimal_info(token_mint)
                    # print("tmp_decimal>>>>>>>>>>>>>>>>>", tmp_decimal)

                    if(tmp_decimal):
                        token_amount = float(int(token_amount)/pow(10, int(tmp_decimal)))
                    
                    formatted_message.append(f"{orderType} :  <b>{str(token_info['symbol']).upper()} 📈 </b> - <b><a href='https://t.me/{constant.bot_name}?start=cancelOrder-{token_public_key}'>CANCEL</a></b> ")
                    
                    formatted_message.append(f"<code>{token_mint}</code>")
                    formatted_message.append(f"● SOl: <b>{sol_amount:.6f}</b>")
                    formatted_message.append(f"● Price(USD): <b>${token_info['price_usd']}</b>")
                    formatted_message.append(f"● Trigger price: <b>${token_amount}</b>")
                # print('token_mint>>>>>>>>>>>>', token_mint)

            message = "\n".join(formatted_message)
            
            await self.edit_message_text(text=message, chat_id = chat_id, message_id = msg.message_id, context = context, parseMode=ParseMode.HTML)

        else:
            await self.send_message(chat_id, f"You don\'t have any wallet to view Order List", context, message_id = msg.message_id)




if __name__ == '__main__':
    bot = Bot()
    bot.main()
#     main()
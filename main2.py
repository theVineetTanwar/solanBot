import asyncio
import os
import re
from pydantic import BaseModel, Field, field_validator # v2 needed
import requests
import locale
import time
import datetime

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
import datetime
from utils import Utils

load_dotenv()

dbURI = os.getenv("dbURI")
TOKEN = os.getenv("TOKEN")
# SHYFT_API_KEY = os.getenv("SHYFT_API_KEY")
mongoClient = MongoClient(dbURI)
db = mongoClient.telegram 
wallet_collection = db.wallet 


chain_id = "solana"  # Change to the appropriate chain ID
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8') 


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
        self.utils = Utils(self.send_message, self.delete_message, self.edit_message_text,  self.userModule, self.jupiterHelper)

    
    
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
        await self.utils.listOrders(chat_id, context)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # reply_markup = InlineKeyboardMarkup(self.utils.main_keyboard)
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
                token_info = self.utils.get_token_info(token_to_sell)
                if token_info:
                    context.chat_data["limitOrderType"] = "sell"
                    await self.utils.sell_swap_menu(chat_id, token_info, token_to_sell, context, message_id=update.message.message_id, callBackType="sell_token")
                else:
                    await self.send_message(chat_id, f"Token information not found for address: {token_to_sell}", context)
            
            elif(cb_type == "cancelOrder"):
                try:
                    retrieved_user = await self.userModule.get_user_by_userId(int(chat_id))
                    if(retrieved_user):
                        sender = Keypair.from_base58_string(retrieved_user.keypair)
                        tmpJupiterHel = JupiterHelper(sender)
                        # tmpData = tmpJupiterHel.cancel_orders([token_to_sell], sender)
                        txn_id = await tmpJupiterHel.cancel_orders([token_to_sell], sender)
                        
                        if not txn_id:
                            await self.send_message(message=f"There is some technical issue while cancelling order", chat_id = chat_id, context = context)
                        else:
                            await self.send_message(message=f"_🟢 Order cancelled succussfully\\!_ [View on Solscan](https://solscan.io/tx/{txn_id})", chat_id = chat_id,  context = context)
                        

                except Exception as err:
                    print("error while cancelling order-----", err)
                    await self.send_message(chat_id, f"Some technical issue while canceling order, Please try again:", context)
            await self.delete_message(chat_id, message_id , context)
            # await update.message.reply_text('Hello! This is Crypto Bot.', reply_markup=reply_markup)
        else:
            reply_markup = InlineKeyboardMarkup(self.utils.main_keyboard)
            await update.message.reply_text('Hello! This is Crypto Bot.', reply_markup=reply_markup)


    async def button_click_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        chat_id = query.from_user.id
        message_id = query.message.message_id
        await query.answer()
        callback_data = query.data
        tmpCallBackType = context.chat_data.get("callbackType", '') or ""
        tmpPubkey = context.chat_data.get("pubKey", '') or ""
        
        sub_callbackType = None
        cb_data = tmpCallBackType.split(':')
        if (len(cb_data) > 1):
            tmpCallBackType = cb_data[0]
            sub_callbackType = cb_data[1]

        print("tmpCallBackType in btn click callback----",context.chat_data)

        if callback_data == 'wallet':
            tmp_menu = await self.utils.getSubmenuKeyboard(chat_id)
            submenu_reply_markup = InlineKeyboardMarkup(tmp_menu)
            context.chat_data["callbackType"] = callback_data
            await query.edit_message_text(text="Manage Your Wallet", reply_markup=submenu_reply_markup)
        elif callback_data == 'buy_token':
            context.chat_data["callbackType"] = callback_data
            context.chat_data["limitOrderType"] = "buy"
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
            main_reply_markup = InlineKeyboardMarkup(self.utils.main_keyboard)
            await query.edit_message_text(text="Hello! This is Crypto Bot, how can I help.", reply_markup=main_reply_markup)
        elif callback_data == 'generate_wallet':
            retrieved_user = await self.userModule.get_user_by_userId(int(chat_id))
            if (retrieved_user == None):
                keypair = Keypair()
                # private_key = str(keypair.secret())
                private_key = self.utils.encode_key(keypair.secret())
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
                # pk = self.utils.decode_key(str(retrieved_user.privateKey))
                print('retrieved_user',retrieved_user)
                print('private key',retrieved_user.keypair)
                await self.send_message(chat_id, f"*Private Key*: _`{retrieved_user.keypair}`_ \\(Tap to copy\\)", context)
            else:
                await self.send_message(chat_id, f"You don\\'t have any wallet", context)
        elif callback_data == 'get_balance':
            retrieved_user = await self.userModule.get_user_by_userId(int(chat_id))
            if(retrieved_user):
                try:
                    res = self.utils.getBalance(retrieved_user.publicKey)
                    
                    message = (
                        f"*Wallet Balance*\n"
                        f"`{retrieved_user.publicKey}` _\\(Tap to copy\\)_ \n"
                        f"Balance: *{self.utils.escape_dots(res.get('sol_bal'))} SOL  \\(${self.utils.escape_dots(res.get('usd_bal'))}*\\)"
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
        elif callback_data == 'buy_limit_0.1_sol':
            print("buy_limit_0.1_sol , tmpCallBackType-",tmpCallBackType, tmpPubkey)
            context.chat_data["limitAmount"] = 0.1
            context.chat_data["lastBuyMenuMsgId"] = message_id
            context.chat_data["callbackType"] = "buy_with_limit"

            updated_markup = InlineKeyboardMarkup(self.utils.getBuyLimitKeyboard(context.chat_data))
            await self.edit_message_reply_markup(chat_id = chat_id, message_id = message_id, context = context, reply_keyboard=updated_markup)
        elif callback_data == 'buy_limit_0.5_sol':
            print("buy_limit_0.5_sol , tmpCallBackType-",tmpCallBackType, tmpPubkey)
            context.chat_data["limitAmount"] = 0.5
            context.chat_data["lastBuyMenuMsgId"] = message_id
            context.chat_data["callbackType"] = "buy_with_limit"
            
            updated_markup = InlineKeyboardMarkup(self.utils.getBuyLimitKeyboard(context.chat_data))
            await self.edit_message_reply_markup(chat_id = chat_id, message_id = message_id, context = context, reply_keyboard=updated_markup)
        elif callback_data == 'buy_limit_1_sol':
            print("buy_limit_1_sol , tmpCallBackType-",tmpCallBackType, tmpPubkey)
            context.chat_data["limitAmount"] = 1
            context.chat_data["lastBuyMenuMsgId"] = message_id
            context.chat_data["callbackType"] = "buy_with_limit"

            updated_markup = InlineKeyboardMarkup(self.utils.getBuyLimitKeyboard(context.chat_data))
            await self.edit_message_reply_markup(chat_id = chat_id, message_id = message_id, context = context, reply_keyboard=updated_markup)
        elif callback_data == 'buy_limit_x_sol':
            print("buy_limit_x_sol , tmpCallBackType-",tmpCallBackType, tmpPubkey)
            context.chat_data["lastBuyMenuMsgId"] = message_id
            context.chat_data["callbackType"] = "buy_with_limit"
            await self.send_message(chat_id, f"Please enter the amount of SOL you want to swap:", context, None, "buy_with_limit", tmpPubkey)    
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
        elif callback_data == 'toggle_buy_swap_mode':
            context.chat_data["callbackType"] = 'buy_token'
            print('toggle_buy_swap_mode',tmpCallBackType)
            updated_markup = InlineKeyboardMarkup(self.utils.buy_swap_keyboard)
            await self.edit_message_reply_markup(chat_id = chat_id, message_id = message_id, context = context, reply_keyboard=updated_markup)
        elif callback_data == 'toggle_buy_limit_mode':
            print('toggle_buy_limit_mode',tmpCallBackType)
            context.chat_data["callbackType"] = 'buy_with_limit'
            updated_markup = InlineKeyboardMarkup(self.utils.getBuyLimitKeyboard(context.chat_data))
            await self.edit_message_reply_markup(chat_id = chat_id, message_id = message_id, context = context, reply_keyboard=updated_markup)
        elif callback_data == 'buy_trigger_at':
            context.chat_data["callbackType"] = 'buy_with_limit:trigger_at'
            context.chat_data["lastBuyMenuMsgId"] = message_id
            tmpCallBackType = context.chat_data.get("callbackType", '') or ""
            print('buy_trigger_at',tmpCallBackType)
            await self.send_message(chat_id, f"Enter the trigger price of your limit buy order. Valid options are % change (e.g. -5% or 5%) or a specific price.", context, None, tmpCallBackType, tmpPubkey, parseMode=ParseMode.HTML)
        elif callback_data == 'buy_expire_at':
            context.chat_data["callbackType"] = 'buy_with_limit:expire_at'
            context.chat_data["lastBuyMenuMsgId"] = message_id
            tmpCallBackType = context.chat_data.get("callbackType", '') or ""
            print('buy_expire_at',tmpCallBackType)
            await self.send_message(chat_id, f"Enter the expiry of your limit buy order. Valid options are s (seconds), m (minutes), h (hours), and d (days). E.g. 30m or 2h", context, None, tmpCallBackType, tmpPubkey, parseMode=ParseMode.HTML)
        elif callback_data == 'buy_create_order':
            print('buy_create_order',tmpCallBackType, "context.chat_data.>>>>>>>>>>>>>>>>>>>", context.chat_data)
            limitAmount = context.chat_data.get("limitAmount", '') or 0
            triggerAt = context.chat_data.get("triggerAt", '') or 0
            expireAt = context.chat_data.get("expireAt", '') or 0

            if('limitOrderType' in context.chat_data and context.chat_data["limitOrderType"] == 'sell'):
                await self.sellWithLimit(chat_id, context, tmpPubkey, tmpCallBackType, limitAmount, triggerAt, expireAt)
            else:
                await self.buyWithLimit(chat_id, context, tmpPubkey, tmpCallBackType, limitAmount, triggerAt, expireAt)
        



    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        response = f"{text}"
        chat_type = update.message.chat.type
        chat_id = update.message.chat.id
        tmpCallBackType = context.chat_data.get("callbackType", '') or ""
        tmpPubkey = context.chat_data.get("pubKey", '') or ""
        # print('-handleMessage: tmpCallBackType',tmpCallBackType)
        
        if chat_type == "private":
            # Capture any word over 32 characters
            token_addresses = re.findall(r'\b\w{33,}\b', text)
            # print('token_addresses-', token_addresses)
            
            # Regex to capture Solana public keys
            public_key_match = re.findall(r'\b[A-HJ-NP-Za-km-z1-9]{44}\b', text)
            # print('public_key_match-', public_key_match)
            
            cb_data = tmpCallBackType.split(':')
            sub_callbackType = None
            if (len(cb_data) > 1):
               tmpCallBackType = cb_data[0]
               sub_callbackType = cb_data[1]
            
            print('-handleMessage: tmpCallBackType',tmpCallBackType)
            print('-handleMessage: sub_callbackType',sub_callbackType)

            if public_key_match:
                public_key = public_key_match[0]
                print('-public_key', public_key)

                if(tmpCallBackType == "transfer_token"):
                    await self.send_message(chat_id, f"Enter amount to proceed for token: \n_{public_key}_", context, None, tmpCallBackType, public_key)
                
                else:                 
                    token_address = token_addresses[0]
                    print('-address', token_address)
                    token_info = self.utils.get_token_info(token_address)
                    if token_info:
                        context.chat_data["limitOrderType"] = "buy"
                        await self.utils.buy_swap_menu(chat_id, token_info, token_address, context, message_id=update.message.message_id, callBackType = tmpCallBackType, publicKey = public_key)
                    else:
                        await self.send_message(chat_id, f"Token information not found for address: {token_address}", context)

            # checks amount 
            elif re.match(r'^\d*\.?\d+$', text):
                inputAmount = float(text)

                if(not(tmpCallBackType == "buy_token" or tmpCallBackType == "transfer_token" or tmpCallBackType == "sell_token" or tmpCallBackType == "buy_with_limit")):
                    await self.send_message(chat_id, f"You have not selected transaction type for the transaction" , context, None, tmpCallBackType, tmpPubkey)
                    return
                
                if(not(re.findall(r'\b[A-HJ-NP-Za-km-z1-9]{44}\b', tmpPubkey) )):
                    await self.send_message(chat_id, f"No public key has been setup for txn" + tmpPubkey, context, None, tmpCallBackType, tmpPubkey)
                    return
                
                if(tmpPubkey is not None and tmpCallBackType == "sell_token"):
                    await self.sellToken(chat_id, context, tmpPubkey, inputAmount)
                    return
                
                if(tmpPubkey is not None and tmpCallBackType == "buy_with_limit"):
                    if(sub_callbackType == "trigger_at"):
                        context.chat_data["triggerAt"] = inputAmount
                    else:
                        context.chat_data["limitAmount"] = inputAmount

                    tmp_pub_key = context.chat_data["pubKey"]
                    token_info = self.utils.get_token_info(tmp_pub_key)
                    print('toggle_swap_mode',tmpCallBackType)
                    await self.utils.buy_swap_menu(chat_id, token_info, tmp_pub_key, context, message_id=update.message.message_id, callBackType = tmpCallBackType, publicKey = tmp_pub_key, is_limit_order_menu = True, chat_data = context.chat_data) 
                    return

                if(tmpPubkey is not None and (tmpCallBackType == "buy_token" or tmpCallBackType == 'transfer_token')):
                    await self.buyToken(chat_id, context, tmpPubkey, tmpCallBackType, inputAmount)
                else:
                    print('---else',context)
                    await self.send_message(chat_id, f"Enter receiver\\'s public key", context)
            # checks Percentage
            
            elif re.match(r'(-?\d+(\.\d+)?)%', text):
                if(not(tmpCallBackType == "buy_with_limit")):
                    await self.send_message(chat_id, f"You have not selected transaction type for the transaction" , context, None, tmpCallBackType, tmpPubkey)
                    return
                
                if(not(re.findall(r'\b[A-HJ-NP-Za-km-z1-9]{44}\b', tmpPubkey) )):
                    await self.send_message(chat_id, f"No public key has been setup for txn" + tmpPubkey, context, None, tmpCallBackType, tmpPubkey)
                    return
                
                print('percentage-', text)
                if(tmpPubkey is not None and tmpCallBackType == "buy_with_limit" and sub_callbackType == "trigger_at"):
                    print('toggle_swap_mode',tmpCallBackType)
                    triggerPercent = float(text.strip('%'))
                    tmp_pub_key = context.chat_data["pubKey"]
                    
                    token_info = self.utils.get_token_info(tmp_pub_key)                 
                    if token_info: 
                        curr_price_of_token = token_info['price_usd']
                        triggerAt = float(curr_price_of_token) * (1 + float(triggerPercent) / 100) # getting trigger price(in USD) from percent

                        context.chat_data["triggerAt"] = f"{float(triggerAt):.8f}"
                        await self.utils.buy_swap_menu(chat_id, token_info, tmp_pub_key, context, message_id=update.message.message_id, callBackType = tmpCallBackType, publicKey = tmp_pub_key, is_limit_order_menu = True, chat_data = context.chat_data) 
                    
                    return
            # checks Expiry
            elif re.match(r"(\d+)([smhd])", text):
                if(not(tmpCallBackType == "buy_with_limit")):
                    await self.send_message(chat_id, f"You have not selected transaction type for the transaction" , context, None, tmpCallBackType, tmpPubkey)
                    return
                
                if(not(re.findall(r'\b[A-HJ-NP-Za-km-z1-9]{44}\b', tmpPubkey) )):
                    await self.send_message(chat_id, f"No public key has been setup for txn" + tmpPubkey, context, None, tmpCallBackType, tmpPubkey)
                    return
                
                print('expiry-', text)
                if(tmpPubkey is not None and tmpCallBackType == "buy_with_limit" and sub_callbackType == "expire_at"):
                    context.chat_data["expireAt"] = text 
                    tmp_pub_key = context.chat_data["pubKey"]
                    token_info = self.utils.get_token_info(tmp_pub_key)
                    # print('toggle_swap_mode',tmpCallBackType)
                    
                    await self.utils.buy_swap_menu(chat_id, token_info, tmp_pub_key, context, message_id=update.message.message_id, callBackType = tmpCallBackType, publicKey = tmp_pub_key, is_limit_order_menu = True, chat_data = context.chat_data) 
                    return
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


    async def edit_message_reply_markup(self, chat_id, message_id, context: ContextTypes.DEFAULT_TYPE, reply_keyboard=None):
        try:
            return await context.bot.edit_message_reply_markup(chat_id = chat_id, message_id=message_id, reply_markup=reply_keyboard)
        except Exception as err:
            print(f"Other error occurred: {err}")


    async def delete_message(self, chat_id, message_id, context: ContextTypes.DEFAULT_TYPE):
        return await context.bot.delete_message(chat_id = chat_id, message_id=message_id)

    async def sellWithLimit(self, chat_id, context, tmpPubkey, tmpCallBackType, inputAmount, triggerAt, expireAt):
        print('--- sell with limit func---', chat_id, tmpPubkey, tmpCallBackType, inputAmount, triggerAt, expireAt)
        if not(inputAmount):
            await self.send_message(chat_id, f"__You need to enter amount to proceed__", context, None, tmpCallBackType, tmpPubkey)
            return
        if not(triggerAt):
            await self.send_message(chat_id, f"__You need to enter trigger price to proceed__", context, None, tmpCallBackType, tmpPubkey)
            return
        
        try:
            
            retrieved_user = await self.userModule.get_user_by_userId(int(chat_id))
            if(retrieved_user):
                sender = Keypair.from_base58_string(retrieved_user.keypair)
                msg = await self.send_message(chat_id, f"_Placing order_\\.\\.\\.",  context, None, tmpCallBackType, tmpPubkey)
                tmpJupiterHel = JupiterHelper(sender)
    
                input_mint = constant.input_mint
                output_mint = tmpPubkey
                in_amount = int(inputAmount * self.one_sol_in_lamports)
                
                output_token_decimal = tmpJupiterHel.get_token_decimal_info(tmpPubkey)
                if not output_token_decimal:
                    print('output token decimals not found >>>>>>')
                    await self.edit_message_text(text=f"Couldn't create order for this token", chat_id = chat_id, message_id = msg.message_id, context = context)
                    
                    
                triggerPercent = None
                if (re.match(r'(-?\d+(\.\d+)?)%', str(triggerAt))):
                    triggerPercent = float(triggerAt.strip('%'))
                
                print ('triggerPercent',triggerPercent)
                
                now = datetime.datetime.now()
                one_day = now + datetime.timedelta(hours=24)
                timestamp = int(time.mktime(one_day.timetuple())) # default set to one day
                
                if (expireAt):
                    match = re.match(r"(\d+)([smhd])", expireAt)
                    value, unit = match.groups()
                    if(unit == "s"):
                        t = now + datetime.timedelta(seconds=int(value))
                    elif(unit == "m"):
                        t = now + datetime.timedelta(minutes=int(value))
                    elif(unit == "h"):
                        t = now + datetime.timedelta(hours=int(value))
                    elif(unit == "d"):
                        t = now + datetime.timedelta(days=int(value))
                        
                    timestamp = int(time.mktime(t.timetuple()))
                    print ('expiry ', int(value), unit)
                    
                    
                print ('timestamp', timestamp)
                                
                token_info = self.utils.get_token_info(tmpPubkey) # need to find another way to get token Symbol
                if token_info: 
                    curr_price_of_token = token_info['price_usd']
                        
                        
                    if(triggerPercent):
                        triggerAt = float(curr_price_of_token) * (1 + float(triggerPercent) / 100) # getting trigger price from percent
                        
                    # print('curr_price_of_token-----------------',f"{curr_price_of_token:.8f}")
                    # print('triggerAt-----------------',f"{triggerAt:.8f}")
    
                    no_of_tokens = float(triggerAt) / float(curr_price_of_token) # getting number of tokens can be bought from with given price (here:- triggerAt is price in usd)
                    out_amount = int(no_of_tokens * (10 ** output_token_decimal)) 
                    
                    print('no_of_tokens-----------------',no_of_tokens)
                    print('out_amount-----------------',out_amount)
                    print ('input_mint, output_mint, in_amount, out_amount, sender',input_mint, output_mint, in_amount, out_amount)
                    
                    jup_txn_id = await tmpJupiterHel.create_order(input_mint, output_mint, in_amount, out_amount, sender, timestamp) # need to send slippage too
        
                    if not jup_txn_id:
                        print('txn failed>>>>>>')
                        await self.edit_message_text(text=f"There is some technical issue while creating order", chat_id = chat_id, message_id = msg.message_id, context = context)
                    else:
                        await self.edit_message_text(text=f"_🟢 Order Placed\\!_ [View on Solscan](https://solscan.io/tx/{jup_txn_id})", chat_id = chat_id, message_id = msg.message_id, context = context)
            
            else:
                await self.send_message(chat_id, f"You don\'t have any wallet to create order", context)
        except Exception as err:
            print("Error while Buying Limit Order-----", err)
            await self.send_message(chat_id, f"Buying Limit Order Failed\\.\\.\\.",  context, None, tmpCallBackType, tmpPubkey)
    
    async def buyWithLimit(self, chat_id, context, tmpPubkey, tmpCallBackType, inputAmount, triggerAt, expireAt):
        print('--- buy with limit func---', chat_id, tmpPubkey, tmpCallBackType, inputAmount, triggerAt, expireAt)
        if not(inputAmount):
            await self.send_message(chat_id, f"__You need to enter amount to proceed__", context, None, tmpCallBackType, tmpPubkey)
            return
        if not(triggerAt):
            await self.send_message(chat_id, f"__You need to enter trigger price to proceed__", context, None, tmpCallBackType, tmpPubkey)
            return
        if not(expireAt):
            await self.send_message(chat_id, f"__You need to enter expiry time to proceed__", context, None, tmpCallBackType, tmpPubkey)
            return
        
        print('ready for buy ')
        # return 
        try:
            
            retrieved_user = await self.userModule.get_user_by_userId(int(chat_id))
            if(retrieved_user):
                sender = Keypair.from_base58_string(retrieved_user.keypair)
                msg = await self.send_message(chat_id, f"_Placing order_\\.\\.\\.",  context, None, tmpCallBackType, tmpPubkey)
                tmpJupiterHel = JupiterHelper(sender)
    
                input_mint = constant.input_mint
                output_mint = tmpPubkey
                in_amount = int(inputAmount * self.one_sol_in_lamports)
                
                output_token_decimal = tmpJupiterHel.get_token_decimal_info(tmpPubkey)
                if not output_token_decimal:
                    print('output token decimals not found >>>>>>')
                    await self.edit_message_text(text=f"Couldn't create order for this token", chat_id = chat_id, message_id = msg.message_id, context = context)
                    
                    
                triggerPercent = None
                if (re.match(r'(-?\d+(\.\d+)?)%', str(triggerAt))):
                    triggerPercent = float(triggerAt.strip('%'))
                
                print ('triggerPercent',triggerPercent)
                
                now = datetime.datetime.now()
                one_day = now + datetime.timedelta(hours=24)
                timestamp = int(time.mktime(one_day.timetuple())) # default set to one day
                
                if (expireAt):
                    match = re.match(r"(\d+)([smhd])", expireAt)
                    value, unit = match.groups()
                    if(unit == "s"):
                        t = now + datetime.timedelta(seconds=int(value))
                    elif(unit == "m"):
                        t = now + datetime.timedelta(minutes=int(value))
                    elif(unit == "h"):
                        t = now + datetime.timedelta(hours=int(value))
                    elif(unit == "d"):
                        t = now + datetime.timedelta(days=int(value))
                        
                    timestamp = int(time.mktime(t.timetuple()))
                    print ('expiry ', int(value), unit)
                    
                    
                print ('timestamp', timestamp)
                                
                token_info = self.utils.get_token_info(tmpPubkey) # need to find another way to get token Symbol
                if token_info: 
                    curr_price_of_token = token_info['price_usd']
                        
                        
                    if(triggerPercent):
                        triggerAt = float(curr_price_of_token) * (1 + float(triggerPercent) / 100) # getting trigger price from percent
                        
                    print('curr_price_of_token-----------------',f"{float(curr_price_of_token):.8f}")
                    print('triggerAt-----------------',f"{float(triggerAt):.8f}")
                    no_of_tokens = float(triggerAt) / float(curr_price_of_token) # getting number of tokens can be bought from with given price (here:- triggerAt is price in usd)
                    out_amount = int(no_of_tokens * (10 ** output_token_decimal)) 
                    
                    print('no_of_tokens-----------------',no_of_tokens)
                    print('out_amount-----------------',out_amount)
                    print ('input_mint, output_mint, in_amount, out_amount, sender',input_mint, output_mint, in_amount, out_amount, timestamp)

                    jup_txn_id = await tmpJupiterHel.create_order(input_mint, output_mint, in_amount, out_amount, sender, timestamp) # need to send slippage too
        
                    if not jup_txn_id:
                        print('txn failed>>>>>>')
                        await self.edit_message_text(text=f"There is some technical issue while creating order", chat_id = chat_id, message_id = msg.message_id, context = context)
                    else:
                        await self.edit_message_text(text=f"_🟢 Order Placed\\!_ [View on Solscan](https://solscan.io/tx/{jup_txn_id})", chat_id = chat_id, message_id = msg.message_id, context = context)
            
            else:
                await self.send_message(chat_id, f"You don\'t have any wallet to create order", context)
        except Exception as err:
            print("Error while Buying Limit Order-----", err)
            await self.send_message(chat_id, f"Buying Limit Order Failed\\.\\.\\.",  context, None, tmpCallBackType, tmpPubkey)

    
    async def buyToken(self, chat_id, context, tmpPubkey, tmpCallBackType, inputAmount):
        amount = int(inputAmount * self.one_sol_in_lamports)
        retrieved_user = await self.userModule.get_user_by_userId(int(chat_id))
        if(retrieved_user):
            sender = Keypair.from_base58_string(retrieved_user.keypair)
            if(tmpCallBackType == "transfer_token"):
                receiver =   Pubkey.from_string(tmpPubkey)
                txn = self.helper.transactionFun(sender, receiver, amount)
                msg = await self.send_message(chat_id, f"__Transferring SOL__", context, None, tmpCallBackType, tmpPubkey)
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
                    await self.send_message(chat_id, f"🔴 Insufficient Balance", context, None, tmpCallBackType, tmpPubkey)
            # elif(tmpCallBackType == "buy_token"):
            else:
                msg = await self.send_message(chat_id, f"__Processing swap__", context, None, tmpCallBackType, tmpPubkey)

                # tmpJupiterHel = self.jupiterHelper.initializeJup(sender)
                self.solanaSwapModule.initializeTracker(sender)
                slippage = 100  # 1% slippage in basis points
                jup_txn_id = await self.solanaSwapModule.execute_swap(tmpPubkey, amount, slippage, sender, constant.input_mint)
                # jup_txn_id = await self.solanaSwapModule.execute_swap(tmpPubkey, inputAmount, slippage, sender, constant.input_mint)
                # jup_txn_id = await self.jupiterHelper.execute_swap(tmpPubkey, amount, slippage, sender)
                if not jup_txn_id:
                    print('txn failed>>>>>>')
                    await self.edit_message_text(text=f"There is some technical issue while buying the token", chat_id = chat_id, message_id = msg.message_id, context = context)
                else:
                    await self.edit_message_text(text=f"_🟢 Buy Success\\!_ [View on Solscan](https://solscan.io/tx/{jup_txn_id})", chat_id = chat_id, message_id = msg.message_id, context = context)
                

        else:
            await self.send_message(chat_id, f"You don\'t have any wallet to send SOL", context, None, tmpCallBackType, tmpPubkey)

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
                token_info = self.utils.get_token_info(mint) # need to find another way to get token Symbol
                if token_info: 
                    curr_price_of_token = token_info['price_usd']
                    sol_info = self.utils.get_token_info(self.sol_address)                 
                    sol_curr_price = sol_info['price_usd']                   
                    
                    price_of_owned_token = float(curr_price_of_token) * float(ui_amount)
                    rounded_price_of_owned_token = round(price_of_owned_token, 6)
                
                    qty_in_sol = rounded_price_of_owned_token / float(sol_curr_price)
                    
                    formatted_message.append(f"<b><a href='https://t.me/{constant.bot_name}?start=sellToken-{mint}'>{str(token_info['symbol']).upper()}</a> ➖</b> {qty_in_sol:.6f} SOL - (${rounded_price_of_owned_token:.2f})")
    
                            
        # print('total_owned_sol',total_owned_sol,toatl_owned_sol_price)
        res = self.utils.getBalance(retrieved_user.publicKey)
        formatted_message.insert(1, f"Balance: <b>{res.get('sol_bal')} SOL (${res.get('usd_bal')})</b>\n")
        message = "\n".join(formatted_message)

        await self.edit_message_text(text=message, chat_id = chat_id, message_id = msg.message_id, context = context, parseMode=ParseMode.HTML)


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
                token_info = self.utils.get_token_info(mint)
                if token_info: 
                    curr_price_of_token = token_info['price_usd']             
                    sol_info = self.utils.get_token_info(self.sol_address)                 
                    sol_curr_price = sol_info['price_usd']   
                    
                    price_of_owned_token = float(curr_price_of_token) * float(ui_amount)
                    rounded_price_of_owned_token = round(price_of_owned_token, 6)
                    
                    qty_in_sol = rounded_price_of_owned_token / float(sol_curr_price)
                    total_owned_sol = total_owned_sol + qty_in_sol
                    toatl_owned_sol_price = toatl_owned_sol_price + rounded_price_of_owned_token
                    
                    formatted_message.append(f"<b><a href='https://t.me/{constant.bot_name}?start=sellToken-{mint}'>{str(token_info['symbol']).upper()} - 📈</a></b> {qty_in_sol:.6f} SOL - (${rounded_price_of_owned_token:.2f})")
                    formatted_message.append(f"<code>{mint}</code>")
                    formatted_message.append(f"● Price: <b>${token_info['price_usd']}</b>")
                    formatted_message.append(f"● Amount (owned): <b>{ui_amount:.6f}</b> {str(token_info['symbol']).upper()}\n")
                                
        res = self.utils.getBalance(retrieved_user.publicKey)
        formatted_message.insert(1, f"Balance: <b>{res.get('sol_bal')} SOL (${res.get('usd_bal')})</b>")
        formatted_message.insert(2, f"Positions: <b>{total_owned_sol:.6f} SOL (${toatl_owned_sol_price:.2f})</b>\n")
        message = "\n".join(formatted_message)
        
        await self.edit_message_text(text=message, chat_id = chat_id, message_id = msg.message_id, context = context, parseMode=ParseMode.HTML)



if __name__ == '__main__':
    print('main 2 started>>>>>>>>>>>>>>>>>>>>>')
    bot = Bot()
    print('main 2 started2>>>>>>>>>>>>>>>>>>>>>')
    bot.main()
#     main()


from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import re
import requests
import math  
import datetime
import base64
import locale
from userModel import UserModule , UserModel
from telegram.constants import ParseMode
from solders.keypair import Keypair
import constant
from solders.pubkey import Pubkey
from solanaHelper import SolanaHelper

chain_id = "solana"

class Utils():
    def __init__(
        self,
        send_message,
        delete_message,
        edit_message_text,
        userModule,
        jupiterHelper
    ):
        """Init API client."""
        super().__init__()
        self.send_message = send_message
        self.delete_message = delete_message
        self.userModule = userModule
        self.jupiterHelper = jupiterHelper
        self.edit_message_text = edit_message_text
        self.helper = SolanaHelper()
        self.one_sol_in_lamports = 1000000000
        self.sol_address = "So11111111111111111111111111111111111111112"
        self.main_keyboard = [
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


        self.buy_swap_keyboard = [
            [
                {"text": "Swap ✅", "callback_data": "toggle_buy_swap_mode"},
                {"text": "Limit", "callback_data": "toggle_buy_limit_mode"}
            ],
            [
                {"text": "0.1 SOL", "callback_data": "buy_0.1_sol"},
                {"text": "0.5 SOL", "callback_data": "buy_0.5_sol"},
            ],
            [
                {"text": "1 SOL", "callback_data": "buy_1_sol"},
                {"text": "X SOL ✏️", "callback_data": "buy_x_sol"}
            ],
        ]



    async def buy_swap_menu(self, chat_id, token_info, token_address, context: ContextTypes.DEFAULT_TYPE, message_id=None, callBackType = "", publicKey = "", is_limit_order_menu = None, chat_data = None):
        # print('buy_swap_menu>>>>>>>>>>>>>')   

        token_info_message = (
            f"Buy *{token_info['symbol']}* \\- {token_info['name']} [📈](https://dexscreener.com/{chain_id}/{token_address})\n"
            f"`{token_address}` _\\(Tap to copy\\)_ \n\n"
            f"Price: *${self.escape_dots(token_info['price_usd'])}*\n"
            f"Liquidity: *{self.escape_dots(locale.currency(token_info['liquidity_usd'], grouping=True))}*\n"
            f"FDV: *{self.escape_dots(locale.currency(token_info['fdv'], grouping=True))}*\n"
        )
        
        reply_keyboard = InlineKeyboardMarkup(self.buy_swap_keyboard)

        if (is_limit_order_menu and chat_data):
            menu_message_id = context.chat_data["lastBuyMenuMsgId"]
            if menu_message_id:
                await self.delete_message(chat_id, menu_message_id, context)
           
            reply_keyboard = InlineKeyboardMarkup(self.getBuyLimitKeyboard(chat_data))

        await self.send_message(chat_id, token_info_message, context, reply_keyboard, callbackType = callBackType,userFilledPubkey = publicKey, message_id = message_id)





    def getUpdatedBuyKeyboard(self, keyboard, chat_data, toggleSwap):
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
                    if not(button.callback_data == 'trigger_at' or button.callback_data == 'create_order' or button.callback_data == 'expire_btn'):
                        new_row.append(button)
            new_buttons.append(new_row)
        
        if not(toggleSwap):
            tmp_trigger_at = ""
            if "triggerAt" in chat_data:
                tmp_trigger_at = chat_data["triggerAt"]
            trigger_btn = [InlineKeyboardButton(
                text='Trigger at:' + tmp_trigger_at,
                callback_data='trigger_at'
            )]
            expire_btn = [InlineKeyboardButton(
                text='Expiry:',
                callback_data='expire_at'
            )]
            execute_btn = [InlineKeyboardButton(
                text='CREATE ORDER',
                callback_data='create_order'
            )]
            new_buttons.append(trigger_btn)
            new_buttons.append(expire_btn)
            new_buttons.append(execute_btn)

        updated_markup = InlineKeyboardMarkup(new_buttons) 
        return updated_markup


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

    def getBuyLimitKeyboard(self, chat_data):
        tmp_trigger_at = ""
        tmp_limit_amount = ""
        tmp_expiry_date = ""
        if "triggerAt" in chat_data:
            tmp_trigger_at = chat_data["triggerAt"]

        if "limitAmount" in chat_data:
            tmp_limit_amount = chat_data["limitAmount"]

        if "expireAt" in chat_data:
            tmp_expiry_date = ": " + chat_data["expireAt"]
        buy_limit_keyboard = [
            [
                {"text": "Swap", "callback_data": "toggle_buy_swap_mode"},
                {"text": "Limit ✅", "callback_data": "toggle_buy_limit_mode"}
            ],
            [
                {"text": '✅ 0.1 SOL' if tmp_limit_amount == 0.1 else "0.1 SOL", "callback_data": "buy_limit_0.1_sol"},
                {"text": '✅ 0.5 SOL' if tmp_limit_amount == 0.5 else "0.5 SOL", "callback_data": "buy_limit_0.5_sol"},
            ],
            [
                {"text": '✅ 1 SOL' if tmp_limit_amount == 1 else "1 SOL", "callback_data": "buy_limit_1_sol"},
                {"text": '✅ ' + str(tmp_limit_amount) + ' ✏️' if (not(tmp_limit_amount == 0.1 or tmp_limit_amount == 0.5 or tmp_limit_amount == 1) and tmp_limit_amount) else 'X SOL ✏️', "callback_data": "buy_limit_x_sol"}
            ],
            [
                {"text": 'Trigger at: ' + str(tmp_trigger_at), "callback_data": "buy_trigger_at"},
            ],
            [
                {"text": "Expiry " + tmp_expiry_date, "callback_data": "buy_expire_at"},
            ],
            [
                {"text": "CREATE ORDER", "callback_data": "buy_create_order"},
            ]
        ]
        # print('buy_limit_keyboard>>>>>>>>>>>>>>>>>>', buy_limit_keyboard)
        return buy_limit_keyboard


    async def listOrders(self, chat_id, context):    

        msg = await self.send_message(chat_id, f"_Fetching your orders\\.\\.\\._", context)
        
        retrieved_user = await self.userModule.get_user_by_userId(int(chat_id))
        if(retrieved_user):
            sender = Keypair.from_base58_string(retrieved_user.keypair)
            self.jupiterHelper.initializeJup(sender)
            orderList = await self.jupiterHelper.query_orders_history(retrieved_user.publicKey)
            # tokens = orderList.value
            
            formatted_message = []
            
            message = "You have no active limit orders. Create a limit order from the Buy/Sell menu."
            for order in orderList:   
                account = order.get('account')
                token_public_key = order.get('publicKey')
                # print("account>>>>>>>>>>>>>>>>>>>", account)
                # token_amount = info.get('tokenAmount', {}).get('amount')
                token_mint = account["inputMint"]
                orderType = "Sell "
                sol_amount = float(int(account["oriOutAmount"]) / self.one_sol_in_lamports)
                token_amount = account["oriInAmount"]
                expiry_date = account["expiredAt"]
                if not expiry_date:
                    expiry_date = "Not setted"
                else:
                    expiry_date = datetime.datetime.fromtimestamp(int(expiry_date))
                    
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
                    formatted_message.append(f"● Trigger price: <b>{str(token_info['symbol']).upper()}  {  token_amount}</b>")
                    formatted_message.append(f"● Expires: <b>{expiry_date}</b>\n\n")
                # print('token_mint>>>>>>>>>>>>', token_mint)

            if formatted_message:
                message = "\n".join(formatted_message)
            
            await self.edit_message_text(text=message, chat_id = chat_id, message_id = msg.message_id, context = context, parseMode=ParseMode.HTML)

        else:
            await self.send_message(chat_id, f"You don\'t have any wallet to view Order List", context, message_id = msg.message_id)





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



    async def sell_swap_menu(self, chat_id, token_info, token_address, context: ContextTypes.DEFAULT_TYPE, message_id=None, callBackType = ""):
        sell_button_text = "SELL ✅"
        limit_button_text = "Limit"

        sell_25_text = "Sell 25%"
        sell_50_text = "Sell 50%"
        sell_100_text = "Sell 100%"
        sell_x_text = "Sell X % ✏️"
        
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
                {"text": sell_button_text, "callback_data": "toggle_sell_mode"},
                {"text": limit_button_text, "callback_data": "toggle_buy_limit_mode"}
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



    def getBalance(self, publicKey):
        response = self.helper.getBalance(Pubkey.from_string(publicKey))
        sol_bal = math.ceil((response.value / self.one_sol_in_lamports) * 100) / 100
            
        sol_price_response = requests.get('https://api.raydium.io/v2/main/price')
        sol_price_response.raise_for_status()  # Check for HTTP errors
        data = sol_price_response.json()
        sol_price = data[self.sol_address]
        usd_bal =  math.ceil((sol_bal * sol_price) * 100) / 100
        return {"sol_bal":sol_bal, "usd_bal":usd_bal}


    def encode_key(self, key: bytes) -> str:
        return base64.b64encode(key).decode('utf-8')

    def decode_key(self, encoded_key: str) -> bytes:
        return base64.b64decode(encoded_key)
    
    def escape_dots(self, value):
        value_str = str(value)
        escaped_str = re.sub(r'\.', r'\\.', value_str)
        return escaped_str
    
    
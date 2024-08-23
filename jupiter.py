import base58
import base64
import json
import requests
import os
import asyncio

from solders import message
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solders.signature import Signature

from solana.rpc.types import TxOpts
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Processed

from jupiter_python_sdk.jupiter import Jupiter, Jupiter_DCA
import httpx
import constant



class JupiterHelper():
    def __init__(
        self,
        keypair = None
    ):
        """Init API client."""
        super().__init__()
        # self.client =  Client(clientURL)
        # self._provider = http.HTTPProvider(endpoint, timeout=timeout, extra_headers=extra_headers)
        self.solana_rpc_url = constant.clientURL

        self.async_client = AsyncClient(self.solana_rpc_url)

        if(keypair):
            Jupiter(
                async_client=self.async_client,
                keypair=keypair,
                quote_api_url="https://quote-api.jup.ag/v6/quote?",
                swap_api_url="https://quote-api.jup.ag/v6/swap",
                open_order_api_url="https://jup.ag/api/limit/v1/createOrder",
                cancel_orders_api_url="https://jup.ag/api/limit/v1/cancelOrders",
                query_open_orders_api_url="https://jup.ag/api/limit/v1/openOrders?wallet=",
                query_order_history_api_url="https://jup.ag/api/limit/v1/orderHistory",
                query_trade_history_api_url="https://jup.ag/api/limit/v1/tradeHistory"
            )
        

    def initializeJup(self, keypair):
        self.jupiter = Jupiter(
            async_client=self.async_client,
            keypair=keypair,
            quote_api_url="https://quote-api.jup.ag/v6/quote?",
            swap_api_url="https://quote-api.jup.ag/v6/swap",
            open_order_api_url="https://jup.ag/api/limit/v1/createOrder",
            cancel_orders_api_url="https://jup.ag/api/limit/v1/cancelOrders",
            query_open_orders_api_url="https://jup.ag/api/limit/v1/openOrders?wallet=",
            query_order_history_api_url="https://jup.ag/api/limit/v1/orderHistory",
            query_trade_history_api_url="https://jup.ag/api/limit/v1/tradeHistory"
        )
        return self.jupiter
    
    async def execute_swap(self, output_mint: str, amount: int, slippage_bps: int, sender: Keypair):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                transaction_data = await self.jupiter.swap(
                    input_mint=constant.input_mint,
                    output_mint=output_mint,
                    amount=amount,
                    slippage_bps=slippage_bps,
                )
                break
            except httpx.ReadTimeout as e:
                if attempt < max_retries - 1:
                    print(f"ReadTimeout occurred, retrying {attempt + 1}/{max_retries}...")
                    await asyncio.sleep(1)  # Wait before retrying
                else:
                    print("Max retries reached. Exiting.")
                    return ""
            except httpx.UnsupportedProtocol as e:
                print(f"UnsupportedProtocol error: {e}")
                return ""
            except Exception as e:
                print(f"Unexpected error during swap: {e}")
                return ""

        try:
            raw_transaction = VersionedTransaction.from_bytes(base64.b64decode(transaction_data))
            signature = sender.sign_message(message.to_bytes_versioned(raw_transaction.message))
            signed_txn = VersionedTransaction.populate(raw_transaction.message, [signature])
            opts = TxOpts(skip_preflight=False, preflight_commitment=Processed)
            result = await self.async_client.send_raw_transaction(txn=bytes(signed_txn), opts=opts)
            transaction_id = json.loads(result.to_json())['result']
            print(f"Transaction sent: https://solscan.io/tx/{transaction_id}")
            return transaction_id
        except Exception as e:
            print(f"Error sending transaction: {e}")
            return ""

    async def check_transaction_status(self, transaction_id: str):
        max_checks = 5
        for attempt in range(max_checks):
            try:
                response = await self.async_client.get_signature_statuses([Signature.from_string(transaction_id)])
                status = response.value[0]
                if status is not None:
                    print(f"Transaction status: {status}")
                    break
                else:
                    print(f"Transaction status not found, retrying {attempt + 1}/{max_checks}...")
                    await asyncio.sleep(5)  # Wait before retrying
            except Exception as e:
                print(f"Error checking transaction status: {e}")

    async def create_order(self, input_mint, output_mint, in_amount, out_amount, sender):        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                transaction_data = await self.jupiter.open_order(input_mint, output_mint, in_amount, out_amount)
                print("transaction_data>>>>>>>>>>>>>>", transaction_data)
                break
            except httpx.ReadTimeout as e:
                if attempt < max_retries - 1:
                    print(f"ReadTimeout occurred, retrying {attempt + 1}/{max_retries}...")
                    await asyncio.sleep(1)  # Wait before retrying
                else:
                    print("Max retries reached. Exiting.")
                    return ""
            except httpx.UnsupportedProtocol as e:
                print(f"UnsupportedProtocol error: {e}")
                return ""
            except Exception as e:
                print(f"Unexpected error during swap: {e}")
                return ""

        try:
            raw_transaction = VersionedTransaction.from_bytes(base64.b64decode(transaction_data['transaction_data']))
            signature = sender.sign_message(message.to_bytes_versioned(raw_transaction.message))
            signed_txn = VersionedTransaction.populate(raw_transaction.message, [signature, transaction_data['signature2']])
            opts = TxOpts(skip_preflight=False, preflight_commitment=Processed)
            result = await self.async_client.send_raw_transaction(txn=bytes(signed_txn), opts=opts)
            transaction_id = json.loads(result.to_json())['result']
            return transaction_id
        except Exception as e:
            print(f"Error sending transaction: {e}")
            return ""

    async def query_orders_history(self, wallet_address: str):
        try:
            # trade_history = await self.jupiter.query_trades_history(wallet_address)
            # order_history = await self.jupiter.query_orders_history(wallet_address)
            open_history = await self.jupiter.query_open_orders(wallet_address)
            # print('history>>>>>>>>>>>>>>>>>>>', trade_history)
            # print('order_history>>>>>>>>>>>>>>>>>>>', order_history)
            # print('open_history>>>>>>>>>>>>>>>>>>>', open_history)
            return open_history
        except Exception as e:
            print(f"Error sending transaction: {e}")
            return ""

    async def cancel_orders(self, orderList, sender):        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                transaction_data = await self.jupiter.cancel_orders(orderList)
                print("transaction_data>>>>>>>>>>>>>>", transaction_data)
                break
            except httpx.ReadTimeout as e:
                if attempt < max_retries - 1:
                    print(f"ReadTimeout occurred, retrying {attempt + 1}/{max_retries}...")
                    await asyncio.sleep(1)  # Wait before retrying
                else:
                    print("Max retries reached. Exiting.")
                    return ""
            except httpx.UnsupportedProtocol as e:
                print(f"UnsupportedProtocol error: {e}")
                return ""
            except Exception as e:
                print(f"Unexpected error during swap: {e}")
                return ""

        try:
            raw_transaction = VersionedTransaction.from_bytes(base64.b64decode(transaction_data))
            signature = sender.sign_message(message.to_bytes_versioned(raw_transaction.message))
            signed_txn = VersionedTransaction.populate(raw_transaction.message, [signature])
            opts = TxOpts(skip_preflight=False, preflight_commitment=Processed)
            result = await self.async_client.send_raw_transaction(txn=bytes(signed_txn), opts=opts)
            transaction_id = json.loads(result.to_json())['result']
            print(f"Transaction sent: https://solscan.io/tx/{transaction_id}")
            return transaction_id
        except Exception as e:
            print(f"Error sending transaction: {e}")
            return ""







    def get_token_decimal_info(self, token_address):
            try:
                api_url = f"https://tokens.jup.ag/token/{token_address}"
                response = requests.get(api_url)
                response.raise_for_status()  # Check for HTTP errors
                data = response.json()
                if(data['decimals']):
                    return data['decimals']
                else:
                    raise Exception('I know Python!')
            except requests.exceptions.HTTPError as http_err:
                print(f"HTTP error occurred: {http_err}")
                raise Exception('I know Python2!')
            except Exception as err:
                print(f"Other error occurred: {err}")
                raise Exception('I know Python3!')

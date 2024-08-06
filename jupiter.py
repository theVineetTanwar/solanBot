import base58
import base64
import json
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



# async def main():
#     # Load keypair from walletTest.json
#     # with open("walletTest.json", "r") as file:
#     #     keypair_data = json.load(file)[0]

#     # public_key = keypair_data["public_key"]
#     # private_key_base58 = keypair_data["private_key"]
#     keypair = Keypair.from_base58_string('2Tojm2pUxXe4KPfnbzNwKWXb5jjT7J91FHfZ9qKwyx8MaSEiwRztSFuf9oV69BsGj7j5g9H6dPzhfe8u8Tspzdwh')
#     private_key = keypair.secret()

#     # private_key = Keypair.from_bytes(base58.b58decode(private_key_base58))
    
#     # Solana RPC endpoint URL
#     solana_rpc_url = "https://api.mainnet-beta.solana.com"

#     async_client = AsyncClient(solana_rpc_url)
#     jupiter = Jupiter(
#         async_client=async_client,
#         keypair=keypair,
#         quote_api_url="https://quote-api.jup.ag/v6/quote?",
#         swap_api_url="https://quote-api.jup.ag/v6/swap",
#         open_order_api_url="https://jup.ag/api/limit/v1/createOrder",
#         cancel_orders_api_url="https://jup.ag/api/limit/v1/cancelOrders",
#         query_open_orders_api_url="https://jup.ag/api/limit/v1/openOrders?wallet=",
#         query_order_history_api_url="https://jup.ag/api/limit/v1/orderHistory",
#         query_trade_history_api_url="https://jup.ag/api/limit/v1/tradeHistory"
#     )

#     async def execute_swap(input_mint: str, output_mint: str, amount: int, slippage_bps: int):
#         max_retries = 3
#         for attempt in range(max_retries):
#             try:
#                 transaction_data = await jupiter.swap(
#                     input_mint=input_mint,
#                     output_mint=output_mint,
#                     amount=amount,
#                     slippage_bps=slippage_bps,
#                 )
#                 break
#             except httpx.ReadTimeout as e:
#                 if attempt < max_retries - 1:
#                     print(f"ReadTimeout occurred, retrying {attempt + 1}/{max_retries}...")
#                     await asyncio.sleep(1)  # Wait before retrying
#                 else:
#                     print("Max retries reached. Exiting.")
#                     return
#             except httpx.UnsupportedProtocol as e:
#                 print(f"UnsupportedProtocol error: {e}")
#                 return
#             except Exception as e:
#                 print(f"Unexpected error during swap: {e}")
#                 return

#         try:
#             raw_transaction = VersionedTransaction.from_bytes(base64.b64decode(transaction_data))
#             signature = keypair.sign_message(message.to_bytes_versioned(raw_transaction.message))
#             signed_txn = VersionedTransaction.populate(raw_transaction.message, [signature])
#             opts = TxOpts(skip_preflight=False, preflight_commitment=Processed)
#             result = await async_client.send_raw_transaction(txn=bytes(signed_txn), opts=opts)
#             transaction_id = json.loads(result.to_json())['result']
#             print(f"Transaction sent: https://solscan.io/tx/{transaction_id}")
#             await check_transaction_status(transaction_id)
#         except Exception as e:
#             print(f"Error sending transaction: {e}")

#     async def check_transaction_status(transaction_id: str):
#         max_checks = 5
#         for attempt in range(max_checks):
#             try:
#                 response = await async_client.get_signature_statuses([Signature.from_string(transaction_id)])
#                 status = response.value[0]
#                 if status is not None:
#                     print(f"Transaction status: {status}")
#                     break
#                 else:
#                     print(f"Transaction status not found, retrying {attempt + 1}/{max_checks}...")
#                     await asyncio.sleep(5)  # Wait before retrying
#             except Exception as e:
#                 print(f"Error checking transaction status: {e}")

#     # Define your token, slippage, and amount of SOL to swap
#     input_token = "So11111111111111111111111111111111111111112"  # Example input token (SOL)
#     output_token = "9EYScpiysGnEimnQPzazr7Jn9GVfxFYzgTEj85hV9L6U"  # Example output token
#     swap_amount = 1_0  # 0.01 SOL in lamports
#     slippage = 100  # 1% slippage in basis points

#     # Execute the swap
#     await execute_swap(input_token, output_token, swap_amount, slippage)


# Run the main function
# asyncio.run(main())


class JupiterHelper():
    def __init__(
        self
    ):
        """Init API client."""
        super().__init__()
        # self.client =  Client(clientURL)
        # self._provider = http.HTTPProvider(endpoint, timeout=timeout, extra_headers=extra_headers)
        self.solana_rpc_url = constant.clientURL

        self.async_client = AsyncClient(self.solana_rpc_url)
        

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
                    output_mint=str(output_mint),
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


# helper = JupiterHelper()
# sender = Keypair.from_base58_string("")

# helper.initializeJup(sender)
# input_token = "So11111111111111111111111111111111111111112"  # Example input token (SOL)
# output_token = ""  # Example output token
# swap_amount = 1_0  # 0.01 SOL in lamports
# slippage = 100  # 1% slippage in basis points

# # helper.execute_swap(output_token, swap_amount, slippage, sender)
# asyncio.run(helper.execute_swap(output_token, swap_amount, slippage, sender))
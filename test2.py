import asyncio
from solders import message
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solders.signature import Signature

from solana.rpc.async_api import AsyncClient
from solana.transaction import Transaction
from solana.rpc.commitment import Confirmed, Processed
from solana.rpc.types import TxOpts


from pyserum.market import Market
from pyserum.enums import OrderType, Side
from pyserum.open_orders_account import OpenOrdersAccount
from solana.rpc.types import TxOpts

async def main():
    # Initialize connection to Solana
    client = AsyncClient("https://api.mainnet-beta.solana.com")

    # Load market address (example: Serum USDC/USDT market)
    market_address = Pubkey("2orqxJdCqDLdya8AwNHti4LUt16ysojKW2UMKuYZpump")

    # Load your wallet (keypair)
    wallet = Keypair.from_base58_string("5A9LpqJaiUQZqQ6jdWeL234ywZrsbmi6ye9cCyvQqcHePRUMbGWa9YLiQjzvmRqa9t5jaKYyNphFg1CetUB4qVFA")

    # Initialize market
    market = await Market.load(client, market_address, "program-id")

    # Create a transaction for the limit order
    transaction = Transaction()

    # Define the order parameters
    side = Side.BUY    # or Side.SELL
    limit_price = 1.0  # Define your price
    max_qty = 1000.0   # Define your quantity

    # Place limit order
    place_order_tx = market.place_order(
        payer=wallet.pubkey,
        owner=wallet,
        side=side,
        order_type=OrderType.LIMIT,
        limit_price=limit_price,
        max_qty=max_qty,
        client_id=1,  # optional, set your own client id
    )

    transaction.add(place_order_tx)

    # Sign and send the transaction
    signature = await client.send_transaction(transaction, wallet, opts=TxOpts(skip_preflight=True, preflight_commitment=Confirmed))
    print(f"Transaction Signature: {signature['result']}")

    # Confirm transaction
    await client.confirm_transaction(signature['result'])

    # Close the client
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())

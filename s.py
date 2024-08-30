import asyncio
import requests
import json
from solana.rpc.async_api import AsyncClient
from solana.transaction import Transaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TxOpts
from jupiter_python_sdk.jupiter import Jupiter
import base58



def swap(quote_response, user_public_key):
    url = 'https://quote-api.jup.ag/v6/swap'
    headers = {
        'Content-Type': 'application/json'
    }
    
    body = {
        "quoteResponse": quote_response,
        "userPublicKey": "7NWwYNKJpE8qo4rbWuCnExHXdNMwqVhp2s2YB5973tfM",
        "wrapAndUnwrapSol": True,
    }
        # 'feeAccount': 'fee_account_public_key',  # Uncomment and set this if you want to charge a fee
    print("bpdy",body)
    response = requests.post(url, headers=headers, json = json.dumps(body))
    response.raise_for_status()  # Check for HTTP errors
    data = response.json()    
    print('++++++++++++++++',data)
    
    
    if response.status_code == 200:
        swap_transaction = response.json().get('swapTransaction')
        return swap_transaction
    else:
        print(f"Failed to fetch swap transaction. Status code: {response.status_code}")
        print(response.text)
        return None


def get_quote(input_mint, output_mint, amount, exclude_dexes, slippage_bps):
    base_url = 'https://quote-api.jup.ag/v6/quote'
    
    params = {
        'inputMint': input_mint,
        'outputMint': output_mint,
        'amount': amount,
        'slippageBps': slippage_bps
    }
        # 'excludeDexes': ','.join(exclude_dexes),
        # 'excludeDexes': '',
    response = requests.get(base_url, params=params)
    
    if response.status_code == 200:
        response.raise_for_status()  # Check for HTTP errors
        data = response.json()
        # print("datatata",data)
        return data
    else:
        print(f"Failed to fetch quote. Status code: {response.status_code}")
        print(response.text)
        return None



async def swap_tokens(
    client: AsyncClient,
    jupiter: Jupiter,
    input_mint: str,
    output_mint: str,
    amount: int,
    slippage_bps: int,
    wallet_keypair: Keypair
):
    # Fetch swap route from Jupiter
    # routes = await jupiter.quote(
    #     input_mint=input_mint,
    #     output_mint=output_mint,
    #     amount=amount,
    #     slippage_bps=slippage_bps
    # )
    
    # routePlan = routes.get('routePlan','')
    # print("routePlan",routePlan)
    # # Select the best route (You can add your logic to select the route)
    # route = routePlan[0]
    # print("route",route)

    # # Perform the swap
    # # swap_txn = await jupiter.swap(route, wallet_keypair)
    # swap_txn = await jupiter.swap(input_mint, output_mint, amount)
    # print('-swap_txn',swap_txn)

    # # Sign and send the transaction
    # # transaction = Transaction.deserialize(swap_txn['swapTransaction'])
    # transaction = Transaction.deserialize(swap_txn)
    # print('transaction',transaction)
    # transaction.sign(wallet_keypair)
    # response = await client.send_transaction(transaction, wallet_keypair, opts=TxOpts(skip_preflight=False, preflight_commitment=Confirmed))
    
    exclude_dexes = {"Openbook", ""}  # Example set of DEXes to exclude

    quote_data = get_quote(input_mint, output_mint, amount, exclude_dexes, slippage_bps)
    if quote_data:
        print("Quote Data:", quote_data)
    
    print('wallet_keypair.pubkey',wallet_keypair.pubkey())
    swap_transaction = swap(quote_data, wallet_keypair.pubkey())
    if swap_transaction:
        print("Swap Transaction:", swap_transaction)
    
    
    

# Main function to execute the swap
async def main():
    client = AsyncClient("https://api.mainnet-beta.solana.com")
    
    wallet_private_key = "your-wallet-private-key"  # Replace with your base58 private key
    # wallet_keypair = Keypair.from_secret_key(base58.b58decode(wallet_private_key))
    wallet_keypair = Keypair.from_base58_string("2Tojm2pUxXe4KPfnbzNwKWXb5jjT7J91FHfZ9qKwyx8MaSEiwRztSFuf9oV69BsGj7j5g9H6dPzhfe8u8Tspzdwh")
    
    
    jupiter = Jupiter(client,wallet_keypair)

    input_mint = "So11111111111111111111111111111111111111112"  # Replace with the input token mint
    output_mint = "BVG3BJH4ghUPJT9mCi7JbziNwx3dqRTzgo9x5poGpump"  # Replace with the output token mint
    amount = 1_0000  # Amount in smallest units (e.g., lamports)
    slippage_bps = 100  # 0.5% slippage

    await swap_tokens(client, jupiter, input_mint, output_mint, amount, slippage_bps, wallet_keypair)

# Run the main function
asyncio.run(main())

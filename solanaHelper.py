import asyncio
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from solana.rpc.api import Client

client =  Client("https://api.devnet.solana.com")
solanaConnected = client.is_connected()
print("solanaConnected>>>>>>>", solanaConnected)  # True

# def main():
    # async with AsyncClient("https://api.devnet.solana.com") as client:
    # async with Client("https://api.devnet.solana.com") as client:
    # async with Client("http://localhost:8899") as client:
    # res = client.is_connected()
    # print("res>>>>>>>", res)  # True

    # pubkeyfromStr = Pubkey.from_string("H5FiG9MiGCWwMHRNc9q3nVHJS7navNdYMGgp67eQoc8K") 
    # balance = client.get_balance(pubkeyfromStr)
    # print("balance>>>>>>>>>>>>>>>>>>>", balance)
    
    # accountInfo = client.get_account_info(pubkeyfromStr)
    # print("accountInfo>>>>>>>>>>>>>>>>>>>", accountInfo)

    
    # singnatureForAdd = client.get_signatures_for_address(pubkeyfromStr)
    # print("singnatureForAdd>>>>>>>>>>>>>>>>>>>", singnatureForAdd)

    # getLatestBlockhash = client.get_latest_blockhash()
    # print("getLatestBlockhash>>>>>>>>>>>>>>>>>>>", getLatestBlockhash)
    


def getAccountInfo(pubkey):
    balance = client.get_balance(pubkey)
    return balance

# pubkeyfromStr1 = Pubkey.from_string("H5FiG9MiGCWwMHRNc9q3nVHJS7navNdYMGgp67eQoc8K") 
# info = getAccountInfo(pubkeyfromStr1)
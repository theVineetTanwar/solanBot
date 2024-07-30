import asyncio
from solders.pubkey import Pubkey
from solana.rpc.api import Client
from solders.hash import Hash
from solders.keypair import Keypair
from solders.system_program import TransferParams, transfer
from solana.transaction import Transaction



client =  Client("https://api.devnet.solana.com")
solanaConnected = client.is_connected()


def transactionFun(sender: Keypair, senderPubKey: Pubkey, receiver: Pubkey, amount):

    txn = Transaction().add(transfer(
        TransferParams(
            from_pubkey=senderPubKey, to_pubkey=receiver, lamports=amount
        )
    ))
    txnRes = client.send_transaction(txn, sender).value # doctest: +SKIP like as 3L6v5yiXRi6kgUPvNqCD7GvnEa3d1qX79REdW1KqoeX4C4q6RHGJ2WTJtARs8ty6N5cSVGzVVTAhaSNM9MSahsqw
    # return response as URL https://solscan.io/tx/txnRes?cluster=devnet
    return txnRes

def getLatestBlockHash():
    return client.get_latest_blockhash()

def getAccountInfo(pubkey):
    return client.get_balance(pubkey)

# transactionFun()
# pubkeyfromStr1 = Pubkey.from_string("string") 
# info = getAccountInfo(pubkeyfromStr1)
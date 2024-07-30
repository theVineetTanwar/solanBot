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



class SolanaHelper():
    def __init__(
        self,
    ):
        """Init API client."""
        super().__init__()
        self.client =  Client("https://api.devnet.solana.com")
        # self._provider = http.HTTPProvider(endpoint, timeout=timeout, extra_headers=extra_headers)

    
    def transactionFun(self, sender: Keypair, senderPubKey: Pubkey, receiver: Pubkey, amount):

        txn = Transaction().add(transfer(
            TransferParams(
                from_pubkey=senderPubKey, to_pubkey=receiver, lamports=amount
            )
        ))
        txnRes = self.client.send_transaction(txn, sender).value # doctest: +SKIP like as 3L6v5yiXRi6kgUPvNqCD7GvnEa3d1qX79REdW1KqoeX4C4q6RHGJ2WTJtARs8ty6N5cSVGzVVTAhaSNM9MSahsqw
        # return response as URL https://solscan.io/tx/txnRes?cluster=devnet
        return txnRes

    def getLatestBlockHash(self):
        return self.client.get_latest_blockhash()

    def getAccountInfo(self, pubkey):
        return self.client.get_balance(pubkey)



# pubkeyfromStr1 = Pubkey.from_string("str") 
# helper = SolanaHelper()
# info = helper.getAccountInfo(pubkeyfromStr1)

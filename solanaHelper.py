import asyncio
from solders.pubkey import Pubkey
from solders.hash import Hash
from solders.keypair import Keypair
from solders.system_program import TransferParams, transfer
from solders.signature import Signature
from solana.rpc.api import Client
from solana.transaction import Transaction
import constant
from solana.rpc import types
from spl.token.constants import TOKEN_PROGRAM_ID

from solana.rpc.types import MemcmpOpts
from typing import List, Union

class SolanaHelper():
    def __init__(
        self,
    ):
        """Init API client."""
        super().__init__()
        self.client =  Client(constant.clientURL)
        # self._provider = http.HTTPProvider(endpoint, timeout=timeout, extra_headers=extra_headers)
        # print('self.client>>>>>>>>>>>>>', self.client)

    
    def transactionFun(self, sender: Keypair, receiver: Pubkey, amount):
        print('sender',sender)
        print('receiver',receiver)
        print('amount',amount)
        try:
            txn = Transaction().add(transfer(
                TransferParams(
                    from_pubkey=sender.pubkey(), to_pubkey=receiver, lamports=int(amount)
                )
            ))
            txnRes = self.client.send_transaction(txn, sender).value # doctest: +SKIP like as 3L6v5yiXRi6kgUPvNqCD7GvnEa3d1qX79REdW1KqoeX4C4q6RHGJ2WTJtARs8ty6N5cSVGzVVTAhaSNM9MSahsqw
            # return response as URL https://solscan.io/tx/txnRes?cluster=devnet
            return txnRes
        except Exception as e:
            print(f'Error sending SOL: {e}')
        return None
    
    def check_transaction_status(self, transaction_id: str):
        print('transaction_id',transaction_id)
        try:
            response = self.client.get_signature_statuses([Signature.from_string(transaction_id)])
            print('check txn status',response)
            status = response.value[0]
            if status is not None:
                print(f"Transaction status: {status}")
                return status
            else:
                print(f"Transaction status not found")
                return None
        except Exception as e:
            print(f'Error getting txn status: {e}')
        return None
    
    
    def getAccountInfo(self, pubKey):
        # print('transaction_id',transaction_id)
        try:
            memcmp_opts = MemcmpOpts(offset=4, bytes="3Mc6vR")
            filters: List[Union[int, MemcmpOpts]] = [17, memcmp_opts]

            tmpOpts = types.TokenAccountOpts(program_id=TOKEN_PROGRAM_ID)
            # print('tmpOpts>>>>>>>>>>>>>>>>>>', tmpOpts, "filters>>>>>>>>>>", filters)
            response = self.client.get_token_accounts_by_owner_json_parsed(pubKey, tmpOpts)
            # print('check txn status>>>>>',response)
            return response
        except Exception as e:
            print(f'Error getting account info: {e}')
        return None

    def getLatestBlockHash(self):
        return self.client.get_latest_blockhash()

    def getBalance(self, pubkey):
        return self.client.get_balance(pubkey)



# pubkeyfromStr1 = Pubkey.from_string("str") 
# helper = SolanaHelper()
# info = helper.getAccountInfo(pubkeyfromStr1)
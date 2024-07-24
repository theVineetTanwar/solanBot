
from solders.pubkey import Pubkey
from solders.hash import Hash
from solders.keypair import Keypair
from solders.message import MessageV0
from solders.system_program import TransferParams, transfer
from solders.transaction import VersionedTransaction

def transfer_sol(senderPubKey, senderKeypairStr, recieverPubKey):
    sender = Pubkey.from_string(senderPubKey)  # let's pretend this account actually has SOL to send
    receiver = Pubkey.from_string(recieverPubKey)
    ix = transfer(
        TransferParams(
            from_pubkey=sender, to_pubkey=receiver, lamports=1_000_000
        )
    )

    blockhash = Hash.default()  # replace with a real blockhash using get_latest_blockhash
    senderKeypair = Keypair.from_base58_string(senderKeypairStr)

    msg = MessageV0.try_compile(
        payer=sender,
        instructions=[ix],
        address_lookup_table_accounts=[],
        recent_blockhash=blockhash,
    )
    tx = VersionedTransaction(msg, [senderKeypair])


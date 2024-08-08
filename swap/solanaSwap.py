from solders.keypair import Keypair
from swap.solanatracker import SolanaTracker
import asyncio
import time

class SolanaSwapModule():
    def __init__(
        self,
        url,
        input_mint
    ):
        """Init API client."""
        super().__init__()
        self.solana_rpc_url = url
        self.input_mint = input_mint


    def initializeTracker(self, keypair):
        self.solana_tracker = SolanaTracker(keypair, self.solana_rpc_url)
        return self.solana_tracker
    
    async def execute_swap(self, output_mint: str, amount, slippage_bps: int, sender: Keypair):

        start_time = time.time()

        
        self.solana_tracker = SolanaTracker(sender, self.solana_rpc_url)
        
        swap_response = await self.solana_tracker.get_swap_instructions(
            self.input_mint,
            output_mint,
            amount,
            slippage_bps,  # Slippage
            str(sender.pubkey()),  # Payer public key
            0.00005,  # Priority fee (Recommended while network is congested)
        )

        
        # Define custom options
        custom_options = {
            "send_options": {"skip_preflight": True, "max_retries": 5},
            "confirmation_retries": 50,
            "confirmation_retry_timeout": 1000,
            "last_valid_block_height_buffer": 200,
            "commitment": "processed",
            "resend_interval": 1500,
            "confirmation_check_interval": 100,
            "skip_confirmation_check": False,
        }
        
        try:
            send_time = time.time()
            # return "id>>>"
            txid = await self.solana_tracker.perform_swap(swap_response, options=custom_options)
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            print("Transaction URL:", f"https://solscan.io/tx/{txid}")
            # print(f"Swap completed in {elapsed_time:.2f} seconds")
            # print(f"Transaction finished in {end_time - send_time:.2f} seconds")
            return txid
        except Exception as e:
            end_time = time.time()
            elapsed_time = end_time - start_time
            print("Swap failed:", str(e))
            return None
            # Add retries or additional error handling as needed


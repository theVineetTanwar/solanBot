import os
from dotenv import load_dotenv
load_dotenv()

clientURL = "https://api.mainnet-beta.solana.com"
# clientURL = "https://api.devnet.solana.com"

solanaTrackerURL = "https://rpc.solanatracker.io/public?advancedTx=true"
input_mint = "So11111111111111111111111111111111111111112"
bot_name = os.getenv("BOT_NAME")
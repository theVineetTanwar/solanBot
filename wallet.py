import os
from dotenv import load_dotenv
import http.client


load_dotenv()
SHYFT_API_KEY = os.getenv("SHYFT_API_KEY")

conn = http.client.HTTPSConnection("api.shyft.to")

headers = {
  'x-api-key': SHYFT_API_KEY
}
# conn.request("GET", "/sol/v1/wallet/balance?network=devnet&wallet=7HB7kG96HxTWUPRKUTGoVmX2WBSyxtgKs2uNPkjNfPtD", payload, headers)
# res = conn.getresponse()
# data = res.read()
# print(data.decode("utf-8"))

def transfer_sol(publicKey):
    payload = ''
    conn.request("GET", "/sol/v1/wallet/balance?network=devnet&wallet=" + publicKey, payload, headers)
    # conn.request("GET", "/sol/v1/wallet/balance?network=devnet&wallet=7HB7kG96HxTWUPRKUTGoVmX2WBSyxtgKs2uNPkjNfPtD", payload, headers)
    res = conn.getresponse()
    data = res.read()
    print(data.decode("utf-8"))

# transfer_sol("7HB7kG96HxTWUPRKUTGoVmX2WBSyxtgKs2uNPkjNfPtD")
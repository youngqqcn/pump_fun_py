from solana.rpc.api import Client
from solders.keypair import Keypair #type: ignore
from dotenv import load_dotenv
import os

load_dotenv()

PRIV_KEY = os.getenv("PRIV_KEY")
RPC = os.getenv("RPC")
client = Client(RPC)
payer_keypair = Keypair.from_base58_string(PRIV_KEY)

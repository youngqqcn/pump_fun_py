import json
from time import sleep
import random
from solders.keypair import Keypair  # type: ignore

# from config import RPC, client, payer_keypair
from traceback import print_exc
from solana.rpc.api import Client
from dotenv import load_dotenv
import os
from pump_fun import TradeBot
import multiprocessing

load_dotenv()


def run_start(worker_instance: TradeBot):
    worker_instance.start()


def main():
    PRIV_KEY = os.getenv("PRIV_KEY")
    PRIV_KEY2 = os.getenv("PRIV_KEY_2")
    RPC = os.getenv("RPC")

    mint_addr = "BBwV9WtsobWJStdY8o2ftxRkpyyNXG41SgSGErRXQWS4"
    tradebot1 = TradeBot(
        rpc_client=Client(RPC),
        keypair=Keypair.from_base58_string(PRIV_KEY),
        mint_addr=mint_addr,
    )

    tradebot2 = TradeBot(
        rpc_client=Client(RPC),
        keypair=Keypair.from_base58_string(PRIV_KEY2),
        mint_addr=mint_addr,
    )

    processes = [
        multiprocessing.Process(target=run_start, args=(tradebot1, )),
        multiprocessing.Process(target=run_start, args=(tradebot2, )),
    ]

    for p in processes:
        p.start()

    for p in processes:
        p.join()

    pass


if __name__ == "__main__":
    main()

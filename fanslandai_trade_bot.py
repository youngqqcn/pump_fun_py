import json
from time import sleep
import random
from solders.keypair import Keypair  # type: ignore

# from config import RPC, client, payer_keypair
from traceback import print_exc
from solana.rpc.api import Client
from dotenv import load_dotenv
import os
from bot.trade_bot import TradeBot
import multiprocessing

load_dotenv(".env")


def run_start(worker_instance: TradeBot):
    worker_instance.start()


def main():
    RPC = os.getenv("RPC")

    # temp = Keypair.from_seed(b"dddddsdfsdfdfuuusfsdfdsfsdffds99")
    # print("temp: {}".format( temp))
    # print("temp: {}".format( temp.pubkey()))

    # mint_addr = "BBwV9WtsobWJStdY8o2ftxRkpyyNXG41SgSGErRXQWS4" # HIHI
    mint_addr = os.getenv("MINT")  # HIHI
    assert len(mint_addr) == 44, "invalid token mint"
    tradebot1 = TradeBot(
        rpc_client=Client(RPC),
        keypair=Keypair.from_base58_string(os.getenv("PRIV_KEY_1")),
        mint_addr=mint_addr,
    )

    tradebot2 = TradeBot(
        rpc_client=Client(RPC),
        keypair=Keypair.from_base58_string(os.getenv("PRIV_KEY_2")),
        mint_addr=mint_addr,
    )

    tradebot3 = TradeBot(
        rpc_client=Client(RPC),
        keypair=Keypair.from_base58_string(os.getenv("PRIV_KEY_3")),
        mint_addr=mint_addr,
    )

    tradebot4 = TradeBot(
        rpc_client=Client(RPC),
        keypair=Keypair.from_base58_string(os.getenv("PRIV_KEY_4")),
        mint_addr=mint_addr,
    )

    processes = [
        multiprocessing.Process(target=run_start, args=(tradebot1,)),
        multiprocessing.Process(target=run_start, args=(tradebot2,)),
        multiprocessing.Process(target=run_start, args=(tradebot3,)),
        multiprocessing.Process(target=run_start, args=(tradebot4,)),
    ]

    for p in processes:
        p.start()

    for p in processes:
        p.join()

    pass


if __name__ == "__main__":
    main()

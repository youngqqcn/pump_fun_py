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

load_dotenv()


def main():
    PRIV_KEY = os.getenv("PRIV_KEY")
    RPC = os.getenv("RPC")
    client = Client(RPC)
    payer_keypair = Keypair.from_base58_string(PRIV_KEY)

    mint_addr = "BBwV9WtsobWJStdY8o2ftxRkpyyNXG41SgSGErRXQWS4"

    temp = Keypair.from_seed(b"sldfksdfjskdfjsdfiwer23242342432")
    print(temp)
    print(temp.pubkey())
    tradebot = TradeBot(rpc_client=client, keypair=payer_keypair)


    print("uri: ", client._provider.endpoint_uri)

    try:
        while True:

            sol_amount = random.randint(1 * 10**8, 3 * 10**8) / 10**9
            tradebot.buy(mint_str=mint_addr, sol_amount=sol_amount, slippage=10)
            # print("ret= {}".format(ret))

            sol_balance = client.get_balance(payer_keypair.pubkey()).value

            sell_flag = False
            if sol_balance / 10**9 < 10:
                # 如果余额不够，马上卖
                sell_flag = True

            if sell_flag or random.randint(0, 100) < 50:
                token_balance = tradebot.get_token_balance(mint_str=mint_addr)

                # 卖出的百分比
                sell_amount = token_balance * random.randint(3, 15) / 100

                tradebot.sell(
                    mint_str=mint_addr,
                    token_amount=sell_amount,
                    slippage=10,
                    close_token_account=False,
                )

            sleep(30)
        pass
    except Exception as e:
        print(e)
        print_exc(e)

    pass


if __name__ == "__main__":
    main()

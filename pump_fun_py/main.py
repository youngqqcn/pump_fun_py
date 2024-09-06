import json
from time import sleep
from pump_fun import buy, sell
import random

from config import RPC, client, payer_keypair
from utils import get_token_balance
from traceback import print_exc

# from solana.rpc.api import Client,


def main():

    mint_addr = "BBwV9WtsobWJStdY8o2ftxRkpyyNXG41SgSGErRXQWS4"

    try:
        while True:

            sol_amount = random.randint(1 * 10**8, 3 * 10**8) / 10**9
            buy(mint_str=mint_addr, sol_amount=sol_amount, slippage=10)
            # print("ret= {}".format(ret))

            sol_balance = client.get_balance(payer_keypair.pubkey()).value

            sell_flag = False
            if sol_balance / 10**9 < 10:
                # 如果余额不够，马上卖
                sell_flag = True

            if sell_flag or random.randint(0, 100) < 30:
                token_balance = get_token_balance(mint_str=mint_addr)

                # 卖出的百分比
                sell_amount = token_balance * random.randint(10, 30) / 100

                sell(
                    mint_str=mint_addr,
                    token_amount=sell_amount,
                    slippage=10,
                    close_token_account=False,
                )

            sleep(50)
        pass
    except Exception as e:
        print(e)
        print_exc(e)

    pass


if __name__ == "__main__":
    main()

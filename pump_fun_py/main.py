import json
from pump_fun import buy, sell

def main():

    mint_addr = 'BBwV9WtsobWJStdY8o2ftxRkpyyNXG41SgSGErRXQWS4'


    ret = buy(mint_str=mint_addr, sol_amount=0.1, slippage=10)
    # ret = sell(mint_str=mint_addr, token_balance=None, slippage=10, close_token_account=True)
    print(ret)

    pass

if __name__ == '__main__':
    main()
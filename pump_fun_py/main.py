from pump_fun import buy, sell


def main():

    mint_addr = '2W4qsMnmFZjeZZeVaix3mLUEg1t383hNdjcm6H31RUGh'
    # ret = buy(mint_str=mint_addr, sol_in=0.0123, slippage=10)
    ret = sell(mint_str=mint_addr, token_balance=None, slippage=10, close_token_account=True)
    print(ret)

    pass

if __name__ == '__main__':
    main()
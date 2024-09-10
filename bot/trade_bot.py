import json
from pprint import pprint
import random
import struct
import time
import requests
from solana.transaction import AccountMeta, Transaction
from spl.token.instructions import (
    create_associated_token_account,
    get_associated_token_address,
    close_account,
    CloseAccountParams,
)
from solders.pubkey import Pubkey  # type: ignore
from solders.instruction import Instruction  # type: ignore
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price  # type: ignore

# from config import payer_keypair, client
from bot.constants import *
from solana.rpc.types import TokenAccountOpts
from bot.calc import calc_buy_for_dy
from bot.utils import find_data
from solana.rpc.types import TxOpts
from typing import Optional, Union
from traceback import print_exc
from solana.rpc.api import Client
from solders.keypair import Keypair  # type: ignore
from solana.transaction import Signature
from solders.pubkey import Pubkey  # type: ignore
from spl.token.instructions import get_associated_token_address
from construct import Int8ub, Padding, Struct, Int64ul, Flag
from binascii import hexlify


class BondingData:
    y = 0  # 虚拟池子中token的数量
    x = 0  # 虚拟池子中SOL的数量
    is_complete = False

    def __init__(
        self, total_supply: int, reserve_token: int, reserve_sol: int, complete: bool
    ):
        self.is_complete = complete
        self.y = (total_supply - reserve_token) / 10**6
        self.x = reserve_sol / 10**9
        pass

    def __str__(self) -> str:
        return f"y:{self.y}, x:{self.x}, complete:{self.is_complete}"


class TradeBot:
    def __init__(self, rpc_client: Client, keypair: Keypair, mint_addr: str) -> None:
        self.client = rpc_client
        self.payer_keypair = keypair
        self.mint_addr = mint_addr

        self.pool_pda = ""
        pass

    def start(self, loop_secs=30):
        buy_probablity = 50
        while True:
            try:
                print("=====地址:{}".format(self.payer_keypair.pubkey()))

                pool_sol = 0
                if self.pool_pda == "":
                    coin_data = self.get_coin_data(self.mint_addr)
                    if coin_data is not None:
                        self.pool_pda = coin_data["pool_pda"]

                if self.pool_pda != "":
                    bonding_data = self.get_bonding_data(
                        Pubkey.from_string(self.pool_pda)
                    )
                    print("bonding data :{}".format(bonding_data))
                    # 池子中的sol越多，买入概率越小, 卖出概率越大
                    buy_probablity = (bonding_data.x / 80) * 100
                    pool_sol = bonding_data.x

                is_sell = random.randint(0, 100) < buy_probablity

                sol_balance = 0.0
                token_balance = 0.0
                sol_balance = self.client.get_balance(
                    self.payer_keypair.pubkey()
                ).value

                # if sol_balance < 1 * 10**9:
                #     print("领取空投: {}".format(self.payer_keypair.pubkey()))
                #     tmpCli = Client("https://api.devnet.solana.com")
                #     r = tmpCli.request_airdrop(
                #         self.payer_keypair.pubkey(), lamports=10**9
                #     )
                #     print("领取成功:{}".format(r.value))

                if True and sol_balance > 10**9 and pool_sol < 75:
                    time.sleep(random.randint(10, 50) / 10)

                    sol_amount = random.randint(1 * 10**8, 3 * 10**8) / 10**9
                    self.buy(
                        mint_str=self.mint_addr, sol_amount=sol_amount, slippage=10
                    )

                token_balance = self.get_token_balance(mint_str=self.mint_addr)
                print(
                    "{} token余额:{}, sol余额:{}".format(
                        self.payer_keypair.pubkey(), token_balance, sol_balance / 10**9
                    )
                )
                if sol_balance < 1*10**9 or pool_sol >= 75 or is_sell and token_balance > 1000000:
                    # 卖出的百分比
                    sell_amount = token_balance * random.randint(3, 10) / 100
                    self.sell(
                        mint_str=self.mint_addr,
                        token_amount=sell_amount,
                        slippage=10,
                        close_token_account=False,
                    )

                time.sleep(loop_secs)
            except Exception as e:
                print(e)
                print_exc(e)

        pass

    def buy(self, mint_str: str, sol_amount: float = 0.01, slippage: int = 25) -> bool:
        try:
            # Get coin data
            coin_data = self.get_coin_data(mint_str)
            pprint(coin_data)

            if not coin_data:
                print("Failed to retrieve coin data...")
                return

            owner = self.payer_keypair.pubkey()
            print("owner: ", owner)
            mint = Pubkey.from_string(mint_str)
            token_account, token_account_instructions = None, None

            # Attempt to retrieve token account, otherwise create associated token account
            try:
                account_data = self.client.get_token_accounts_by_owner(
                    owner, TokenAccountOpts(mint)
                )
                token_account = account_data.value[0].pubkey
                token_account_instructions = None
            except:
                token_account = get_associated_token_address(owner, mint)
                token_account_instructions = create_associated_token_account(
                    owner, owner, mint
                )

            # Define account keys required for the swap
            MINT = Pubkey.from_string(coin_data["mint"])
            BONDING_CURVE = Pubkey.from_string(coin_data["bonding_curve"])
            ASSOCIATED_BONDING_CURVE = Pubkey.from_string(
                coin_data["associated_bonding_curve"]
            )
            ASSOCIATED_USER = token_account
            USER = owner

            POOL_PDA = Pubkey.from_string(coin_data["pool_pda"])
            CURVE_CONFIG_PDA = Pubkey.from_string(coin_data["curve_config_pda"])
            self.pool_pda = coin_data["pool_pda"]

            bonding_data = self.get_bonding_data(POOL_PDA)
            print(bonding_data)
            assert bonding_data is not None, "empty bonding data"

            # token 数量
            token_amount = calc_buy_for_dy(x=bonding_data.x, dx=sol_amount)
            token_amount = int(token_amount * 10**6)
            print("token amount: {}".format(token_amount))

            # Build account key list
            keys = [
                # curve config,  即 dexConfigurationAccount
                AccountMeta(pubkey=CURVE_CONFIG_PDA, is_signer=False, is_writable=True),
                # pool PDA,  即 pool
                AccountMeta(pubkey=POOL_PDA, is_signer=False, is_writable=True),
                # token mint,  即 tokenMint
                AccountMeta(pubkey=MINT, is_signer=False, is_writable=True),
                # bonding curve  ata,  即 poolTokenAccount
                AccountMeta(
                    pubkey=ASSOCIATED_BONDING_CURVE, is_signer=False, is_writable=True
                ),
                # bondign curve PDA, 即 poolSolVault
                AccountMeta(pubkey=BONDING_CURVE, is_signer=False, is_writable=True),
                # 用户 token ata,  userTokenAccount
                AccountMeta(pubkey=ASSOCIATED_USER, is_signer=False, is_writable=True),
                # 手续费接收
                AccountMeta(pubkey=FEE_RECIPIENT, is_signer=False, is_writable=True),
                # 用户
                AccountMeta(pubkey=USER, is_signer=True, is_writable=True),
                # 系统
                AccountMeta(pubkey=RENT, is_signer=False, is_writable=False),
                AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
                AccountMeta(pubkey=TOKEN_PROGRAM, is_signer=False, is_writable=False),
                AccountMeta(
                    pubkey=ASSOC_TOKEN_ACC_PROG, is_signer=False, is_writable=False
                ),
                # ==============
                AccountMeta(pubkey=FANSLNAD_PROGRAM, is_signer=False, is_writable=True),
            ]

            # Construct the swap instruction
            data = bytearray()
            data.extend(bytes.fromhex("66063d1201daebea"))
            data.extend(struct.pack("<Q", int(token_amount)))
            data.extend(struct.pack("<Q", 10**9))  # TODO: 计算滑点
            data = bytes(data)
            swap_instruction = Instruction(FANSLNAD_PROGRAM, data, keys)

            # Construct and sign transaction
            recent_blockhash = self.client.get_latest_blockhash().value.blockhash
            txn = Transaction(recent_blockhash=recent_blockhash, fee_payer=owner)
            txn.add(set_compute_unit_price(UNIT_PRICE))
            txn.add(set_compute_unit_limit(UNIT_BUDGET))
            if token_account_instructions:
                txn.add(token_account_instructions)
            txn.add(swap_instruction)
            txn.sign(self.payer_keypair)

            # Send and confirm transaction
            txn_sig = self.client.send_transaction(
                txn, self.payer_keypair, opts=TxOpts(skip_preflight=True)  # TODO
            ).value
            print("Transaction Signature", txn_sig)
            confirm = self.confirm_txn(txn_sig)
            print(confirm)

        except Exception as e:
            print(e)
            # print_exc(e)

    def sell(
        self,
        mint_str: str,
        token_amount: Optional[Union[int, float]] = None,
        slippage: int = 25,
        close_token_account: bool = True,
    ) -> bool:
        try:
            # Get coin data
            coin_data = self.get_coin_data(mint_str)
            print(coin_data)
            if not coin_data:
                print("Failed to retrieve coin data...")
                return

            owner = self.payer_keypair.pubkey()
            mint = Pubkey.from_string(mint_str)

            # Get token account
            token_account = get_associated_token_address(owner, mint)

            # # Calculate token price
            # sol_decimal = 10**9
            token_decimal = 10**6
            # virtual_sol_reserves = coin_data['virtual_sol_reserves'] / sol_decimal
            # virtual_token_reserves = coin_data['virtual_token_reserves'] / token_decimal
            # token_price = virtual_sol_reserves / virtual_token_reserves
            # print(f"Token Price: {token_price:.20f} SOL")

            # Get token balance
            if token_amount == None:
                token_balance = self.get_token_balance(mint_str)
                token_account = token_balance  # 全部卖完
                print("Token Balance:", token_balance)

            if token_amount == 0:
                return

            # Calculate amount
            amount = int(token_amount * token_decimal)

            # Calculate minimum SOL output
            # sol_out = float(token_balance) * float(token_price)
            # slippage_adjustment = 1 - (slippage / 100)
            # sol_out_with_slippage = sol_out * slippage_adjustment
            # min_sol_output = int(sol_out_with_slippage * LAMPORTS_PER_SOL)
            # print("Min Sol Output:", sol_out_with_slippage)

            # Define account keys required for the swap
            MINT = Pubkey.from_string(coin_data["mint"])
            BONDING_CURVE = Pubkey.from_string(coin_data["bonding_curve"])
            ASSOCIATED_BONDING_CURVE = Pubkey.from_string(
                coin_data["associated_bonding_curve"]
            )
            ASSOCIATED_USER = token_account
            USER = owner
            POOL_PDA = Pubkey.from_string(coin_data["pool_pda"])
            CURVE_CONFIG_PDA = Pubkey.from_string(coin_data["curve_config_pda"])

            self.pool_pda = coin_data["pool_pda"]

            pool_pda_, bump = Pubkey.find_program_address(
                ["liquidity_sol_vault".encode(), bytes(mint)], FANSLNAD_PROGRAM
            )
            assert pool_pda_ == BONDING_CURVE, "invalid bonding curve pda"

            # Build account key list
            keys = [
                # curve config,  即 dexConfigurationAccount
                AccountMeta(pubkey=CURVE_CONFIG_PDA, is_signer=False, is_writable=True),
                # pool PDA,  即 pool
                AccountMeta(pubkey=POOL_PDA, is_signer=False, is_writable=True),
                # token mint,  即 tokenMint
                AccountMeta(pubkey=MINT, is_signer=False, is_writable=True),
                # bonding curve  ata,  即 poolTokenAccount
                AccountMeta(
                    pubkey=ASSOCIATED_BONDING_CURVE, is_signer=False, is_writable=True
                ),
                # bondign curve PDA, 即 poolSolVault
                AccountMeta(pubkey=BONDING_CURVE, is_signer=False, is_writable=True),
                # 用户 token ata,  userTokenAccount
                AccountMeta(pubkey=ASSOCIATED_USER, is_signer=False, is_writable=True),
                # 手续费接收
                AccountMeta(pubkey=FEE_RECIPIENT, is_signer=False, is_writable=True),
                # 用户
                AccountMeta(pubkey=USER, is_signer=True, is_writable=True),
                # 系统
                AccountMeta(pubkey=RENT, is_signer=False, is_writable=False),
                AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
                AccountMeta(pubkey=TOKEN_PROGRAM, is_signer=False, is_writable=False),
                AccountMeta(
                    pubkey=ASSOC_TOKEN_ACC_PROG, is_signer=False, is_writable=False
                ),
                # ==============
                AccountMeta(pubkey=FANSLNAD_PROGRAM, is_signer=False, is_writable=True),
            ]

            # Construct swap instruction
            # https://docs.python.org/3/library/struct.html
            data = bytearray()
            data.extend(bytes.fromhex("33e685a4017f83ad"))
            data.extend(struct.pack("<Q", amount))
            data.extend(struct.pack("<B", bump))
            data.extend(struct.pack("<Q", 1))  # TODO
            data = bytes(data)
            swap_instruction = Instruction(FANSLNAD_PROGRAM, data, keys)

            # Construct and sign transaction
            recent_blockhash = self.client.get_latest_blockhash().value.blockhash
            txn = Transaction(recent_blockhash=recent_blockhash, fee_payer=owner)
            txn.add(set_compute_unit_price(UNIT_PRICE))
            txn.add(set_compute_unit_limit(UNIT_BUDGET))
            txn.add(swap_instruction)
            if close_token_account:
                close_account_instructions = close_account(
                    CloseAccountParams(TOKEN_PROGRAM, token_account, owner, owner)
                )
                txn.add(close_account_instructions)
            txn.sign(self.payer_keypair)

            # Send and confirm transaction
            txn_sig = self.client.send_transaction(
                txn, self.payer_keypair, opts=TxOpts(skip_preflight=True)  # TODO
            ).value
            print("Transaction Signature", txn_sig)
            confirm = self.confirm_txn(txn_sig)
            print(confirm)

        except Exception as e:
            print(e)
            # print_exc(e)

    def confirm_txn(self, txn_sig, max_retries=20, retry_interval=3):
        retries = 0
        if isinstance(txn_sig, str):
            txn_sig = Signature.from_string(txn_sig)
        while retries < max_retries:
            try:
                txn_res = self.client.get_transaction(
                    txn_sig,
                    encoding="json",
                    commitment="confirmed",
                    max_supported_transaction_version=0,
                )
                txn_json = json.loads(txn_res.value.transaction.meta.to_json())
                if txn_json["err"] is None:
                    print("Transaction confirmed... try count:", retries + 1)
                    return True
                print("Error: Transaction not confirmed. Retrying...")
                if txn_json["err"]:
                    print(
                        "Transaction failed: {}".format(json.dumps(txn_json, indent=4))
                    )
                    return False
            except Exception as e:
                print("Awaiting confirmation... try count:", retries + 1)
                retries += 1
                time.sleep(retry_interval)
        print("Max retries reached. Transaction confirmation failed.")
        return None

    def get_token_balance(self, mint_str: str):
        try:
            headers = {"accept": "application/json", "content-type": "application/json"}

            payload = {
                "id": 1,
                "jsonrpc": "2.0",
                "method": "getTokenAccountsByOwner",
                "params": [
                    str(self.payer_keypair.pubkey()),
                    {"mint": mint_str},
                    {"encoding": "jsonParsed"},
                ],
            }

            response = requests.post(
                url=self.client._provider.endpoint_uri, json=payload, headers=headers
            )
            ui_amount = find_data(response.json(), "uiAmount")
            return float(ui_amount)
        except Exception as e:
            # print_exc(e)
            return 0

    def get_bonding_data(self, bonding_curve_pda: Pubkey) -> BondingData:
        bonding_curve_struct = Struct(
            Padding(8),
            Padding(32),  # pool_authority
            Padding(32),  # creator
            Padding(32),  # token
            "total_supply" / Int64ul,
            "reserve_token" / Int64ul,
            "reserve_sol" / Int64ul,
            "bump" / Int8ub,
            "complete" / Int8ub,
        )

        try:
            account_info = self.client.get_account_info(bonding_curve_pda)
            print(account_info)
            data = account_info.value.data
            print("data={}".format(hexlify(data)))
            parsed_data = bonding_curve_struct.parse(data)
            print("total supply = {}".format(parsed_data.total_supply))

            return BondingData(
                total_supply=parsed_data.total_supply,
                reserve_token=parsed_data.reserve_token,
                reserve_sol=parsed_data.reserve_sol,
                complete=parsed_data.complete,
            )

        except Exception as e:
            print("error: {}".format(e))
            return None

    def derive_pool_accounts(self, mint_str: str):
        try:
            mint = Pubkey.from_string(mint_str)
            bonding_curve, _ = Pubkey.find_program_address(
                ["liquidity_sol_vault".encode(), bytes(mint)], FANSLNAD_PROGRAM
            )
            associated_bonding_curve = get_associated_token_address(bonding_curve, mint)
            return bonding_curve, associated_bonding_curve
        except Exception:
            return None, None

    def derive_curve_config_pda(self) -> Pubkey:
        seed = "CurveConfiguration"
        curve_config_pda, _ = Pubkey.find_program_address(
            [seed.encode()], FANSLNAD_PROGRAM
        )
        return curve_config_pda

    def derive_pool_pda(self, mint_str: str) -> Pubkey:
        seed = "liquidity_pool"
        mint = Pubkey.from_string(mint_str)
        pool_pda, _ = Pubkey.find_program_address(
            [seed.encode(), bytes(mint)], FANSLNAD_PROGRAM
        )
        return pool_pda

    def get_coin_data(self, mint_str: str):
        bonding_curve, associated_bonding_curve = self.derive_pool_accounts(mint_str)
        if bonding_curve is None or associated_bonding_curve is None:
            return None

        curve_config_pda = self.derive_curve_config_pda()
        pool_pda = self.derive_pool_pda(mint_str)
        try:
            return {
                "mint": mint_str,
                "bonding_curve": str(bonding_curve),
                "associated_bonding_curve": str(associated_bonding_curve),
                "pool_pda": str(pool_pda),
                "curve_config_pda": str(curve_config_pda),
            }
        except Exception:
            return None

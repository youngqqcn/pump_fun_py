from pprint import pprint
import struct
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
from config import payer_keypair, client
from constants import *
from solana.rpc.types import TokenAccountOpts
from calc import calc_buy_for_dy
from utils import get_token_balance, confirm_txn
from solana.rpc.types import TxOpts
from coin_data import get_bonding_data, get_coin_data
from typing import Optional, Union

# def buy(mint_str: str, sol_in: float = 0.01, slippage: int = 25) -> bool:


def buy(mint_str: str, sol_amount: float = 0.01, slippage: int = 25) -> bool:
    try:
        # Get coin data
        coin_data = get_coin_data(mint_str)
        pprint(coin_data)

        if not coin_data:
            print("Failed to retrieve coin data...")
            return

        owner = payer_keypair.pubkey()
        print("owner: ", owner)
        mint = Pubkey.from_string(mint_str)
        token_account, token_account_instructions = None, None

        # Attempt to retrieve token account, otherwise create associated token account
        try:
            account_data = client.get_token_accounts_by_owner(
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

        bonding_data = get_bonding_data(POOL_PDA)
        pprint(str(bonding_data))
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
        data.extend(struct.pack("<Q", 10**9))
        data = bytes(data)
        swap_instruction = Instruction(FANSLNAD_PROGRAM, data, keys)

        # Construct and sign transaction
        recent_blockhash = client.get_latest_blockhash().value.blockhash
        txn = Transaction(recent_blockhash=recent_blockhash, fee_payer=owner)
        txn.add(set_compute_unit_price(UNIT_PRICE))
        txn.add(set_compute_unit_limit(UNIT_BUDGET))
        if token_account_instructions:
            txn.add(token_account_instructions)
        txn.add(swap_instruction)
        txn.sign(payer_keypair)

        # Send and confirm transaction
        txn_sig = client.send_transaction(
            txn, payer_keypair, opts=TxOpts(skip_preflight=True)
        ).value
        print("Transaction Signature", txn_sig)
        confirm = confirm_txn(txn_sig)
        print(confirm)

    except Exception as e:
        print(e)


def sell(
    mint_str: str,
    token_balance: Optional[Union[int, float]] = None,
    slippage: int = 25,
    close_token_account: bool = True,
) -> bool:
    try:
        # Get coin data
        coin_data = get_coin_data(mint_str)
        print(coin_data)
        if not coin_data:
            print("Failed to retrieve coin data...")
            return

        owner = payer_keypair.pubkey()
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
        if token_balance == None:
            token_balance = get_token_balance(mint_str)
        print("Token Balance:", token_balance)
        if token_balance == 0:
            return

        # Calculate amount
        amount = int(token_balance * token_decimal)

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
        data.extend(struct.pack("<Q", 100))  # TODO
        data = bytes(data)
        swap_instruction = Instruction(FANSLNAD_PROGRAM, data, keys)

        # Construct and sign transaction
        recent_blockhash = client.get_latest_blockhash().value.blockhash
        txn = Transaction(recent_blockhash=recent_blockhash, fee_payer=owner)
        txn.add(set_compute_unit_price(UNIT_PRICE))
        txn.add(set_compute_unit_limit(UNIT_BUDGET))
        txn.add(swap_instruction)
        if close_token_account:
            close_account_instructions = close_account(
                CloseAccountParams(TOKEN_PROGRAM, token_account, owner, owner)
            )
            txn.add(close_account_instructions)
        txn.sign(payer_keypair)

        # Send and confirm transaction
        txn_sig = client.send_transaction(
            txn, payer_keypair, opts=TxOpts(skip_preflight=True)
        ).value
        print("Transaction Signature", txn_sig)
        confirm = confirm_txn(txn_sig)
        print(confirm)

    except Exception as e:
        print(e)

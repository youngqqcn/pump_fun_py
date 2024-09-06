from solders.pubkey import Pubkey  # type: ignore
from spl.token.instructions import get_associated_token_address
from construct import Int8ub, Padding, Struct, Int64ul, Flag
from binascii import hexlify
from config import client
from constants import FANSLNAD_PROGRAM


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


def get_virtual_reserves(bonding_curve: Pubkey):
    bonding_curve_struct = Struct(
        Padding(8),
        "virtualTokenReserves" / Int64ul,
        "virtualSolReserves" / Int64ul,
        "realTokenReserves" / Int64ul,
        "realSolReserves" / Int64ul,
        "tokenTotalSupply" / Int64ul,
        "complete" / Flag,
    )

    try:
        account_info = client.get_account_info(bonding_curve)
        data = account_info.value.data

        parsed_data = bonding_curve_struct.parse(data)
        return parsed_data
    except Exception:
        return None


def get_bonding_data(bonding_curve_pda: Pubkey) -> BondingData:
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
        account_info = client.get_account_info(bonding_curve_pda)
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


def derive_pool_accounts(mint_str: str):
    try:
        mint = Pubkey.from_string(mint_str)
        bonding_curve, _ = Pubkey.find_program_address(
            ["liquidity_sol_vault".encode(), bytes(mint)], FANSLNAD_PROGRAM
        )
        associated_bonding_curve = get_associated_token_address(bonding_curve, mint)
        return bonding_curve, associated_bonding_curve
    except Exception:
        return None, None


def derive_curve_config_pda() -> Pubkey:
    seed = "CurveConfiguration"
    curve_config_pda, _ = Pubkey.find_program_address([seed.encode()], FANSLNAD_PROGRAM)
    return curve_config_pda


def derive_pool_pda(mint_str: str) -> Pubkey:
    seed = "liquidity_pool"
    mint = Pubkey.from_string(mint_str)
    pool_pda, _ = Pubkey.find_program_address(
        [seed.encode(), bytes(mint)], FANSLNAD_PROGRAM
    )
    return pool_pda


def get_coin_data(mint_str: str):
    bonding_curve, associated_bonding_curve = derive_pool_accounts(mint_str)
    if bonding_curve is None or associated_bonding_curve is None:
        return None

    curve_config_pda = (
        derive_curve_config_pda()
    )  # "6ASYfsmfsqkHudWo1MahkuhHPJrC5eSV36tLrgGeD18b"

    # SOMEONE
    pool_pda = derive_pool_pda(
        mint_str
    )  # "4ztHC14oxFUcRDYNWk459DujmQiSugvJNumDkcR2QEZ3"

    # virtual_reserves = get_virtual_reserves(bonding_curve)
    # if virtual_reserves is None:
    #     return None

    try:
        # virtual_token_reserves = int(virtual_reserves.virtualTokenReserves)
        # virtual_sol_reserves = int(virtual_reserves.virtualSolReserves)
        # token_total_supply = int(virtual_reserves.tokenTotalSupply)
        # complete = bool(virtual_reserves.complete)

        return {
            "mint": mint_str,
            "bonding_curve": str(bonding_curve),
            "associated_bonding_curve": str(associated_bonding_curve),
            "pool_pda": str(pool_pda),
            "curve_config_pda": str(curve_config_pda),
            # "virtual_token_reserves": virtual_token_reserves,
            # "virtual_sol_reserves": virtual_sol_reserves,
            # "token_total_supply": token_total_supply,
            # "complete": complete
        }
    except Exception:
        return None

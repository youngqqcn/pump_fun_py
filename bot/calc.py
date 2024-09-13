def cacl_buy_for_dx(
    dy: int, virtual_sol_reserve: int, virtual_token_reserve: int
) -> int:
    """买入，按照Token计算所需要的SOL的数量"""
    dx = int(int(dy * virtual_sol_reserve) / int(virtual_token_reserve - dy)) + 1
    return dx


def calc_buy_for_dy(
    dx: int, virtual_sol_reserve: int, virtual_token_reserve: int
) -> int:
    """买入，按照SOL计算"""

    dy = virtual_token_reserve - int(
        int(virtual_sol_reserve * virtual_token_reserve) / int(virtual_sol_reserve + dx)
        + 1
    )
    return dy


def calc_market_price(virtual_sol_reserve: int, virtual_token_reserve: int) -> float:
    """计算市场价格
    Args:
        x (float): 池子中最新的SOL数量

    Returns:
        float: 最新市场价格
    """
    market_price = virtual_sol_reserve * 1.0 / (virtual_token_reserve * 1.0 * 10**3)
    return market_price


def calc_sell_for_dx(
    dy: int, virtual_sol_reserve: int, virtual_token_reserve: int
) -> float:
    """计算卖出dy个token , 能够得到的 SOL数量"""

    dx = int(int(dy * virtual_sol_reserve) / int(virtual_token_reserve + dy))
    return dx

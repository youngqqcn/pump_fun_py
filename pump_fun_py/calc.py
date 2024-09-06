### k常量
K = 1073000000

### 常量
V = 32190000000


def cacl_buy_for_dx(x: float, dy: float) -> float:
    """买入，按照Token计算所需要的SOL的数量

    Args:
        x (float): 现有的SOL的数量
        dy (float): 买入的Token数量
    Returns:
        float: 买入 dy数量的token, 所需要花费的 SOL数量
    """
    dx = (dy * (30 + x) * (30 + x)) / (V - dy * (30 + x))
    return dx


def calc_buy_for_dy(x: float, dx: float) -> float:
    """买入，按照SOL计算

    Args:
        x (float): 现有的SOL的数量
        dx (float): 买入的SOL数量
    Returns:
        float: 能够购买的token数量
    """

    dy = (V * dx) / ((30 + x) * (30 + x + dx))
    return dy


def calc_market_price(x: float) -> float:
    """计算市场价格

    Args:
        x (float): 池子中最新的SOL数量

    Returns:
        float: 最新市场价格
    """
    market_price = ((30 + x) * (30 + x)) / V
    return market_price


def calc_sell_for_dx(y: float, dy: float) -> float:
    """计算卖出dy个token , 能够得到的 SOL数量

    Args:
        y (float): 池子中现有的token数量
        dy (float): 要卖出的token数量

    Returns:
        float: 能够得到的 SOL 数量
    """


    dx = (V * dy) / ((K - y) * (K - y + dy))
    return dx

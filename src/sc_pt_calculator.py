# xb_pt_calculator.py
import sys
from sc_symbol import Symbol


# get buy and sell prices given the net euro balance and the quantity (qb=qs)
def get_prices_given_neb(mp: float, symbol: Symbol):
    # get parameters from config.ini
    # config = configparser.ConfigParser()
    # config.read('config.ini')
    config = symbol.config_data
    fee = float(config['fee'])
    quantity = float(config['quantity'])
    neb = float(config['net_quote_balance'])

    bp = mp * (1 - fee) - neb / (2 * quantity)
    sp = mp * (1 + fee) + neb / (2 * quantity)

    return bp, sp, quantity


def get_pt_values(
        mp: float,  # reference market price
        nab: float,  # net amount balance
        s1_qty: float,  # s1_amount
        buy_fee: float,  # buy fee,
        sell_fee: float,  # sell fee
        geb: float = 0):  # forced to create a perfect trade

    """create perfect trade"""
    cost = buy_fee / (1 - buy_fee) * (nab + s1_qty) + sell_fee * s1_qty
    gbb = nab + cost
    b1_qty = gbb + s1_qty
    b1_price = (2 * mp * s1_qty - geb) / (b1_qty + s1_qty)
    s1_price = (2 * mp * b1_qty + geb) / (b1_qty + s1_qty)
    g = (mp * (b1_qty - s1_qty) + geb) / (b1_qty + s1_qty)

    return b1_qty, b1_price, s1_price, g


def get_compensation(
        cmp: float,
        gap: float,
        qty_bal: float,
        price_bal: float,
        buy_fee: float,
        sell_fee: float):
    """get both orders values after compensation
        cmp: current market price
        gap: gap
        qty_bal: 1st symbol balance in BTC/EUR
        price_bal: 2nd symbol balance"""
    s1_p = 0.0
    b1_p = 0.0
    n1 = 0.0
    try:
        s1_p = cmp + gap
        b1_p = cmp - gap
        a = price_bal + b1_p * qty_bal * (1 + buy_fee)
        b = s1_p * (1 - sell_fee) - b1_p * (1 + buy_fee)
        s1_qty = a / b
        b1_qty = qty_bal + s1_qty

        n1 = (1 + sell_fee) / (1-buy_fee)
        n2 = qty_bal / (1 - buy_fee)
        s1_qty = (price_bal + b1_p * n2) / (s1_p - b1_p * n1)
        b1_qty = s1_qty * n1 + n2
    except ZeroDivisionError as e:
        print(e)
        print(f's1_p: {s1_p} b1_p: {b1_p} n1: {n1} b1_p * n1: {b1_p * n1}')
        sys.exit()

    return s1_p, b1_p, s1_qty, b1_qty

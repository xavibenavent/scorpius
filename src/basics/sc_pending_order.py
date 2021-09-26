# sc_pending_order.py

from binance import enums as k_binance


class PendingOrder:
    def __init__(self,
                 symbol_name: str,
                 uid: str,
                 k_side: k_binance,
                 price: float,
                 qty: float):
        self.symbol_name = symbol_name
        self.uid = uid
        self.k_side = k_side
        self.price = price
        self.qty = qty

    def get_tuple_for_pending_order_table(self) -> (str, str, k_binance, float, float):
        return self.symbol_name, self.uid, self.k_side, self.price, self.qty


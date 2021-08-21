# pp_balance_manager.py

from typing import List, Dict
from binance import enums as k_binance

from sc_account_balance import AccountBalance
from sc_market import Market
from sc_order import Order

EUR_MIN_BALANCE = 1000.0  # 2000.0  # remaining guaranteed EUR balance
BTC_MIN_BALANCE = 0.02  # 0.04  # remaining guaranteed BTC balance

# below _MIN_BALANCE + BUFFER some liquidity will be forced
EUR_BUFFER = 1000.0
BTC_BUFFER = 0.02


class Account:
    # ASSET_NAME = 'a'
    # FREE = 'f'
    # LOCKED = 'l'

    def __init__(self, name: str, free=0.0, locked=0.0):
        self.name = name
        self.free = free
        self.locked = locked

    def get_total(self) -> float:
        return self.free + self.locked


class BalanceManager:
    def __init__(self, market: Market, account_names: List[str]):
        self.market = market[]

        self.accounts = []

        # set accounts
        for name in account_names:
            account=self.market.get_account(asset_name=name)
            if account:
                self.accounts.append(account)

    def update_current_accounts(self, received_accounts: List[Account]) -> None:
        # loop through names of received accounts
        for received_account in received_accounts:
            # compare against already existing accounts
            # if exists, update it, otherwise add new account
            account_updated = False
            for account in self.accounts:
                if account.name == received_account.name:
                    # update account
                    account.free = received_account.free
                    account.locked = received_account.locked
                    account_updated = True
                    break
            # create new account if it doesn't exist
            if not account_updated:
                self.accounts.append(received_account)

    def is_s2_below_buffer(self):
        buffer = EUR_BUFFER + EUR_MIN_BALANCE
        return self.current_ab.s2.get_total() < buffer  # total = free + locked

    def is_s1_below_buffer(self):
        buffer = BTC_BUFFER + BTC_MIN_BALANCE
        return self.current_ab.s1.get_total() < buffer

    def get_account_balance(self, tag='') -> AccountBalance:
        btc_bal = self.market.get_asset_balance(asset='BTC', tag=tag)
        eur_bal = self.market.get_asset_balance(asset='EUR', tag=tag, p=2)
        bnb_bal = self.market.get_asset_balance(asset='BNB', tag=tag)
        d = dict(s1=btc_bal, s2=eur_bal, bnb=bnb_bal)
        return AccountBalance(d)

    def is_balance_enough(self, order: Order) -> (bool, float, float):
        # if enough balance, it returns True, 0, 0
        # if False, it returns False, eur_liquidity, btc_liquidity
        # is_balance_enough = False
        if order.k_side == k_binance.SIDE_BUY:
            balance_allowance = self.current_ab.get_free_price_s2()
            eur_liquidity = balance_allowance - EUR_MIN_BALANCE  # [EUR]
            if (eur_liquidity - order.get_total()) > 0:
                # is_balance_enough = True
                return True, 0, 0
            else:
                return False, eur_liquidity, 0
        else:  # SIDE_SELL
            balance_allowance = self.current_ab.get_free_amount_s1()
            btc_liquidity = balance_allowance - BTC_MIN_BALANCE  # [BTC]
            if (btc_liquidity - order.amount) > 0:
                # is_balance_enough = True
                return True, 0, 0
            else:
                return False, 0, btc_liquidity

        # return is_balance_enough

    @staticmethod
    def get_balance_for_list(orders: List[Order]) -> (float, float, float, float):
        balance_amount = 0.0
        balance_total = 0.0
        balance_commission = 0.0
        comm_btc = 0.0
        for order in orders:
            balance_amount += order.get_signed_amount()
            balance_total += order.get_signed_total()
            balance_commission += order.bnb_commission
            # comm_btc += order.btc_commission
        return balance_amount, balance_total, balance_commission  # , comm_btc

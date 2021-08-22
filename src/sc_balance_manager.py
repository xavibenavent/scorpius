# pp_balance_manager.py

from typing import List, Optional
import logging

# EUR_MIN_BALANCE = 1000.0  # 2000.0  # remaining guaranteed EUR balance
# BTC_MIN_BALANCE = 0.02  # 0.04  # remaining guaranteed BTC balance
#
# # below _MIN_BALANCE + BUFFER some liquidity will be forced
# EUR_BUFFER = 1000.0
# BTC_BUFFER = 0.02

log = logging.getLogger('log')


class Account:
    def __init__(self, name: str, free=0.0, locked=0.0):
        self.name = name.upper()
        self.free = free
        self.locked = locked

    def get_total(self) -> float:
        return self.free + self.locked


class BalanceManager:
    def __init__(self, accounts: List[Account]):
        self.accounts = accounts

    def update_current_accounts(self, received_accounts: List[Account]) -> None:
        log.debug([account.name for account in received_accounts])
        log.debug([account.name for account in self.accounts])
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

        log.debug([account.name for account in self.accounts])

    def get_account_by_name(self, name: str) -> Optional[Account]:
        for account in self.accounts:
            if account.name == name:
                return account
        return None

    # @staticmethod
    # def get_balance_for_list(orders: List[Order]) -> (float, float, float, float):
    #     balance_amount = 0.0
    #     balance_total = 0.0
    #     balance_commission = 0.0
    #     comm_btc = 0.0
    #     for order in orders:
    #         balance_amount += order.get_signed_amount()
    #         balance_total += order.get_signed_total()
    #         balance_commission += order.bnb_commission
    #         # comm_btc += order.btc_commission
    #     return balance_amount, balance_total, balance_commission  # , comm_btc

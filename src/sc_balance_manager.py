# pp_balance_manager.py

from typing import List, Optional
import logging

from sc_symbol import Asset

log = logging.getLogger('log')


class Account:
    def __init__(self, name: str, free=0.0, locked=0.0, precision_for_visualization=2):
        self.name = name.upper()
        self.free = free
        self.locked = locked
        self.asset = Asset(name=name)

    def get_total(self) -> float:
        return self.free + self.locked


class BalanceManager:
    def __init__(self, accounts: List[Account]):
        self.accounts = accounts

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

    def get_account(self, name: str) -> Optional[Account]:
        for account in self.accounts:
            if account.name == name:
                return account
        return None

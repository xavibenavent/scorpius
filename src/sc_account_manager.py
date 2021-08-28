# sc_account_manager.py
import pprint
from typing import List, Optional, Dict
import logging

from sc_symbol import Asset

log = logging.getLogger('log')


class Account:
    def __init__(self, name: str, free=0.0, locked=0.0):
        self.name = name.upper()
        self.free = free
        self.locked = locked

    def get_total(self) -> float:
        return self.free + self.locked


class AccountManager:
    def __init__(self, accounts: List[Account]):
        # create dict of Accounts
        self.accounts: Dict[str, Account] = {}
        for a in accounts:
            self.accounts[a.name] = a
        pprint.pprint(self.accounts)

    def update_current_accounts(self, received_accounts: List[Account]) -> None:
        for a in received_accounts:
            if a.name in self.accounts.keys():
                # update values
                self.accounts[a.name].free = a.free
                self.accounts[a.name].locked = a.locked
            else:
                # add new account
                self.accounts[a.name] = a

    def get_account(self, name: str) -> Optional[Account]:
        if name in self.accounts.keys():
            return self.accounts[name]
        # if not found
        return None

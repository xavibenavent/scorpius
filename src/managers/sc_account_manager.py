# sc_account_manager.py
from typing import List, Optional, Dict
import logging

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
        print('available accounts:')
        for a in accounts:
            self.accounts[a.name] = a
            print(f'{a.name} locked: {a.locked} free: {a.free}')

    def update_current_accounts(self, received_accounts: List[Account]) -> None:
        for a in received_accounts:
            if a.name in self.accounts.keys():
                # update values
                # log.info(f'account: {a.name} free updated from {self.accounts[a.name].free} to {a.free}')
                # log.info(f'account: {a.name} locked updated from {self.accounts[a.name].locked} to {a.locked}')
                self.accounts[a.name].free = a.free
                self.accounts[a.name].locked = a.locked
            else:
                # add new account
                # log.info(f'account: {a.name} set to free {a.free} locked {a.locked}')
                self.accounts[a.name] = a

    def get_account(self, name: str) -> Optional[Account]:
        if name in self.accounts.keys():
            return self.accounts[name]
        # if not found
        return None

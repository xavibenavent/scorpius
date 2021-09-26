# sc_db_manager.py
import sqlite3
from sqlite3 import Connection, Error
from typing import List, Optional
from binance import enums as k_binance
import logging

from basics.sc_action import Action

log = logging.getLogger('log')


class DBManager:
    FILE_NAME = 'database.db'
    ACTIONS_TABLE = 'actions'
    ORDERS_TABLE = 'orders'

    def __init__(self, tables: List[str]):
        self.conn = self._create_connection()
        self.cursor = self.conn.cursor()

        # create tables if they do not exist
        try:
            if self.ACTIONS_TABLE in tables:
                query = f'CREATE TABLE IF NOT EXISTS {self.ACTIONS_TABLE} '
                query += '(action_id TEXT, side TEXT, qty REAL, price REAL);'
                self.cursor.execute(query)
                self.conn.commit()
            elif self.ORDERS_TABLE in tables:
                pass
        except Error as e:
            log.critical(e)

        pass

    def __del__(self):
        log.info('closing cursor and connection to database')
        self.conn.close()

    def add_action(self, action: Action):
        try:
            # aligned with Action class
            self.cursor.execute(f'INSERT INTO {self.ACTIONS_TABLE} VALUES (?, ?, ?, ?)', action.get_tuple())
            self.conn.commit()
        except Error as e:
            log.critical(e)

    def delete_action(self, action: Action):
        try:
            query = f'DELETE FROM {self.ACTIONS_TABLE} WHERE action_id = ?'
            self.cursor.execute(query, (action.action_id,))
            self.conn.commit()
        except Error as e:
            log.critical(e)

    def get_all_actions(self) -> Optional[List[Action]]:
        try:
            query = f'SELECT * FROM {self.ACTIONS_TABLE};'
            rows = self.cursor.execute(query).fetchall()
            return [self._get_action_from_row(row) for row in rows]
        except Error as e:
            log.critical(e)
        return None

    @staticmethod
    def _get_action_from_row(row: list) -> Action:
        return Action(
            action_id=row[0],
            side=row[1],
            qty=row[2],
            price=row[3]
        )

    def _create_connection(self) -> Optional[Connection]:
        try:
            conn = sqlite3.connect(
                database=self.FILE_NAME,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
                check_same_thread=False
            )
            return conn
        except Error as e:
            log.critical(e)
        return None

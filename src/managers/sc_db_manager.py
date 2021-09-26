# sc_db_manager.py
import sqlite3
from sqlite3 import Connection, Error
from typing import List, Optional
from binance import enums as k_binance
import logging

from basics.sc_action import Action
from basics.sc_order import Order
from basics.sc_pending_order import PendingOrder

log = logging.getLogger('log')


class DBManager:
    FILE_NAME = 'database.db'
    ACTIONS_TABLE = 'actions'
    PENDING_ORDERS_TABLE = 'orders'

    def __init__(self):
        self.conn = self._create_connection()
        self.cursor = self.conn.cursor()

        # create tables if they do not exist
        try:
            # ACTIONS TABLE
            query = f'CREATE TABLE IF NOT EXISTS {self.ACTIONS_TABLE} '
            query += '(action_id TEXT, side TEXT, qty REAL, price REAL);'
            self.cursor.execute(query)
            self.conn.commit()
            # PENDING ORDERS TABLE
            query = f'CREATE TABLE IF NOT EXISTS {self.PENDING_ORDERS_TABLE} '
            query += '(symbol_name TEXT, uid TEXT, k_side TEXT, price REAL, qty REAL);'
            self.cursor.execute(query)
            self.conn.commit()
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

    def add_pending_order(self, pending_order: PendingOrder):
        try:
            # aligned with Order class
            self.cursor.execute(f'INSERT INTO {self.PENDING_ORDERS_TABLE} VALUES (?, ?, ?, ?, ?)',
                                pending_order.get_tuple_for_pending_order_table())
            self.conn.commit()
            log.info(f'added pending order {pending_order}')
        except Error as e:
            log.critical(e)

    def delete_action(self, action: Action):
        try:
            query = f'DELETE FROM {self.ACTIONS_TABLE} WHERE action_id = ?'
            self.cursor.execute(query, (action.action_id,))
            self.conn.commit()
        except Error as e:
            log.critical(e)

    def delete_pending_order(self, pending_order_uid: str):
        try:
            query = f'DELETE FROM {self.PENDING_ORDERS_TABLE} WHERE uid = ?'
            self.cursor.execute(query, (pending_order_uid,))
            self.conn.commit()
            log.info(f'deleted pending order wirh uid {pending_order_uid}')
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

    def get_all_pending_orders(self) -> Optional[List[PendingOrder]]:
        try:
            query = f'SELECT * FROM {self.PENDING_ORDERS_TABLE};'
            rows = self.cursor.execute(query).fetchall()
            return [self._get_pending_order_from_row(row) for row in rows]
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

    @staticmethod
    def _get_pending_order_from_row(row: list) -> PendingOrder:
        return PendingOrder(
            symbol_name=row[0],
            uid=row[1],
            k_side=row[2],
            price=row[3],
            qty=row[4]
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

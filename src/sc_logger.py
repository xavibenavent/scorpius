# sc_logger.py

import logging


class XBLogger:
    def __init__(self):
        log = logging.getLogger('log')
        log.setLevel(logging.DEBUG)

        # setup file handler & formatter
        ch = logging.FileHandler(filename='log/scorpius.log', mode='w')

        # setup output string
        # format_s = '%(levelname)-8s %(message)s'
        # format_s = '%(levelname)-8s %(asctime)s %(filename)-20s %(funcName)-25s %(message)s'
        format_s = '%(asctime)s %(levelname)-8s %(funcName)-25s %(message)s'

        formatter = logging.Formatter(format_s)
        ch.setFormatter(formatter)
        log.addHandler(ch)

        # %(threadName)-20s, %(asctime)s, %(filename)-20s, %(funcName)-25s

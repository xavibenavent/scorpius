# xb_logger.py

import logging


class XBLogger:
    def __init__(self):
        log = logging.getLogger('log')
        log.setLevel(logging.DEBUG)

        # setup file handler & formatter
        ch = logging.FileHandler(filename='log/scorpius.log', mode='w')

        # setup output string
        s1 = '%(threadName)-20s, %(filename)-20s, %(funcName)-25s, %(levelname)-8s'
        s2 = '- %(message)s'
        format_s = s1 + s2

        formatter = logging.Formatter(format_s)
        ch.setFormatter(formatter)
        log.addHandler(ch)

        # %(asctime)s, %(filename)-20s, %(funcName)-25s

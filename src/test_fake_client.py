# test_fake_client.py
import time

from sc_fake_client import FakeClient, FakeCmpMode


def p(cmp: float):
    print(cmp)


if __name__ == '__main__':
    fc = FakeClient(user_socket_callback=p, symbol_ticker_callback=p, cmp=40000, fake_cmp_mode=FakeCmpMode.MODE_GENERATOR)
    fc.start_cmp_generator()
    time.sleep(2)
    fc.stop_cmp_generator()



# sc_df_manager.py

from sc_session import Session, ClientMode

print('sc_df_manager.py')
# create session
# session = Session(client_mode=ClientMode.CLIENT_MODE_SIMULATOR)


class DataframeManager:
    def __init__(self):
        self.session = Session(client_mode=ClientMode.CLIENT_MODE_SIMULATOR)

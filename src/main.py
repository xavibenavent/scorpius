# main.py

import logging
from dash_app import app
import dash_callbacks  # do not delete
# from dash_callbacks import session
from sc_session import Session, QuitMode
from sc_market import ClientMode
from sc_logger import XBLogger

# # create session
# session = Session(client_mode=ClientMode.CLIENT_MODE_SIMULATOR)
print('main.py')

XBLogger()
log = logging.getLogger('log')


'''
    The Code Reloading feature is provided by Flask & Werkzeug via
    the use_reloader keyword. A caveat of Code Reloading is that
    your app code is run twice when starting: once to start the parent
    process and another time to run the child process that gets reloaded.
'''

server = app.server

if __name__ == '__main__':
    # dev_tools_hot_release=False to avoid going twice in this file
    app.run_server(dev_tools_ui=True, dev_tools_hot_reload=False)
    # session.quit(quit_mode=QuitMode.CANCEL_ALL_PLACED)




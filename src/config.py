"""
The config.py file contains some global parameters for the application, such as the length of the channel keys and the location for the server's private certificate. It also contains the string for the banner.
"""

class logo:
    text = '''
 _____                       _____        __     _____ _           _   
/  ___|                     /  ___|      / _|   /  __ \ |         | |  
\ `--. _   _ _ __   ___ _ __\ `--.  __ _| |_ ___| /  \/ |__   __ _| |_ 
 `--. \ | | | '_ \ / _ \ '__|`--. \/ _` |  _/ _ \ |   | '_ \ / _` | __|
/\__/ / |_| | |_) |  __/ |  /\__/ / (_| | ||  __/ \__/\ | | | (_| | |_ 
\____/ \__,_| .__/ \___|_|  \____/ \__,_|_| \___|\____/_| |_|\__,_|\__|
            | |                                                        
v0.0.1      |_|                          by: @edvtaz, @???, @szilard95  
'''[1:]


SECURE_CHANNEL_KEY_SIZE_BYTES = 16
SERVER_SIGNING_KEY_PATH = 'private_sig.pem'
DISPLAY_HISTORY_SIZE = 4
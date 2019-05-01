import os
import sys
import socket
import threading
import frontend
import json
import messaging.client

STORAGE = None
CHAN = ""
ADDRESS = ""
SOCK = None
USER, PW = "", ""
SYMKEY = None
create_chan_event = threading.Event()
invite_event = threading.Event()
replay_finished = threading.Event()


def run(address, storagePath):
    global STORAGE
    global CHAN
    global ADDRESS
    global SOCK
    global USER
    global PW
    global SYMKEY
    global create_chan_event
    global invite_event
    global replay_finished

    create_chan_event.clear()
    invite_event.clear()
    replay_finished.clear()

    with open(storagePath, 'rt') as f:
        STORAGE = json.load(f)
        STORAGE['channels'] = dict()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        ADDRESS = address
        ip, port = address.split(':')
        address = (ip, int(port))
        sock.connect(address)
        SOCK = sock

        USER, PW = frontend.get_user()
        SYMKEY = messaging.client.init_connection(sock, USER)

        frontend_thread = threading.Thread(target=main_menu)
        frontend_thread.start()

        listen(sock)


def listen(sock):
    global STORAGE
    global CHAN
    global ADDRESS
    global SOCK
    global USER
    global PW
    global SYMKEY
    global create_chan_event
    global invite_event
    global replay_finished

    while True:
        msg = messaging.common.recv_message(sock, SYMKEY)
        print(f"recvd: {msg}")

# ==============================================================================
        if msg['type'] == "addUser":
            stored_format = {
                'inviter': msg['inviter'],
                'payload': msg,
                'timestamp': msg['timestamp']
            }
            if msg['inviter'] == msg['invitee']:
                create_chan_event.set()
                if msg['channelID'] not in STORAGE['channels']:
                    STORAGE['channels'][msg['channelID']] = {
                        'invites': {
                            msg['invitee']: stored_format},
                        'messages': []
                    }
                if msg['invitee'] == USER:
                    # TODO recover key and verify contents
                    STORAGE['channels'][msg['channelID']
                                        ]['channelkey'] = b"asdf"
            else:
                invite_event.set()
                STORAGE['channels'][msg['channelID']
                                    ]['invites'][msg['invitee']] = stored_format
                if msg['invitee'] == USER:
                    # TODO recover key and verify contents
                    STORAGE['channels'][msg['channelID']
                                        ]['channelkey'] = b"asdf"
# ==============================================================================
        elif msg['type'] == "comms":
            # TODO decrypt message
            STORAGE['channels'][msg['channelID']
                                ]['messages'].append({
                                    'timestamp': msg['timestamp'],
                                    'sender': msg['userID'],
                                    'text': msg['msg'],
                                    'payload': msg
                                })  # TODO
            if CHAN == msg['channelID']:
                frontend.display_message(
                    msg['sender'], msg['timestamp'], msg['msg'])
# ==============================================================================
        elif msg['type'] == "replayFinished":
            replay_finished.set()
# ==============================================================================


def main_menu():
    global STORAGE
    global CHAN
    global ADDRESS
    global SOCK
    global USER
    global PW
    global SYMKEY
    global create_chan_event
    global invite_event
    global replay_finished

    replay_finished.wait()
    choice = frontend.main_menu(ADDRESS, STORAGE['storage']['channels'].keys())

    while choice == None:
        new_chan = frontend.new_channel()  # check if there is no name collision TODO
        create_chan_event.clear()
        messaging.client.new_channel(SOCK, USER, new_chan)
        create_chan_event.wait()

        while new_chan not in STORAGE['storage']['channels']:
            frontend.failure('of reasons')
            new_chan = frontend.new_channel()  # check if there is no name collision TODO

            create_chan_event.clear()
            messaging.client.new_channel(SOCK, USER, new_chan)
            create_chan_event.wait()

        frontend.success()
        choice = frontend.main_menu(
            ADDRESS, STORAGE['storage']['channels'].keys())

    chat(choice)


def chat(channel):
    global STORAGE
    global CHAN
    global ADDRESS
    global SOCK
    global USER
    global PW
    global SYMKEY
    global create_chan_event
    global invite_event
    global replay_finished

    CHAN = channel

    frontend.display_channel(channel)

    iii = ""
    while True:
        iii += sys.stdin.read(1)

        if iii[-1] == '\n':
            messaging.client.send_msg(SOCK, channel, USER, iii)
            iii = ""
        elif iii == ':invite':
            iii = ""
            user = frontend.invite_user()
            invite_event.clear()
            messaging.client.invite_user(SOCK, channel, USER, user)
            invite_event.wait()
            if True:  # TODO check if user invite was successful
                frontend.success()
            else:
                frontend.failure('of reasons')

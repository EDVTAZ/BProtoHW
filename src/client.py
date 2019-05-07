import os
import sys
import socket
import threading
import frontend
import json
import messaging.client
import messaging.common
import copy
import config
from StringKeys import kk
from session import Session
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.Signature import pss
from base64 import b64decode, b64encode
from utils import getch

"""
The client.py file contains code controlling the main execution flow of the client. The run function needs to be called to initiate a client.
"""

SESSION = None

"""
The run function loads the storage, connects to the server, creates a new Session object, that is used to start the main menu on a new thread and listen for incoming messages on the original thread.
"""


def run(address, storagePath, user, pw):
    global SESSION

    with open(storagePath, 'rt') as f:
        storage = json.load(f)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        ip, port = address.split(':')
        address = (ip, int(port))
        sock.connect(address)

        if user == None or pw == None:
            user, pw = frontend.get_user()

        SESSION = Session(
            storage=storage, saddr=address, socket=sock, user=user, pw=pw)
        messaging.client.init_connection(SESSION)

        frontend_thread = threading.Thread(target=main_menu)
        frontend_thread.start()

        listen(sock)


"""
The listen function handles incomming messages from the server, and calls the respective handler for the message on the session object.
"""


def listen(sock):
    global SESSION

    while True:
        try:
            msg = messaging.common.recv_message(sock, SESSION.symkey)
            mt = msg[kk.typ]

            if mt in (kk.add_user, kk.comms) and kk.timestamp not in msg:
                # no timestamp attached means this is a replayed message => drop it
                print('Replayed message detected')
                continue

            if mt == kk.add_user:
                SESSION.add_user(msg)
            elif mt == kk.comms:
                SESSION.incomm(msg)
            elif mt == kk.replay_finished:
                SESSION.replay_finished.set()
            elif mt == kk.error:
                print(f'Server says nono:\n{msg}')
        except Exception as e:
            print('That\'s a big nono.')
            print(e)


"""
The main_menu function lists known channels, handles the execution of creating new channels and joining existing channels.
"""


def main_menu():
    global SESSION

    SESSION.replay_finished.wait()
    choice = frontend.main_menu(
        SESSION.saddr, SESSION.user, SESSION.get_channels())

    while choice == None:
        new_chan = frontend.new_channel()  # check if there is no name collision TODO
        messaging.client.new_channel(SESSION, new_chan)
        SESSION.create_chan_event.wait()

        while new_chan not in SESSION.get_channels():
            frontend.failure('of reasons')
            new_chan = frontend.new_channel()  # check if there is no name collision TODO

            messaging.client.new_channel(SESSION, new_chan)
            SESSION.create_chan_event.wait()

        frontend.success()
        choice = frontend.main_menu(
            SESSION.saddr, SESSION.user, SESSION.get_channels())

    chat(choice)


"""
The chat function handles input from the user in a channel. Possible actions are sending messages, inviting users and exiting the application.
"""


def chat(channel):
    global SESSION

    SESSION.chan = channel
    frontend.display_channel(channel)
    print(f"""Not displaying additional {
                max(len(SESSION.storage[kk.chs][channel]
                    [kk.messages])-config.DISPLAY_HISTORY_SIZE, 0)
            } messages from history!""")
    for m in SESSION.storage[kk.chs][channel][kk.messages][-config.DISPLAY_HISTORY_SIZE:]:
        frontend.display_message(m[kk.sender], m[kk.timestamp], m[kk.text])

    iii = ""
    while True:
        frontend.type_message(iii)
        iii += getch()
        frontend.type_message(iii)

        if iii == ':exit':
            SESSION.persist()
            try:
                sys.exit(0)
            except SystemExit:
                os._exit(0)
        elif iii == ':invite':
            iii = ""
            user = frontend.invite_user()
            messaging.client.invite_user(SESSION, user)
        elif iii[-1] == '|':
            frontend.type_message("")
            messaging.client.send_msg(SESSION, iii[:-1])
            iii = ""
        elif iii[-1] == '\b' or ord(iii[-1]) == 127:
            iii = iii[:-2]

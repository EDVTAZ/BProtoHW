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


SESSION = None


def run(address, storagePath):
    global SESSION

    with open(storagePath, 'rt') as f:
        storage = json.load(f)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        ip, port = address.split(':')
        address = (ip, int(port))
        sock.connect(address)

        user, pw = frontend.get_user()

        SESSION = Session(
            storage=storage, saddr=address, socket=sock, user=user, pw=pw)
        messaging.client.init_connection(SESSION)

        frontend_thread = threading.Thread(target=main_menu)
        frontend_thread.start()

        listen(sock)


def listen(sock):
    global SESSION

    while True:
        msg = messaging.common.recv_message(sock, SESSION.symkey)
        print(f"recvd: {msg}")
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


def main_menu():
    global SESSION

    SESSION.replay_finished.wait()
    choice = frontend.main_menu(SESSION.saddr, SESSION.get_channels())

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
        choice = frontend.main_menu(SESSION.saddr, SESSION.get_channels())

    chat(choice)


def chat(channel):
    global SESSION

    SESSION.chan = channel
    frontend.display_channel(channel)

    iii = ""
    while True:
        iii += sys.stdin.read(1)

        if iii[-1] == '\n':
            messaging.client.send_msg(SESSION, iii)
            iii = ""
        elif iii == ':exit':
            SESSION.persist()
            exit(0)
        elif iii == ':invite':
            iii = ""
            user = frontend.invite_user()
            messaging.client.invite_user(SESSION, user)
            SESSION.invite_event.wait()
            if True:  # TODO check if user invite was successful
                frontend.success()
            else:
                frontend.failure('of reasons')
        elif iii[-1] == '\b':
            iii = iii[0:-1]

        frontend.type_message(iii)

import socket
import threading
import socketserver
import struct
import json
import config
import base64 as b64
import time
import signal
import sys
import os
from Crypto.Random import get_random_bytes
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.Signature import pss
from messaging import common
from session import Session
from StringKeys import kk


g_sessions = []
g_storage = {}
g_storage_path = ''
g_signing_key = None

"""
ThreadedTCPRequestHandler class is responsible for handling client requests. A new instance of this class is created automatically every time a new client connects. The new instance listens for incoming messages and handles them in accordance to their type. The secure connection is inited with initConn and initKey messages and if that is successful all subsequent messages are checked as specified and the ones that pass and need to be forwarded are broadcasted to the correct users.
"""


class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    """
    The setup function initilizes the current user's Session object, and stores it in the session storage (containing the current connections).
    """

    def setup(self):
        global g_storage
        global g_sessions
        global g_signing_key
        print(f'Connection from {self.client_address}')

        self.current_session = Session(
            g_storage, self.client_address, self.request)
        self.current_session.signing_key = g_signing_key
        self.current_session.storage[kk.chs] = g_storage[kk.chs]

        g_sessions.append(self.current_session)

    def handle(self):
        global g_storage
        global g_sessions

        cur_thread = threading.current_thread()

        while self.request.fileno() != -1:
            try:
                msg = common.recv_message(
                    self.request, self.current_session.symkey)
                # print(f'[{cur_thread.name}]Message received:{msg}')
                self.handle_message(msg)
            except (socket.error, common.ClientDisconnected) as e:
                print(f"{self.client_address} disconnected")
                self.request.close()
                g_sessions.remove(self.current_session)
                break

    def handle_message(self, msg):
        global g_storage
        global g_sessions

        t = msg[kk.typ]
        print(f'[<--] {t}')

        if t == kk.init_conn:
            user = msg[kk.user]
            self.current_session.user = user
            nonce = msg[kk.nonce]

            key = get_random_bytes(config.SECURE_CHANNEL_KEY_SIZE_BYTES)

            ekey = b64.b64encode(common.pkc_encrypt(
                key, self.current_session.get_encryption_cert(user))).decode()

            msg = {
                kk.typ: kk.init_key,
                kk.key: ekey,
            }
            msg[kk.signature] = b64.b64encode(common.create_msg_sig(
                self.current_session, msg, extra=nonce)).decode()
            self.send(msg)

            self.current_session.symkey = key

            # Check if user in any channel and Send channel to user
            for channel_key, c in g_storage[kk.chs].items():
                if user in c[kk.invites]:
                    self.send_invites(c)
                    self.send_messages(c)
            self.send_replay_finished()

            return

        if self.current_session.symkey is None:
            self.send_error('Secure Channel Not Established')
            return

        if t == kk.add_user:
            channel_id = msg[kk.chid]
            channel_key = msg[kk.chkey]
            inviter = msg[kk.inviter]
            invitee = msg[kk.invitee]

            timestamp = time.time()
            msg[kk.timestamp] = timestamp

            # Check signature
            if not common.check_msg_sig(self.current_session, msg):
                return

            # Create channelID if not already exists
            ch = None
            if not channel_id in g_storage[kk.chs]:
                if invitee != inviter:
                    self.send_error('Channel does not exist')
                    return
                ch = {
                    kk.chkey: channel_key,
                    kk.invites: {
                        invitee: {
                            kk.inviter: inviter,
                            kk.payload: msg,
                            kk.timestamp: timestamp
                        }
                    },
                    kk.messages: []
                }
                g_storage[kk.chs][channel_id] = ch
            else:
                ch = g_storage[kk.chs][channel_id]
                invites = ch[kk.invites]
                # Check if inviter is in channelID
                if not inviter in invites:
                    self.send_error(f'Inviter not in channel {channel_id}')
                    return

                # Try add invitee to channelID
                if not invitee in invites:
                    invites[invitee] = {
                        kk.inviter: inviter,
                        kk.payload: msg,
                        kk.timestamp: timestamp
                    }
                else:
                    self.send_error(
                        f'Invitee is already in channel {channel_id}')
                    return

            # Send previous invites to new member
            self.send_invites(ch, invitee)
            # Send previous messages to new member
            self.send_messages(ch, invitee)
            # Replay done
            self.send_replay_finished(invitee)
            # Broadcast original message to members of channelID
            self.send_broadcast(msg, ch)

        elif t == kk.comms:
            timestamp = time.time()
            msg[kk.timestamp] = timestamp
            user = msg[kk.user]
            text = msg[kk.msg]
            channel_id = msg[kk.chid]
            channel_seq = msg[kk.chseq]
            user_seq = msg[kk.userseq]

            # Check if channel exists
            if channel_id not in g_storage[kk.chs]:
                self.send_error('Channel does not exist')
                return
            ch = g_storage[kk.chs][channel_id]

            # Check if user is in channel
            if user not in ch[kk.invites]:
                self.send_error('User not part of channel')
                return

            # Check seqnums
            if self.current_session.check_seqnum(user, user_seq, channel_id, channel_seq):
                self.send_error('Sequence number very bad.')
                return

            # Store message
            ch[kk.messages].append({
                kk.timestamp: timestamp,
                kk.sender: user,
                kk.text: text,
                kk.payload: msg
            })

            # Broadcast message to channel users
            self.send_broadcast(msg, ch)

        else:
            print('Unknown Message Type')

    """
    Sends the given message to the specified session, or the current session if unspecified. Secure channel is used if a key has been established.
    """

    def send(self, msg, session=None):
        sock = self.request if session is None else session.sock
        key = self.current_session.symkey if session is None else session.symkey
        if key is not None:
            common.send_msg(sock, msg, key)
        else:
            common.send_msg(sock, msg)

    def send_error(self, msg):
        print('[-->] error')
        self.send({kk.typ: kk.error, kk.error: msg})

    """
    Sends the invites contained in the given channel to the specified user, or the current user if unspecified. 
    """

    def send_invites(self, channel, user=None):
        sess = self.get_session(user)
        if sess is None:
            return
        user = sess.user
        print('[-->] invites to', user)
        for i in channel[kk.invites].values():
            self.send(i[kk.payload], sess)

    """
    Sends the messages contained in the given channel to the specified user, or the current user if unspecified. 
    """

    def send_messages(self, channel, user=None):
        sess = self.get_session(user)
        if sess is None:
            return
        user = sess.user
        print('[-->] messages to', user)
        for i in channel[kk.messages]:
            self.send(i[kk.payload], sess)

    """
    The send_replay_finished signals the given user (or the current user if unspecified) that the replaying of messages and invites are finished.
    """

    def send_replay_finished(self, user=None):
        sess = self.get_session(user)
        if sess is None:
            return
        user = sess.user
        print('[-->] replay finished to', user)
        self.send({kk.typ: kk.replay_finished})

    def get_session(self, user=None):
        if user is None:
            return self.current_session
        else:
            sess = [s for s in g_sessions if s.user == user]
            if len(sess) <= 0:
                return None
            return sess[0]

    def send_broadcast(self, msg, channel=None):
        for sess in g_sessions:
            if channel is None or sess.user in channel[kk.invites]:
                # print('user:', self.current_session.user)
                # print('cch:', channel)
                self.send(msg, sess)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


"""
The run function loads the storage and the server certificates. Starts a TCP server, that automatically spawns a new thread for every incoming connection. 
"""


def run(address, storage_path):
    global g_storage
    global g_sessions
    global g_storage_path
    global g_signing_key

    g_storage_path = storage_path

    HOST, PORT = address.split(':')
    PORT = int(PORT)

    with open(g_storage_path, 'rt') as f:
        g_storage = json.load(f)
    with open(config.SERVER_SIGNING_KEY_PATH, 'rb') as f:
        g_signing_key = RSA.import_key(f.read())

    server = socketserver.ThreadingTCPServer(
        (HOST, PORT), ThreadedTCPRequestHandler, bind_and_activate=False)
    server.allow_reuse_address = True
    server.server_bind()
    server.server_activate()

    with server:
        ip, port = server.server_address
        print(f'Server started {ip}:{port}')

        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        running = True
        while running:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                persist()
                running = False

        print('shut down...')
        server.shutdown()


"""
The persist function in the server.py file *actually* persists the storage object, storing all channels, messages and invites.
"""


def persist():
    with open(g_storage_path, 'wt') as f:
        json.dump(g_storage, f, indent=2)

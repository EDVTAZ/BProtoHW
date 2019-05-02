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
from messaging import common, server
from session import Session
from StringKeys import kk


g_sessions = []
g_storage = {}
g_storage_path = ''
g_signing_key = None


class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    def setup(self):
        global g_storage
        global g_sessions
        global g_signing_key
        print(f'Connection from {self.client_address}')

        self.current_session = Session(g_storage, self.client_address, self.request)
        self.current_session.signing_key = g_signing_key

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

            key = get_random_bytes( config.SECURE_CHANNEL_KEY_SIZE_BYTES)
            ekey = b64.b64encode(common.pkc_encrypt(key, self.current_session.encryption_key)).decode()

            msg = {
                kk.typ: kk.init_key,
                kk.key: ekey,
            }
            msg[kk.signature] = b64.b64encode(common.create_msg_sig(self.current_session, msg), extra=nonce)
            self.send(msg)

            self.current_session.symkey = key

            # Check if user in any channel and Send channel to user
            for ck, c in g_storage[kk.chs].items():
                if user in c[kk.invites]:
                    self.send_invites(c)
                    self.send_messages(c)
            self.send_replay_finished()

#            user_sig = b64.b64decode(
#                g_storage['certs'][user]['signing']['public'])
#            self.current_session['user_sig'] = RSA.import_key(user_sig)

            return

        if self.current_session.symkey is None:
            self.send_error('Secure Channel Not Established')
            return

        if t == kk.add_user:
            cid = msg[kk.chid]
            ck = msg[kk.chkey]
            ir = msg[kk.inviter]
            ie = msg[kk.invitee]

            timestamp = time.time()
            msg[kk.timestamp] = timestamp

            # Check signature
            if not common.check_msg_sig(self.current_session, msg):
                return

            # Create channelID if not already exists
            ch = None
            if not cid in g_storage[kk.chs]:
                if ie != ir:
                    self.send_error('Channel does not exist')
                    return
                ch = {
                    kk.chkey: ck,
                    kk.invites: {
                        ie: {
                            kk.inviter: ir,
                            kk.payload: msg,
                            kk.timestamp: timestamp
                        }
                    },
                    kk.messages: []
                }
                g_storage[kk.chs][cid] = ch
            else:
                ch = g_storage[kk.chs][cid]
                invites = ch[kk.invites]
                # Check if inviter is in channelID
                if not ir in invites:
                    self.send_error(f'Inviter not in channel {cid}')
                    return

                # Try add invitee to channelID
                if not ie in invites:
                    invites[ie] = {
                        kk.inviter: ir,
                        kk.payload: msg,
                        kk.timestamp: timestamp
                    }
                else:
                    self.send_error(f'Invitee is already in channel {cid}')
                    return

            # Broadcast original message to members of channelID
            self.send_broadcast(msg, ch)
            # Send previous invites to new member
            self.send_invites(ch, ie)
            # Send previous messages to new member
            self.send_messages(ch, ie)
            # Replay done
            self.send_replay_finished(ie)

        elif t == kk.comms:
            timestamp = time.time()
            msg[kk.timestamp] = timestamp
            user = msg[kk.user]
            text = msg[kk.msg]
            cid = msg[kk.chid]

            # Check if channel exists
            if cid not in g_storage[kk.chs]:
                self.send_error('Channel does not exist')
                return
            ch = g_storage[kk.chs][cid]

            # Check if user is in channel
            if user not in ch[kk.invites]:
                self.send_error('User not part of channel')
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

    def send_invites(self, channel, user=None):
        sess = self.get_session(user)
        if sess is None:
            return
        user = sess.user
        print('[-->] invites to', user)
        for i in channel[kk.invites].values():
            self.send(i[kk.payload], sess)

    def send_messages(self, channel, user=None):
        sess = self.get_session(user)
        if sess is None:
            return
        user = sess.user
        print('[-->] messages to', user)
        for i in channel[kk.messages]:
            self.send(i[kk.payload], sess)

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
            if channel is None or self.current_session.user in channel[kk.invites]:
                self.send(msg, sess)

    def checks_sign(self, msg, signature_b64):
        h = SHA256.new(msg)
        verifier = pss.new(self.current_session['user_sig'])
        try:
            verifier.verify(h, b64.b64decode(signature_b64))
            return True
        except (ValueError, TypeError):
            return False

    def sign(self, msg):
        h = SHA256.new(msg)
        signature = pss.new(g_signing_key).sign(h)
        return b64.b64encode(signature)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


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


def persist():
    with open(g_storage_path, 'wt') as f:
        json.dump(g_storage, f, indent=2)


if __name__ == '__main__':
    run('0.0.0.0:42069', 'ss.json')

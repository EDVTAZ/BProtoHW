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


g_sessions = []
g_storage = {}
g_storage_path = 'ss.json'
g_signing_key = None


class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    def setup(self):
        global g_storage
        global g_sessions
        print(f'Connection from {self.client_address}')

        self.current_session = {
            'socket': self.request,
            'address': self.client_address,
            'secure_channel_key': None,
            'user': None,
            'user_sig': None
        }

        g_sessions.append(self.current_session)

    def handle(self):
        global g_storage
        global g_sessions

        cur_thread = threading.current_thread()

        while self.request.fileno() != -1:
            try:
                msg = common.recv_message(
                    self.request, self.current_session['secure_channel_key'])
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

        t = msg['type']
        print(f'[<--] {t}')

        if t == 'initConn':
            user = msg['userID']
            nonce = msg['nonce']

            key = get_random_bytes(config.SECURE_CHANNEL_KEY_SIZE_BYTES)

            signature = self.sign(bytes(nonce) + key)

            msg = {
                'type': 'initKey',
                'key': b64.b64encode(key).decode('utf-8'),
                'signature': signature.decode('utf-8')
            }
            self.send(msg)

            self.current_session['secure_channel_key'] = key
            self.current_session['user'] = user

            # Check if user in any channel and Send channel to user
            for ck, c in g_storage['channels'].items():
                if user in c['invites']:
                    self.send_invites(c)
                    self.send_messages(c)
            self.send_replay_finished()

            user_sig = b64.b64decode(
                g_storage['certs'][user]['signing']['public'])
            self.current_session['user_sig'] = RSA.import_key(user_sig)

            return

        if self.current_session['secure_channel_key'] is None:
            self.send_error('Secure Channel Not Established')
            return

        if t == 'addUser':
            cid = msg['channelID']
            ck = msg['channelKey']
            ir = msg['inviter']
            ie = msg['invitee']

            timestamp = time.time()
            msg['timestamp'] = timestamp

            # Check signature
            if not self.checks_sign(bytes(ir + ie + cid + ck, 'utf-8'), msg['signature']):
                self.send_error('Signature invalid')
                return

            # Create channelID if not already exists
            ch = None
            if not cid in g_storage['channels']:
                if ie != ir:
                    self.send_error('Channel does not exist')
                    return
                ch = {
                    'channelkey': ck,
                    'invites': {
                        ie: {
                            'inviter': ir,
                            'payload': msg,
                            'timestamp': timestamp
                        }
                    },
                    'messages': []
                }
                g_storage['channels'][cid] = ch
            else:
                ch = g_storage['channels'][cid]
                invites = ch['invites']
                # Check if inviter is in channelID
                if not ir in invites:
                    self.send_error(f'Inviter not in channel {cid}')
                    return

                # Try add invitee to channelID
                if not ie in invites:
                    invites[ie] = {
                        'inviter': ir,
                        'payload': msg,
                        'timestamp': timestamp
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

        elif t == 'comms':
            timestamp = time.time()
            msg['timestamp'] = timestamp
            user = msg['userID']
            text = msg['msg']
            cid = msg['channelID']

            # Check if channel exists
            if cid not in g_storage['channels']:
                self.send_error('Channel does not exist')
                return
            ch = g_storage['channels'][cid]

            # Check if user is in channel
            if user not in ch['invites']:
                self.send_error('User not part of channel')
                return

            # Store message
            ch['messages'].append({
                "timestamp": timestamp,
                "sender": user,
                "text": text,
                "payload": msg
            })

            # Broadcast message to channel users
            self.send_broadcast(msg, ch)

        else:
            print('Unknown Message Type')

    def send(self, msg, session=None):
        sock = self.request if session is None else session['socket']
        key = self.current_session['secure_channel_key'] if session is None else session['secure_channel_key']
        if key is not None:
            common.send_msg(sock, msg, key)
        else:
            common.send_msg(sock, msg)

    def send_error(self, msg):
        print('[-->] error')
        self.send({'type': 'error', 'error': msg})

    def send_invites(self, channel, user=None):
        sess = self.get_session(user)
        if sess is None:
            return
        user = sess['user']
        print('[-->] invites to', user)
        for i in channel['invites'].values():
            self.send(i['payload'], sess)

    def send_messages(self, channel, user=None):
        sess = self.get_session(user)
        if sess is None:
            return
        user = sess['user']
        print('[-->] messages to', user)
        for i in channel['messages']:
            self.send(i['payload'], sess)

    def send_replay_finished(self, user=None):
        sess = self.get_session(user)
        if sess is None:
            return
        user = sess['user']
        print('[-->] replay finished to', user)
        self.send({'type': 'replayFinished'})

    def get_session(self, user=None):
        if user is None:
            return self.current_session
        else:
            sess = [s for s in g_sessions if s['user'] == user]
            if len(sess) <= 0:
                return None
            return sess[0]

    def send_broadcast(self, msg, channel=None):
        for sess in g_sessions:
            if channel is None or self.current_session['user'] in channel['invites']:
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

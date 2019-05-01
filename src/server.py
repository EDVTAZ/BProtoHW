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
from messaging import common, server

g_sessions = []
g_storage = {}
g_running = True


class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    def setup(self):
        global g_storage
        global g_sessions
        print(f'Connection from {self.client_address}')

        self.current_session = {
            "socket": self.request,
            "address": self.client_address,
            "secure_channel_key": b''
        }

        g_sessions.append(self.current_session)

    def handle(self):
        global g_storage
        global g_sessions

        cur_thread = threading.current_thread()

        while self.request.fileno() != -1:
            try:
                msg = common.recv_message(self.request)
                # print(f'[{cur_thread.name}]Message received:{msg}')
                self.handle_message(msg)
            except (socket.error, common.ClientDisconnected) as e:
                print(f'[{cur_thread.name}] client disconnected, removing...')
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
            self.current_session["secure_channel_key"] = key

            msg = {
                "type": "initKey",
                "key": str(b64.b64encode(key)),
                "signature": "TODO"  # TODO nonce too
            }
            self.send(msg)

            # Check if user in any channel and Send channel to user
            for ck, c in g_storage['channels'].items():
                if user in c['invites']:
                    print(f'[S] {user} is in {ck}')
                    self.send_invites(c)
                    self.send_messages(c)
            self.send_replay_finished()

            return

        if self.current_session["secure_channel_key"] == b'':
            self.send_error('Secure Channel Not Established')
            return

        if t == 'addUser':
            # msg = {"inviter": "userIDa",
            #        "invitee": "userIDb",
            #        "channelID": "channelID",
            #        "channelKey": "AAAA====",
            #        "signature": "BBBB===="
            #        }
            cid = msg['channelID']
            ck = msg['channelKey']
            ir = msg['inviter']
            ie = msg['invitee']

            timestamp = time.time()
            msg['timestamp'] = timestamp

            # Check signature TODO

            # Create channelID if not already exists
            if not cid in g_storage['channels']:
                if ie != ir:
                    self.send_error('Channel does not exist')
                    return
                g_storage['channels'][cid] = {
                    "channelkey": ck,
                    "invites": {
                        ie: {
                            "inviter": ir,
                            "payload": msg,
                            "timestamp": timestamp
                        }
                    },
                    "messages": []
                }
            else:
                # Check if inviter is in channelID
                if not ir in g_storage['channels'][cid]['invites']:
                    print(f'Inviter not in channel {cid}')
                    self.send_error(f'Inviter not in channel {cid}')
                    return

                # Try add invitee to channelID
                if not ie in g_storage['channels'][cid]['invites']:
                    g_storage['channels'][cid]['invites'][ie] = {
                        "inviter": ir,
                        "payload": msg,
                        "timestamp": timestamp
                    }
                else:
                    self.send_error(f'Invitee is already in channel {cid}')
                    return

            # Broadcast original message to members of channelID
            for sess in g_sessions:
                common.send_msg(sess['socket'], msg)

        elif t == 'comms':
            pass
        else:
            print("Unknown Message Type")

    def send_error(self, msg):
        print('[-->] error')
        self.send({"type": "error", "error": msg})

    def send(self, msg):
        common.send_msg(self.request, msg)

    def send_invites(self, channel):
        print('[-->] invites')
        for i in channel['invites'].values():
            self.send(i['payload'])

    def send_messages(self, channel):
        print('[-->] messages')
        for i in channel['messages']:
            self.send(i['payload'])

    def send_replay_finished(self):
        print('[-->] replay finished')
        self.send({'type': 'replayFinished'})


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


def client(ip, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((ip, port))
        common.send_msg(sock, {
            "type": "initConn",
            'userID': 'A',
            'nonce': 123123
        })
        common.send_msg(sock, {
            "type": "addUser",
            "inviter": "B",
            "invitee": "C",
            "channelID": "C",
            "channelKey": "macska",
            "signature": "BBBB===="
        })
        while g_running:
            print(f'[-->] {common.recv_message(sock)}')


def run(address, storage_path):
    global g_storage
    global g_sessions
    global g_storage_path
    global g_running

    signal.signal(signal.SIGINT, sigint)

    g_storage_path = storage_path

    HOST, PORT = address.split(':')
    PORT = int(PORT)

    with open(g_storage_path, 'rt') as f:
        g_storage = json.load(f)

    server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
    with server:
        ip, port = server.server_address

        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        # client(ip, port)
        while g_running:
            time.sleep(1)

        print('shut down...')
        server.shutdown()


def persist():
    with open(g_storage_path, 'wt') as f:
        json.dump(g_storage, f)


def sigint(signum=None, frame=None):
    global g_running
    persist()
    try:
        sys.exit(0)
    except SystemExit:
        os._exit(0)


if __name__ == "__main__":
    run('0.0.0.0:42069', 'ss.json')

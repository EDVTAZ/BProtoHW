import socket
from messaging import common
import base64 as b64


def client(ip='127.0.0.1', port=42069):
    key = None
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((ip, port))
        common.send_msg(sock, {
            'type': 'initConn',
            'userID': 'A',
            'nonce': 123123
        })
        msg = common.recv_message(sock)
        key = b64.b64decode(msg['key'])

        common.send_msg(sock, {
            'type': 'addUser',
            'inviter': 'A',
            'invitee': 'B',
            'channelID': 'C',
            'channelKey': 'macska',
            'signature': 'WfJYfD3jML09SqX2/BFw1GiiMQwL4WS2syBJqlY6cN4cDMXwPdhK2gmuUUmCrydE8mNePDNwEHRL3hRf7/pWnUZxhswYB9qJnSNsKoE4CUT5MnuPRP0yvbf4iQu2Q6oJ7+zYeejCYFSCWZ0dyCYu3+w/zVyHvJ5TnbxWYIEn99fCRhO5G7m0Hw3KJlutsopbF2PXJZTRhQ1LmgBudzTyiJetmKKX/QsvM65bmVjPy5L86oiCR9rdYI62KkG/sHNosDjIp3wrA4O/jb7Sh0H7kDV+Ai3xs5Y/OxciID+dppDdE4OfbGuO1kRrf1kQMGDofrBKRsPd3UF7Voi1F3FRmw=='
        }, key)
        # common.send_msg(sock, {
        #     "type": "comms",
        #     "channelID": "C",
        #     "channelSeq": 2,
        #     "userID": "A",
        #     "userSeq": 2,
        #     "msg": "macske",
        #     "signature": "----"
        # }, key)
        print('users:')
        while True:
            try:
                msg = common.recv_message(sock, key)
                # print(f'[C] {msg}')
                if (msg['type'] == 'addUser'):
                    print(msg['invitee'])
                elif (msg['type'] == 'comms'):
                    print(msg['userID'], ':', msg['msg'])
            except Exception as e:
                print(e)
                return


if __name__ == "__main__":
    client()

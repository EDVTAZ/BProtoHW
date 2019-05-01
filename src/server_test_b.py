import socket
from messaging import common
import base64 as b64


def client(ip='127.0.0.1', port=42069):
    key = None
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((ip, port))
        common.send_msg(sock, {
            'type': 'initConn',
            'userID': 'B',
            'nonce': 123123
        })
        msg = common.recv_message(sock)
        key = b64.b64decode(msg['key'])

        # common.send_msg(sock, {
        #     'type': 'addUser',
        #     'inviter': 'A',
        #     'invitee': 'A',
        #     'channelID': 'C',
        #     'channelKey': 'macska',
        #     'signature': 'sdsr/Ibtrpls36X9QDCFROuR1kYN421cT499ZzpG/DKNPVIITbNQU1znMHNcsXrO4XCLU51LgdcFecU298l6EUc1kQsHmLumK58gf0fRdMx4SXbFq1B9E/mQqwv7z+nC4mIxQ8d5pGTuD/FIm3ybDYYOefzc6somfPkdQCjEcUfN8mJFyQmAUoFPTpEgl7k8Peq4But+2z/YXpPlDIaTS2Fzgx3J3s6exWfv/ut/bDpXYYBpEhZQ/V597E1oYEvIfBKq99ETVKLjmnmbI9jjjITAEvmgD890U5hqzY4yUDgglZ2nvS+syGPv2dIVfElV+JnkaNZZu0QYFXVvUjH+4w=='
        # }, key)
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

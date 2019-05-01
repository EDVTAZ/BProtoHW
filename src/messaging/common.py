import json
from Crypto.Cipher import AES
import base64 as b64


class ClientDisconnected(Exception):
    pass

# receives exactly n bytes


def recv_all(socket, n):
    recvd = 0
    res = b''
    while recvd < n:
        got = socket.recv(n - recvd)
        if got == b'':
            raise ClientDisconnected()
        res = res + got
        recvd = len(res)
    return res


def recv_message(socket, key=None):
    msg_len = int.from_bytes(recv_all(socket, 4), byteorder='big')
    msg = recv_all(socket, msg_len)

    if (key is not None):
        msg = decrypt_sym(msg, key)
    msg = json.loads(msg.decode('utf-8'))

    return msg


def decrypt_sym(msg, key):
    msg = json.loads(msg.decode('utf-8'))
    json_k = ['nonce', 'ciphertext', 'tag']
    jv = {k: b64.b64decode(msg[k]) for k in json_k}
    cipher = AES.new(key, AES.MODE_GCM, nonce=jv['nonce'])
    msg = cipher.decrypt_and_verify(jv['ciphertext'], jv['tag'])
    return msg


def encrypt_sym(msg, key):
    msg = bytes(json.dumps(msg), 'utf-8')

    cipher = AES.new(key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(msg)
    json_k = ['nonce', 'ciphertext', 'tag']
    json_v = [b64.b64encode(x).decode('utf-8')
              for x in [cipher.nonce, ciphertext, tag]]
    msg = dict(zip(json_k, json_v))
    return msg


def pack_msg(msg):
    msg = json.dumps(msg)
    msg_len = len(msg).to_bytes(4, byteorder='big')
    return msg_len + bytes(msg, 'utf-8')


def send_msg(sock, msg, key=None):
    if (key is not None):
        msg = encrypt_sym(msg, key)

    sock.sendall(pack_msg(msg))

import json
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.Signature import pss
import base64 as b64
import copy
from StringKeys import kk


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


def verify_sig(json_payload, signature, cert):
    p = json.dumps(json_payload).encode()
    h = SHA256.new(p)
    verifier = pss.new(cert)
    try:
        verifier.verify(h, signature)
        return True
    except (ValueError, TypeError):
        return False


def check_msg_sig(session, msg, extra=None):
    payload = copy.deepcopy(msg)
    payload.pop(kk.signature, None)
    payload.pop(kk.timestamp, None)
    if extra != None:
        payload[kk.nonce] = extra.decode()
    return verify_sig(payload, b64.b64decode(msg[kk.signature]), session.get_signing_cert(select_cert(msg)))


def create_sig(json_payload, cert):
    p = json.dumps(json_payload).encode()
    h = SHA256.new(p)
    signer = pss.new(cert)
    return signer.sign(h)


def create_msg_sig(session, msg, extra=None):
    payload = copy.deepcopy(msg)
    if extra != None:
        payload[kk.nonce] = extra
    return create_sig(payload, session.signing_key)
    

def select_cert(msg):
    mt = msg[kk.typ]
    if mt == kk.add_user:
        return msg[kk.inviter]
    if mt == kk.comms:
        return msg[kk.user]
    if mt == kk.init_key:
        return kk.server_key


def pkc_encrypt(msg, key):
    cipher = PKCS1_OAEP.new(key)
    return cipher.encrypt(msg)
    

def pkc_decrypt(msg, key):
    cipher = PKCS1_OAEP.new(key)
    return cipher.decrypt(msg)

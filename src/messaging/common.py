import json


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
    return json.loads(str(recv_all(socket, msg_len), 'utf-8'))


# def recv_message(socket, key=None):
#     msg_len = int.from_bytes(recv_all(socket, 4), byteorder='big')
#     msg = recv_all(socket, msg_len)
#     # msg = print(msg) ## TODO decrypt IF key NONENONEONEONE
#     return json.loads(str(msg), 'utf-8')


def decrypt_sym(msg, key):
    # TODO actually decrypt
    return msg


def pack_msg(msg):
    msg = json.dumps(msg)
    msg_len = len(msg).to_bytes(4, byteorder='big')
    return msg_len + bytes(msg, 'utf-8')


def send_msg(sock, msg, key=None):
    sock.sendall(pack_msg(msg))


# def send_msg(sock, msg, key=None):
#    # TODO encrypt with key
#    sock.sendall(pack_msg(msg))

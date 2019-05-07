import config
import messaging.common
import json
import copy
from base64 import b64decode, b64encode
from messaging import common
from StringKeys import kk
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes


def init_connection(session):
    """
    Initializes secure channel, returns with the aggreed key.
    """
    user = session.user
    sock = session.sock
    rnd = b64encode(get_random_bytes(config.SECURE_CHANNEL_KEY_SIZE_BYTES))
    common.send_msg(sock, {
        kk.typ: kk.init_conn,
        kk.user: user,
        kk.nonce: rnd.decode()
    })
    resp = common.recv_message(sock)
    if resp[kk.typ] != kk.init_key:
        print('Big bad happen.')
        exit(1)
    if messaging.common.check_msg_sig(session, resp, extra=rnd) != True:
        print('Invalid server signature while initiating connection!')
        exit(2)
    key = messaging.common.pkc_decrypt(
        b64decode(resp[kk.key]), session.encryption_key)
    session.symkey = key


def new_channel(session, channel):
    """
    Sends message to create new channel.
    """
    session.create_chan_event.clear()
    key = b64encode(messaging.common.pkc_encrypt(get_random_bytes(
        config.SECURE_CHANNEL_KEY_SIZE_BYTES), session.encryption_key)).decode()
    msg = {
        kk.typ: kk.add_user,
        kk.inviter: session.user,
        kk.invitee: session.user,
        kk.chid: channel,
        kk.chkey: key
    }
    msg[kk.signature] = b64encode(
        messaging.common.create_msg_sig(session, msg)).decode()
    messaging.common.send_msg(session.sock, msg, key=session.symkey)


def invite_user(session, invitee):
    """
    Sends message to invite user.
    """
    session.invite_event.clear()
    key = b64encode(messaging.common.pkc_encrypt(
        session.get_channel_key(), session.get_encryption_cert(invitee))).decode()
    msg = {
        kk.typ: kk.add_user,
        kk.inviter: session.user,
        kk.invitee: invitee,
        kk.chid: session.chan,
        kk.chkey: key,
    }
    msg[kk.signature] = b64encode(
        messaging.common.create_msg_sig(session, msg)).decode()
    messaging.common.send_msg(session.sock, msg, key=session.symkey)


def send_msg(session, msg):
    """
    Send text message to channel.
    """
    useq, chseq = session.get_seqnum()
    msg = {
        kk.typ: kk.comms,
        kk.chid: session.chan,
        kk.chseq: chseq + 1,
        kk.user: session.user,
        kk.userseq: useq + 1,
        kk.msg: msg
    }
    msg = encrypt_comm(msg, session)
    msg[kk.signature] = b64encode(
        messaging.common.create_msg_sig(session, msg)).decode()
    messaging.common.send_msg(session.sock, msg, key=session.symkey)


"""
Serializes GCM header data into bytesarray.
"""


def GCM_create_header(chid, chseq, user, userseq):
    return json.dumps({
        kk.chid: chid,
        kk.chseq: chseq,
        kk.user: user,
        kk.userseq: userseq
    }).encode()


"""
Symmetrical encryption used to protect channel messages with AES-GCM.
"""


def encrypt_comm(msg, session):
    header = GCM_create_header(
        msg[kk.chid], msg[kk.chseq], msg[kk.user], msg[kk.userseq])

    cipher = AES.new(session.get_channel_key(), AES.MODE_GCM)
    cipher.update(header)
    ciphertext, tag = cipher.encrypt_and_digest(msg[kk.msg].encode())

    msg[kk.msg] = {
        kk.nonce: b64encode(cipher.nonce).decode(),
        kk.tag: b64encode(tag).decode(),
        kk.ct: b64encode(ciphertext).decode()
    }

    return msg


def decrypt_comm(ogmsg, session):
    msg = copy.deepcopy(ogmsg)
    header = GCM_create_header(
        msg[kk.chid], msg[kk.chseq], msg[kk.user], msg[kk.userseq])

    cipher = AES.new(session.get_channel_key(
        msg[kk.chid]), AES.MODE_GCM, nonce=b64decode(msg[kk.msg][kk.nonce]))
    cipher.update(header)
    plaintext = cipher.decrypt_and_verify(
        b64decode(msg[kk.msg][kk.ct]),
        b64decode(msg[kk.msg][kk.tag])
    )

    msg[kk.msg] = plaintext.decode()

    return msg

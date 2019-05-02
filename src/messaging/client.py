import config
import messaging.common
import json
import copy
from base64 import b64decode, b64encode
from messaging import common
from StringKeys import kk
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from base64 import b64decode, b64encode


def init_connection(session):
    """
    initializes secure channel, returns with the aggreed key
    """
    user = session.user
    sock = session.sock
    rnd = b64encode(get_random_bytes(config.SECURE_CHANNEL_KEY_SIZE_BYTES))
    common.send_msg(sock, {
        kk.typ: kk.init_conn,
        kk.user: user,
        kk.nonce: b64encode(rnd)
    })
    resp = json.loads( messaging.common.pkc_decrypt( b64decode(common.recv_message(sock)), session.encryption_key ) )
    if resp[kk.typ] != kk.init_key:
        print('Big bad happen.')
        exit(1)
    if messaging.common.check_msg_sig(session, resp, extra=rnd) != True:
        print('Invalid server signature while initiating connection!')
        exit(2)
    session.symkey = resp[kk.key]


def new_channel(session, channel):
    """
    create new channel called <name>
    """
    session.create_chan_event.clear()
    key = b64encode(messaging.common.pkc_encrypt(get_random_bytes(
        config.SECURE_CHANNEL_KEY_SIZE_BYTES), session.encryption_key))
    msg = {
        kk.typ: kk.add_user,
        kk.inviter: session.user,
        kk.invitee: session.user,
        kk.chid: channel,
        kk.chkey: key
    }
    msg[kk.signature] = b64encode(
        messaging.common.create_msg_sig(session, msg))
    messaging.common.send_msg(session.sock, msg, key=session.symkey)


def invite_user(session, invitee):
    """
    invite user with name to channel channel
    """
    session.invite_event.clear()
    key = b64encode(messaging.common.pkc_encrypt(
        session.get_channel_key(), session.get_encryption_cert(invitee)))
    msg = {
        kk.typ: kk.add_user,
        kk.inviter: session.user,
        kk.invitee: invitee,
        kk.chid: session.chan,
        kk.chkey: key,
    }
    msg[kk.signature] = b64encode(
        messaging.common.create_msg_sig(session, msg))
    messaging.common.send_msg(session.sock, msg, key=session.symkey)


def send_msg(session, msg):
    """
    send message to channel
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
        messaging.common.create_msg_sig(session, msg))
    messaging.common.send_msg(session.sock, msg, key=session.symkey)


def GCM_create_header(chid, chseq, user, userseq):
    return json.dumps({
        kk.chid: chid,
        kk.chseq: chseq,
        kk.user: user,
        kk.userseq: userseq
    })


def encrypt_comm(msg, session):
    header = GCM_create_header(
        msg[kk.chid], msg[kk.chseq], msg[kk.user], msg[kk.userseq])

    cipher = AES.new(session.get_channel_key(), AES.MODE_GCM)
    cipher.update(header)
    ciphertext, tag = cipher.encrypt_and_digest(msg[kk.msg].encode())

    msg[kk.msg] = {
        kk.nonce: b64encode(cipher.nonce),
        kk.tag: b64encode(tag),
        kk.ct: b64encode(ciphertext)
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

    msg[kk.msg] = plaintext.encode()

    return msg

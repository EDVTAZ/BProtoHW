from messaging import common


def init_connection(sock, user):
    """
    initializes secure channel, returns with the aggreed key
    """
    rnd = 1234  # TODO fresh random
    common.send_msg(sock, {
        "type": "initConn",
        "userID": user,
        "nonce": rnd
    })
    print(common.recv_message(sock))
    return ""


def new_channel(sock, user, channel):
    """
    create new channel called <name>
    """
    common.send_msg({
        "type": "addUser",
        "inviter": user,
        "invitee": user,
        "channelID": channel,
        "channelKey": "AAAA====",
        "signature": "BBBB===="
    })


def invite_user(sock, channel, inviter, invitee):
    """
    invite user with name to channel channel
    """
    common.send_msg({
        "type": "addUser",
        "inviter": inviter,
        "invitee": invitee,
        "channelID": channel,
        "channelKey": "AAAA====",
        "signature": "BBBB===="
    })


def send_msg(sock, channel, name, msg):
    """
    send message to channel
    """
    rnd = 1234  # TODO fresh rand
    common.send_msg({
        "type": "comms",
        "nonce": rnd,
        "channelID": channel,
        "channelSeq": 123213,
        "userID": "userIDa",
        "userSeq": 123123,
        "msg": msg,
        "signature": "BBBB====",
        "timestamp": 12341234
    })

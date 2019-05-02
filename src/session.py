import os
import sys
import socket
import threading
import frontend
import json
import messaging.client
import messaging.common
import copy
import config
from StringKeys import kk
from session import Session
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.Signature import pss
from base64 import b64decode, b64encode

class Session():
    def __init__(self, storage, saddr, socket, user=None, pw=None):
        storage[kk.chs] = dict()
        for u in storage[kk.certs]:
            storage[kk.certs][u][kk.signing][kk.public] = RSA.import_key(
                b64decode(storage[kk.certs][u][kk.signing][kk.public]))
            storage[kk.certs][u][kk.encryption][kk.public] = RSA.import_key(
                b64decode(storage[kk.certs][u][kk.encryption][kk.public]))
        self.storage = storage

        self.chan = ""
        self.saddr = saddr
        self.sock = socket
        self.user = user
        self.pw = pw
        s, e = self.decrypt_privkeys()
        self.signing_key = s
        self.encryption_key = e
        self.symkey = None
        self.create_chan_event = threading.Event()
        self.invite_event = threading.Event()
        self.replay_finished = threading.Event()

        self.create_chan_event.clear()
        self.invite_event.clear()
        self.replay_finished.clear()

    def decrypt_privkeys(self):
        if self.pw == None:
            # TODO import server keys
            return None, None
        rsk = b64decode(self.storage[kk.certs]
                        [self.user][kk.signing][kk.private])
        rek = b64decode(self.storage[kk.certs]
                        [self.user][kk.encryption][kk.private])
        return RSA.import_key(rsk, self.pw), RSA.import_key(rek, self.pw)

    def get_signing_cert(self, username):
        try:
            return self.storage[kk.certs][username][kk.signing][kk.public]
        except:
            return None

    def get_encryption_cert(self, username):
        try:
            return storage[kk.certs][username][kk.encryption][kk.public]
        except:
            return None

    def get_channel_key(self, channel=None):
        try:
            if channel == None:
                channel = self.chan
            return self.storage[kk.chs][channel][kk.chkey]
        except:
            return None

    def set_channel_key(self, channel, value):
        try:
            sefl.storage[kk.chs][channel][kk.chkey] = value
        except:
            pass

    def get_seqnum(self, user=None, channel=None):
        try:
            if user == None:
                user = self.user
            if channel == None:
                channel = self.chan
            return self.storage[kk.chs][channel][kk.invites][user][kk.seqnum], self.storage[kk.chs][channel][kk.seqnum]
        except:
            return None

    def check_seqnum(self, user, userseq, channel, channelseq):
        try:
            if userseq <= self.storage[kk.chs][channel][kk.invites][user][kk.seqnum]:
                return False
            if channelseq <= self.storage[kk.chs][channel][kk.seqnum]:
                return False

            self.storage[kk.chs][channel][kk.invites][user][kk.seqnum] = userseq
            self.storage[kk.chs][channel][kk.seqnum] = channelseq

            return True

        except:
            return False

    def get_channels(self):
        return self.storage[kk.chs].keys()

    def add_user(self, msg):
        if not messaging.common.check_msg_sig(self, msg):
            return

        stored_format = {
            kk.inviter: msg[kk.inviter],
            kk.payload: msg,
            kk.timestamp: msg[kk.timestamp],
            kk.seqnum: 1
        }

        if msg[kk.inviter] == msg[kk.invitee]:
            if msg[kk.chid] in self.storage[kk.chs]:
                return
            self.create_chan_event.set()
            self.storage[kk.chs][msg[kk.chid]] = {
                kk.seqnum: 1,
                kk.invites: {
                    msg[kk.invitee]: stored_format},
                kk.messages: []
            }
            if msg[kk.inviter] == self.user:
                self.storage[kk.chs][msg[kk.chid]][kk.chkey] = messaging.common.pkc_decrypt(
                    b64decode(msg[kk.chkey]), self.encryption_key)
        else:
            if msg[kk.invitee] in self.storage[kk.chs][msg[kk.chid]][kk.invites]:
                return
            invite_event.set()
            self.storage[kk.chs][msg[kk.chid]
                                 ][kk.invites][msg[kk.invitee]] = stored_format
            if msg[kk.invitee] == self.user:
                self.storage[kk.chs][msg[kk.chid]][kk.chkey] = messaging.common.pkc_decrypt(
                    b64decode(msg[kk.chkey]), self.encryption_key)

        if msg[kk.chid] == self.chan:
            frontend.display_invite(msg)

    def incomm(self, msg):
        try:
            pt_msg = messaging.client.decrypt_comm(msg, self)
        except:
            return

        if (not messaging.common.check_msg_sig(msg, self) or
            msg[kk.user] not in self.storage[kk.chs][msg[kk.chid]][kk.invites] or
                self.check_seqnum(msg[kk.user], msg[kk.userseq], msg[kk.chid], msg[kk.chseq])):
            return

        self.storage[kk.chid][msg[kk.chid]][kk.messages].append({
            kk.timestamp: msg[kk.timestamp],
            kk.sender: msg[kk.user],
            kk.text: pt_msg[kk.msg],
            'payload': msg
        })
        if self.chan == msg[kk.chid]:
            frontend.display_message(
                msg[kk.user], msg[kk.timestamp], pt_msg[kk.msg])

    def persist(self):
        pass
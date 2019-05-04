import sys, os, datetime
from StringKeys import kk

CACHED_MSG = ""

def main_menu(address, user, channels):
    print()
    print(f"Welcome, {user}!")
    print(f"server address: {address}")
    print("=============================================")
    print("Type the number of the channel you want to join, -1 to create new channel, -42 to exit")
    for i, channel in enumerate(channels):
        print(f"{i}: {channel}")
    cc = -10
    while cc == -10:
        try:
            cc = int(input())
            if cc not in range(len(channels)):
                raise Exception
        except:
            print("Please type the number of the channel you want to join")
    if cc == -1:
        return None
    if cc == -42:
        os._exit(0)
    return channels[cc]


def new_channel():
    print("Channel name: ", end='')
    return input()


def invite_user():
    print()
    print("Name of user to invite: ", end='')
    return [input(), print()][0]


def success():
    print("Success!")


def failure(reason):
    print(f"Operation failed, because {reason}...")


def get_user():
    print("Please enter your user: ", end='')
    n = input()
    print("Please enter your password: ", end='')
    return [n, input()]


def display_channel(name):
    print(f"Channel {name}")
    print("Send you message by typing '|', invite a friend by typing ':invite' and exit by typing ':exit'")
    print()

def display_message(sender, timestamp, msg):
    global CACHED_MSG
    print(f"\r[{datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')}] {sender} :: {msg}")
    print()
    type_message(CACHED_MSG)

def display_invite(msg):
    global CACHED_MSG
    print(f"\r* [{datetime.datetime.fromtimestamp(msg[kk.timestamp]).strftime('%Y-%m-%d %H:%M:%S')}] {msg[kk.inviter]} invited {msg[kk.invitee]} to the channel! *")
    print()
    type_message(CACHED_MSG)


def type_message(msg):
    global CACHED_MSG
    CACHED_MSG = msg
    if len(msg) > 0 and msg[0] == ':':
        print(f"\r{msg}", end=' ')
    else:
        print(f"\r> {msg}", end=' ')
    sys.stdout.flush()

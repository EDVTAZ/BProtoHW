from StringKeys import kk

def main_menu(address, channels):
    print()
    print("MAIN MENU")
    print(f"server address: {address}")
    print("=========")
    print("Type the number of the channel you want to join, or -1 to create new channel")
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
    return {'username': n, 'password': input()}


def display_channel(name):
    print(f"Channel {name}")
    print()


def display_message(sender, timestamp, msg):
    print(f"\r[{timestamp}] {sender} :: {msg}")
    print()


def display_invite(msg):
    print(f"\r* [{msg[kk.timestamp]}] {msg[kk.inviter]} invited {msg[kk.invitee]} to the channel! *")
    print()


def type_message(msg):
    print(f"\r> {msg}", end='                            ')

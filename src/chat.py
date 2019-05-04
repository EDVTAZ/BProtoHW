import argparse
import server
import client
import config

parser = argparse.ArgumentParser()
parser.add_argument('--mode', choices=['s', 'c', 'server', 'client'],
                    default='s', help="The mode the program should start in")
parser.add_argument('--address', type=str,
                    default='0.0.0.0:8989', help="Address of the server")
parser.add_argument('--storage', type=str,
                    default='storage.json', help="File that holds certs and history")
parser.add_argument('--user', type=str,
                    default=None, help="Username to log in with")
parser.add_argument('--password', type=str,
                    default=None, help="Password to log in with")
args = parser.parse_args()
MODE = args.mode

print(config.logo.text)

if MODE in ('s', 'server'):
    print('Starting server!')
    server.run(args.address, args.storage)
if MODE in ('c', 'client'):
    print('Starting in client mode!')
    client.run(args.address, args.storage, args.user, args.password)

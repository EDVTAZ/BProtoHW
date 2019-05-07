import argparse
import server
import client
import config
import gen

"""
The chat.py contains the entrz point for the application. There are three different modes. One for starting the server, one for the client and one for generationg necessarz files for normal operation. If the generate mode is chosen, the users and their respective passwords need to be specified. We used the `argparse` module.
"""

parser = argparse.ArgumentParser()
parser.add_argument('--mode', choices=['s', 'server', 'c', 'client', 'g', 'generate'],
                    default='s', help="The mode the program should start in")
parser.add_argument('--address', type=str,
                    default='0.0.0.0:8989', help="Address of the server")
parser.add_argument('--storage', type=str,
                    default='storage.json', help="File that holds certs and history")
parser.add_argument('--user', type=str,
                    default=None, help="Username to log in with")
parser.add_argument('--password', type=str,
                    default=None, help="Password to log in with")
parser.add_argument('--users', type=str,
                    default="szilard:spw,gabor:gpw,marci:mpw", help="Users and passwords to generate")
args = parser.parse_args()
MODE = args.mode

print(config.logo.text)

if MODE in ('s', 'server'):
    print('Starting server!')
    server.run(args.address, args.storage)
if MODE in ('c', 'client'):
    print('Starting in client mode!')
    client.run(args.address, args.storage, args.user, args.password)
if MODE in ('g', 'generate'):
    print(f'Generating users and certs ({args.storage})...')
    gen.gen(args.users, args.storage)
    print('Done!')

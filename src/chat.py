import argparse
import server
import client

parser = argparse.ArgumentParser()
parser.add_argument('--mode', choices=['s', 'c', 'server', 'client'],
                    default='s', help="The mode the program should start in")
parser.add_argument('--address', type=str,
                    default='0.0.0.0:8989', help="Address of the server")
parser.add_argument('--storage', type=str,
                    default='storage.json', help="File that holds certs and history")
args = parser.parse_args()
MODE = args.mode

if MODE in ('s', 'server'):
    server.run(args.address, args.storage)
if MODE in ('c', 'client'):
    client.run(args.address, args.storage)

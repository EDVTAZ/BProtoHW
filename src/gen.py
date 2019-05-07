import json
from base64 import b64decode, b64encode
from StringKeys import kk
from Crypto.PublicKey import RSA

"""
The gen.py file contains the code responsible for generating the certificates and constructing the storage file, that is used by all instances of the application, to load the respective certificates for all users. The private keys are contained protected by a passphrase, the password of the user.
"""

def gen(users, storage_path):
    key = RSA.generate(2048)
    private_key = key.export_key()
    file_out = open("private_enc.pem", "wb")
    file_out.write(private_key)

    public_key = key.publickey().export_key()
    pek = public_key
    file_out = open("public_enc.pem", "wb")
    file_out.write(public_key)

    key = RSA.generate(2048)
    private_key = key.export_key()
    file_out = open("private_sig.pem", "wb")
    file_out.write(private_key)

    public_key = key.publickey().export_key()
    psk = public_key
    file_out = open("public_sig.pem", "wb")
    file_out.write(public_key)

    users = [(i.split(':')[0], i.split(':')[1].encode())
             for i in users.split(',')]

    storage = {
        kk.certs: {
            kk.server_key: {
                kk.signing: {
                    kk.public: b64encode(psk).decode()
                },
                kk.encryption: {
                    kk.public: b64encode(pek).decode()
                }
            },
        },
        kk.chs: {}
    }

    for u, p in users:
        ek = RSA.generate(2048)
        pek = ek.publickey()
        sk = RSA.generate(2048)
        psk = sk.publickey()

        storage[kk.certs][u] = {}
        storage[kk.certs][u][kk.signing] = {}
        storage[kk.certs][u][kk.encryption] = {}
        storage[kk.certs][u][kk.signing][kk.public] = b64encode(
            psk.export_key()).decode()
        storage[kk.certs][u][kk.signing][kk.private] = b64encode(
            sk.export_key(passphrase=p)).decode()
        storage[kk.certs][u][kk.encryption][kk.public] = b64encode(
            pek.export_key()).decode()
        storage[kk.certs][u][kk.encryption][kk.private] = b64encode(
            ek.export_key(passphrase=p)).decode()

    with open(storage_path, 'w') as f:
        json.dump(storage, f)

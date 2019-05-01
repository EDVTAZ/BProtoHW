from Crypto.Signature import pss
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto import Random

import base64 as b

message = b'ABCmacska'
key = RSA.import_key(open('private_sig.pem').read())
h = SHA256.new(message)
signature = pss.new(key).sign(h)
print(b.b64encode(signature))

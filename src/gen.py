from Crypto.PublicKey import RSA

key = RSA.generate(2048)
private_key = key.export_key()
file_out = open("private_enc.pem", "wb")
file_out.write(private_key)

public_key = key.publickey().export_key()
file_out = open("public_enc.pem", "wb")
file_out.write(public_key)

key = RSA.generate(2048)
private_key = key.export_key()
file_out = open("private_sig.pem", "wb")
file_out.write(private_key)

public_key = key.publickey().export_key()
file_out = open("public_sig.pem", "wb")
file_out.write(public_key)

# auto generated by update_py.py
# encoding=utf8

import Crypto.Random
import Crypto.PublicKey.RSA
import Crypto.Cipher.PKCS1_v1_5
import base64
import sys


def gen_rsa_keys(fmt='PEM'):
    random_generator = Crypto.Random.new().read
    # rsa算法生成实例
    rsa = Crypto.PublicKey.RSA.generate(1024, random_generator)
    # master的秘钥对的生成
    private_pem = rsa.exportKey(fmt)
    public_pem = rsa.publickey().exportKey(fmt)
    return (private_pem, public_pem)


def write_pem_rsa_keys(private_pem_file, public_pem_file):
    (private_pem, public_pem) = gen_rsa_keys()
    with open(private_pem_file, 'wb') as f:
        f.write(private_pem)
    with open(public_pem_file, 'wb') as f:
        f.write(public_pem)


def encode_msg(msg, public_pem_file=None, public_pem=None):
    if public_pem is None:
        if public_pem_file is None:
            return None
        else:
            with open(public_pem_file, 'r') as f:
                public_pem = f.read()
    rsakey = Crypto.PublicKey.RSA.importKey(public_pem)
    cipher = Crypto.Cipher.PKCS1_v1_5.new(rsakey)
    if sys.version_info[0] == 3:
        msg = msg.encode(encoding="utf-8")
    cipher_text = base64.b64encode(cipher.encrypt(msg))
    if sys.version_info[0] == 3:
        cipher_text = str(cipher_text, encoding='utf-8')
    return cipher_text


def decode_msg(msg, private_pem_file=None, private_pem=None):
    if private_pem is None:
        if private_pem_file is None:
            return None
        else:
            with open(private_pem_file, 'r') as f:
                private_pem = f.read()
    rsakey = Crypto.PublicKey.RSA.importKey(private_pem)
    cipher = Crypto.Cipher.PKCS1_v1_5.new(rsakey)
    text = cipher.decrypt(base64.b64decode(msg), None)
    if isinstance(text, bytes):
        text = text.decode()
    return text


if __name__ == '__main__':
    commands = ["gen_keys", "encode", "decode"]
    import argparse
    import os
    parser = argparse.ArgumentParser(description='rsa tool', usage='''
    
    1. to encode message

        > python rsa_encrypter.py -t encode -f ${public_pem_file_path} -m "${the_message_to_encode}"

    2. to decode message

        > python rsa_encrypter.py -t decode -f ${private_pem_file_path} -m "${the_encoded_message_to_decode}"

    3. to generate new rsa keys (auto generate private.pem and public.pem in current folder)

        > python rsa_encrypter.py -t gen_keys
    
    ''')
    parser.add_argument('-t', '--command_type', help='command type includes ' + str(commands))
    parser.add_argument('-f', '--pem_file', default='public.pem', help='public/private key pem file for encode/decode')
    parser.add_argument('-m', '--message', help='the msg to encode/decode')
    args = parser.parse_args(sys.argv[1:])
    if not args.command_type in commands:
        raise "unexpected command"

    if args.command_type == 'encode':
        if args.message is None:
            print(' **** please input string to encode **** ')
        else:
            if not os.path.isfile(args.pem_file):
                print(' **** please input valid pem file to encode **** ')
            else:
                print(encode_msg(msg=args.message, public_pem_file=args.pem_file))
    elif args.command_type == 'decode':
        if args.message is None:
            print(' **** please input string to decode **** ')
        else:
            if not os.path.isfile(args.pem_file):
                print(' **** please input valid pem file to decode **** ')
            else:
                print(decode_msg(msg=args.message, private_pem_file=args.pem_file))
    elif args.command_type == 'gen_keys':
        write_pem_rsa_keys('private.pem', 'public.pem')
        print('private.pem and public.pem is updated')

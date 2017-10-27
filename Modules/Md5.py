#-*- coding: utf-8 -*-
import hashlib
from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex
def Md5_make(ID):
    m = hashlib.md5()
    m.update(ID)
    v = m.hexdigest()
    return v

class crypto():
    def __init__(self, key):
        self.key = key
        self.mode = AES.MODE_CBC
    #加密
    def encrypt(self, text):
        text = str(text)
        cryptor = AES.new(self.key, self.mode, self.key)
        x = len(text) % 16
        if x != 0:
            text = text + '.' * (16 - x)
        self.ciphertext = cryptor.encrypt(text)
        return b2a_hex(self.ciphertext)
    #解密
    def decrypt(self, text):
        cryptor = AES.new(self.key, self.mode, self.key)
        plain_text = cryptor.decrypt(a2b_hex(text))
        return plain_text.rstrip('.')
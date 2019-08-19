#-*- coding: utf-8 -*-
import hashlib
import io
from module import loging
logging = loging.Error()
def Md5_make(string):
    try:
        m = hashlib.md5()
        m.update(str(string).encode('utf-8'))
        md5value = m.hexdigest()
        return md5value
    except Exception as e:
        logging.error(e)

def Md5_file(path):
    try:
        m = hashlib.md5()
        file = io.FileIO(path, 'r')
        bytes = file.read(1024)
        while (bytes != b''):
            m.update(bytes)
            bytes = file.read(1024)
        file.close()
        md5value = m.hexdigest()
        return md5value
    except Exception as e:
        logging.error(e)
#-*- coding: utf-8 -*-
import hashlib
def Md5_make(ID):
    m = hashlib.md5()
    m.update(ID)
    v = m.hexdigest()
    return v
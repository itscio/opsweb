#-*- coding: utf-8 -*-
import platform
from Modules import loging
logging = loging.Error()
if platform.python_version().startswith('2.7.'):
    logging.error("Python %s is not supported!" %platform.python_version())

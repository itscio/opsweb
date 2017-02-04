#-*- coding: utf-8 -*-
import time
import __init__
import logging
from logging.handlers import RotatingFileHandler
app = __init__.app
log_path = app.config.get('LOG_PATH')
logging.basicConfig(level=logging.INFO,
                format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                datefmt='%a, %d %b %Y %H:%M:%S',
                filename=log_path,
                filemode='a+')
Rthandler = RotatingFileHandler('myapp.log', maxBytes=10*1024*1024,backupCount=1)
Rthandler.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
Rthandler.setFormatter(formatter)
logging.getLogger('').addHandler(Rthandler)
def write(Message,Level='INFO'):
    logging.info(str(Message))
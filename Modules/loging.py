#-*- coding: utf-8 -*-
import __init__
import logging
import logzero
from logzero import logger
app = __init__.app
log_path = app.config.get('LOG_PATH')
def Error():
    logzero.logfile(log_path)
    logzero.loglevel(logging.ERROR)
    return logger
def write(Message):
    logzero.logfile(log_path)
    logzero.loglevel(logging.INFO)
    logger.info(str(Message))
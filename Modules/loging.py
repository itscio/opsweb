#-*- coding: utf-8 -*-
import logging
import logzero
from logzero import logger
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from logging.handlers import RotatingFileHandler
app = Flask(__name__)
app.config.from_pyfile('../conf/log.conf')
log_path = app.config.get('LOG_PATH')
log_debug_path = app.config.get('LOG_DEBUG_PATH')
def Error():
    handler = logging.FileHandler(log_path, encoding='UTF-8')
    handler.setLevel(logging.ERROR)
    logging_format = logging.Formatter('%(asctime)s - %(filename)s - %(funcName)s - %(lineno)s行 - %(message)s')
    handler.setFormatter(logging_format)
    app.logger.addHandler(handler)
    rHandler = RotatingFileHandler(log_path, maxBytes=1024 * 102400, backupCount=3)
    app.logger.addHandler(rHandler)
    dHandler = RotatingFileHandler(log_debug_path, maxBytes=1024 * 102400, backupCount=3)
    app.logger.addHandler(dHandler)
    return app.logger
def write(Message,*v,**d):
    logzero.logfile(log_path)
    logzero.loglevel(logging.INFO)
    logger.info(str(Message))
    if v:
        for msg in v:
            logger.info('%s\n' %msg)
    if d:
        for k in d:
            logger.info('%s\n' %d[k])
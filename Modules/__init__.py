#-*- coding: utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
from flask import Flask
app = Flask(__name__)
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/sql.conf')
app.config.from_pyfile('../conf/log.conf')
app.config.from_pyfile('../conf/purge.conf')
app.config.from_pyfile('../conf/kafka.conf')
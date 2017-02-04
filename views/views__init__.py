#-*- coding: utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
from flask import Flask
app = Flask(__name__)
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/mail.conf')
app.config.from_pyfile('../conf/init.conf')
app.config.from_pyfile('../conf/kafka.conf')
app.config.from_pyfile('../conf/zookeeper.conf')
app.config.from_pyfile('../conf/sql.conf')
app.config.from_pyfile('../conf/mobile.conf')
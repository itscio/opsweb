# coding=utf-8
import sys
reload(sys)
from flask import Flask
sys.setdefaultencoding('utf8')
app = Flask(__name__)
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/mail.conf')
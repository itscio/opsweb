#-*- coding: utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf8')
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_ipaddr
app = Flask(__name__)
limiter = Limiter(app,key_func=get_ipaddr,global_limits=["30/minute"])
app.config.from_pyfile('../conf/haproxy.conf')
app.config.from_pyfile('../conf/redis.conf')
#-*- coding: utf-8 -*-
import sys
from imp import reload
reload(sys)
sys.setdefaultencoding('utf8')
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_ipaddr
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)
DB = SQLAlchemy(app)
limiter = Limiter(app,key_func=get_ipaddr,global_limits=["30/minute"])
app.config.from_pyfile('../conf/main.conf')
app.config.from_pyfile('../conf/haproxy.conf')
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/security.conf')
app.config.from_pyfile('../conf/sql.conf')
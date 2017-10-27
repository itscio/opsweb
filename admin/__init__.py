# coding=utf-8
import sys
from imp import reload
reload(sys)
sys.setdefaultencoding('utf8')
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/main.conf')
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/mail.conf')
app.config.from_pyfile('../conf/security.conf')
app.config.from_pyfile('../conf/sql.conf')
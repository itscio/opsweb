#-*- coding: utf-8 -*-
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
app.config.from_pyfile('../conf/sql.conf')
app.config.from_pyfile('../conf/log.conf')
app.config.from_pyfile('../conf/purge.conf')
app.config.from_pyfile('../conf/kafka.conf')
app.config.from_pyfile('../conf/svn.conf')
app.config.from_pyfile('../conf/git.conf')
app.config.from_pyfile('../conf/twemproxy.conf')
app.config.from_pyfile('../conf/security.conf')
app.config.from_pyfile('../conf/acl.conf')
app.config.from_pyfile('../conf/task.conf')
app.config.from_pyfile('../conf/init.conf')
app.config.from_pyfile('../conf/zabbix.conf')
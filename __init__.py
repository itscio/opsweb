#-*- coding: utf-8 -*-
import sys
from imp import reload
reload(sys)
sys.setdefaultencoding('utf8')
import os
from flask_sqlalchemy import SQLAlchemy
from flask import Flask,Blueprint
from api import haproxy_conf,haproxy_blacklist
from views import sql_app,php_list,publish_java,publish_php,pw,update_php,vpn_admin
from views import cdn,java_list,clear_redis,svn_admin,chart_center
from views import kafka_info,zookeeper_info,slow_redis ,mysql_parse,deploy
from views import sql_scheduler,git_admin,sql_kill,sql_run,update_java
from views import clean_project,sql_query,dns_conf,scheduler_list,sql_create
from views import publish_apply,init_system,mongodb_info,message
from admin import examine,op_user
from flask_limiter import Limiter
from flask_limiter.util import get_ipaddr
import chartkick
from Modules import produce
from flask_debugtoolbar import DebugToolbarExtension
app = Flask(__name__)
DB = SQLAlchemy(app)
app.secret_key = os.urandom(24)
app.debug = False
toolbar = DebugToolbarExtension(app)
limiter = Limiter(app,key_func=get_ipaddr,global_limits=["1000/minute"])
app.config.from_pyfile('conf/main.conf')
app.config.from_pyfile('conf/redis.conf')
app.config.from_pyfile('conf/sql.conf')
app.config.from_pyfile('conf/log.conf')
app.config.from_pyfile('conf/purge.conf')
app.config.from_pyfile('conf/kafka.conf')
app.config.from_pyfile('conf/svn.conf')
app.config.from_pyfile('conf/git.conf')
app.config.from_pyfile('conf/twemproxy.conf')
app.config.from_pyfile('conf/security.conf')
app.config.from_pyfile('conf/acl.conf')
page_ck = Blueprint('ck_page', __name__, static_folder=chartkick.js(),static_url_path='/static')
app.register_blueprint(page_ck, url_prefix='/ck')
app.jinja_env.add_extension("chartkick.ext.charts")
app.register_blueprint(sql_app.page_mysql)
app.register_blueprint(sql_app.page_mysql_op)
app.register_blueprint(pw.page_pw)
app.register_blueprint(cdn.page_cdn)
app.register_blueprint(publish_php.page_publish_php)
app.register_blueprint(php_list.page_php_list)
app.register_blueprint(java_list.page_java_list)
app.register_blueprint(update_php.page_update_php)
app.register_blueprint(publish_java.page_publish_java)
app.register_blueprint(haproxy_conf.page_haproxy_conf)
app.register_blueprint(clear_redis.page_clear_redis)
app.register_blueprint(chart_center.page_chart_center)
app.register_blueprint(vpn_admin.page_vpn_admin)
app.register_blueprint(svn_admin.page_svn_admin)
app.register_blueprint(kafka_info.page_kafka_info)
app.register_blueprint(zookeeper_info.page_zk_info)
app.register_blueprint(slow_redis.page_slow_redis)
app.register_blueprint(mysql_parse.page_mysql_parse)
app.register_blueprint(sql_scheduler.page_sql_scheduler)
app.register_blueprint(git_admin.page_git_admin)
app.register_blueprint(examine.page_examine)
app.register_blueprint(sql_kill.page_sql_kill)
app.register_blueprint(sql_run.page_sql_run)
app.register_blueprint(update_java.page_update_java)
app.register_blueprint(op_user.page_op_user)
app.register_blueprint(deploy.page_deploy)
app.register_blueprint(deploy.page_haproxy_reload)
app.register_blueprint(clean_project.page_Clean_project)
app.register_blueprint(sql_query.page_sql_query)
app.register_blueprint(dns_conf.page_dns_conf)
app.register_blueprint(scheduler_list.page_scheduler_list)
app.register_blueprint(haproxy_blacklist.page_haproxy_blacklist)
app.register_blueprint(sql_create.page_sql_create)
app.register_blueprint(publish_apply.page_publish_apply)
app.register_blueprint(init_system.page_init_system)
app.register_blueprint(mongodb_info.page_mongodb_info)
app.register_blueprint(message.page_message)
produce.scheduler_tasks()
Sch = produce.Scheduler_backgroud()
Sch.Run()
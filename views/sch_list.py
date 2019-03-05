#-*- coding: utf-8 -*-
from flask import Blueprint,render_template,request,g
from Modules import produce,check,db_op,loging
import time
import redis
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/sql.conf')
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
DB = SQLAlchemy(app)
RC = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
page_sch_list=Blueprint('scheduler_list',__name__)
@page_sch_list.route('/scheduler_list')
def scheduler_list():
    tables = ('定时任务','下次执行时间')
    db = db_op.apscheduler_jobs
    values = db.query.with_entities(db.id, db.next_run_time).all()
    values = [{'time':time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(val[1])),'task':str(val[0])} for val in values]
    return render_template('scheduler_list.html',tables=tables,values=sorted(values,key=lambda x:x['time']))
@page_sch_list.before_request
@check.login_required(grade=1)
def check_login(exception = None):
    produce.Async_log(g.user, request.url)

@page_sch_list.teardown_request
def db_remove(exception):
    db_op.DB.session.remove()
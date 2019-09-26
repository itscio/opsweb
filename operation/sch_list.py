#-*- coding: utf-8 -*-
from flask import Flask,Blueprint,render_template,request,g
from module import tools,user_auth,db_idc,loging
import time
import redis
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/redis.conf')
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
RC = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
page_sch_list=Blueprint('scheduler_list',__name__)
@page_sch_list.route('/scheduler_list')
def scheduler_list():
    db_jobs = db_idc.apscheduler_jobs
    values = db_jobs.query.with_entities(db_jobs.id, db_jobs.next_run_time).all()
    values = [{'time':time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(val[1])),'task':str(val[0])} for val in values]
    return render_template('scheduler_list.html',values=sorted(values,key=lambda x:x['time']))

@page_sch_list.before_request
@user_auth.login_required(grade=1)
def check_login(exception = None):
    tools.Async_log(g.user, request.url)

@page_sch_list.teardown_request
def db_remove(exception):
    db_idc.DB.session.remove()
#-*- coding: utf-8 -*-
from flask import Blueprint,render_template,g,request
from Modules import produce,check,MyForm,db_op
import redis
import __init__
app = __init__.app
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
Redis = redis.StrictRedis(host=redis_host, port=redis_port)
page_Scheduler=Blueprint('Scheduler',__name__)
@page_Scheduler.route('/Scheduler',methods = ['GET', 'POST'])
def Scheduler():
    form = MyForm.MyForm_Scheduler()
    cron = form.cron.data
    host = '127.0.0.1'
    if form.host.data:
        host = form.host.data
    user = form.user.data
    job = form.job.data
    return render_template('Scheduler.html',form=form)
@page_Scheduler.before_request
@check.login_required(grade=0)
def check_login(error=None):
    produce.Async_log(g.user, request.url)

@page_Scheduler.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
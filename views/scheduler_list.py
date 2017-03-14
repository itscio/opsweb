#-*- coding: utf-8 -*-
from flask import Blueprint,render_template,request,g
from Modules import produce,check,db_op,loging
import time
page_scheduler_list=Blueprint('scheduler_list',__name__)
@page_scheduler_list.route('/scheduler_list')
def scheduler_list():
    tables = ('定时任务','下次执行时间')
    db = db_op.apscheduler_jobs
    values = db.query.with_entities(db.id, db.next_run_time).all()
    values = [[val[0],time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(val[1]))] for val in values]
    return render_template('scheduler_list.html',tables=tables,values=values)

@page_scheduler_list.before_request
@check.login_required(grade=0)
def check_login(error=None):
    produce.Async_log(g.user, request.url)

@page_scheduler_list.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
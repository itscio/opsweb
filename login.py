#-*- coding: utf-8 -*-
from flask import Blueprint,redirect,url_for,render_template,make_response,flash,request
from sqlalchemy import and_
from Modules import db_op,MyForm, Md5, check ,produce,loging
import string
import redis
import time
import __init__
app = __init__.app
limiter = __init__.limiter
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
Redis = redis.StrictRedis(host=redis_host, port=redis_port)
page_login = Blueprint('login', __name__)
@page_login.route('/login',methods = ['GET', 'POST'])
@limiter.limit("60/minute")
def login():
    form = MyForm.MyForm_login()
    form.name.label = '用户名:'
    form.password.label = '密码:'
    ym = time.strftime('%Y',time.localtime())
    if form.submit.data:
        if  form.name.data and  form.password.data:
            user = form.name.data
            pw = form.password.data
            try:
                Key_Incr = '%s_Incr' % user
                Key_Lock = 'Lock_login_%s' %user
                if Redis.exists(Key_Incr):
                    Incr = int(Redis.get(Key_Incr))
                else:
                    Incr = 1
                if Redis.exists(Key_Lock):
                    raise flash('该帐号异常登陆,已被锁定1分钟!')
                va_p = db_op.idc_users.query.filter(and_(db_op.idc_users.name == user, db_op.idc_users.passwd == Md5.Md5_make(pw))).first()
                produce.Async_log(user, request.url)
                if va_p:
                    URL = url_for('index.index')
                    if pw == app.config.get('INIT_OP_PASSWORD'):
                        URL = url_for('pw.pw')
                        flash('请修改初始密码!')
                    timestamp = None
                    if form.remember_me.data:
                        timestamp = check.timestamp(7)
                    ID = produce.Produce(length=24,chars=string.hexdigits)
                    app_resp = make_response( redirect(URL))
                    app_resp.set_cookie('user',user,expires=timestamp)
                    app_resp.set_cookie('ID',ID,expires=timestamp)
                    Redis.set('OP_ID_%s'%user,ID)
                    return app_resp
                else:
                    Redis.set(Key_Incr,Incr+1)
                    if Incr >= 11:
                        Redis.incr(Key_Lock,'True')
                        Redis.expire(Key_Lock,60)
                    flash('用户名或者密码错误,还有%s次机会重试!'%(10-int(Incr)))
                    URL = url_for('login.login')
                    app_resp = make_response(redirect(URL))
                    app_resp.set_cookie('user', user)
                    return app_resp
            except Exception as e:
                if 'old' not in str(e):
                    flash(str(e))
    return render_template('login.html',form=form,ym=ym)
@page_login.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()


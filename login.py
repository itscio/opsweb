#-*- coding: utf-8 -*-
from flask import Blueprint,redirect,url_for,render_template,make_response,flash,request,session
from sqlalchemy import and_
from Modules import db_op,MyForm, Md5, check ,produce
import string
import redis
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
    user = request.cookies.get('user')
    if user:
        Incr = Redis.incr('%s_Incr' %user)
    else:
        Incr = 0
    if form.submit.data:
        if  form.name.data and  form.password.data:
            user = form.name.data
            pw = form.password.data
            Key_Incr = '%s_Incr' %user
            Key_Lock = '%s_lock' %user
            try:
                if Incr >= 30:
                    raise flash('该帐号异常登陆,已被锁定3分钟!')
                if Incr >= 5:
                    if form.code.data:
                        if str(form.code.data) != str(session['verify_code']):
                            raise flash('输入验证码错误!')
                    else:
                        raise flash('请输入验证码,看不清点击验证码刷新!')
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
                    Redis.delete(Key_Lock)
                    Redis.delete(Key_Incr)
                    return app_resp
                else:
                    Redis.incr(Key_Incr)
                    if Incr >= 30:
                        Redis.set(Key_Lock,'True')
                        Redis.expire(Key_Incr,60)
                        Redis.expire(Key_Lock,180)
                    flash('用户名或者密码错误!')
                    URL = url_for('login.login')
                    app_resp = make_response(redirect(URL))
                    app_resp.set_cookie('user', user)
                    return app_resp
            except Exception as e:
                if 'old' not in str(e):
                    flash(str(e))
    return render_template('login.html',form=form,verify_incr = Incr)
@page_login.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()


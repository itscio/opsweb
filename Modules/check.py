#-*- coding: utf-8 -*-
from flask import request,g ,session,render_template_string,redirect,url_for
import datetime,time
import db_op
import redis
from functools import wraps
import loging
import __init__
app = __init__.app
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
Redis = redis.StrictRedis(host=redis_host, port=redis_port)
def timestamp(i):
    '''
    i is 0 days ago
    '''
    if i>=1:
        t = (datetime.datetime.now() + datetime.timedelta(days=1))
    else:
        t = (datetime.datetime.now() - datetime.timedelta(days=1))
    tp = int(time.mktime(t.timetuple()))
    return tp
def login_required(grade = 0,page=None):
    def login_check(func):
        @wraps(func)
        def Login(*args, **kwargs):
            user = request.cookies.get('user')
            ID = request.cookies.get('ID')
            try:
                if user and ID:
                    if Redis.get('%s_lock' %user):
                        return render_template_string('该帐号异常登陆,已被锁定3分钟!')
                    if request.cookies.get('ID') == Redis.get('OP_ID_%s' % user):
                        g.user = user
                        g.secret_key = request.cookies.get('secret_key')
                        db = db_op.idc_users
                        val = db.query.with_entities(db.grade).filter(db.name == user).all()
                        g.grade = int(val[0][0]) if val else 10
                        if g.grade > grade:
                            return render_template_string('无权限访问该页面!')
                        return func(*args, **kwargs)
                    else:
                        for info in ('user', 'ID', 'session'):
                            session[info] = ''
                        if page:
                            return redirect(url_for('login.login'))
                        return render_template_string('该帐号已在其他地方登陆,请确认账号安全!')
                else:
                    if page:
                        return redirect(url_for('login.login'))
                    return render_template_string('认证已过期,请重新登陆!')
            except Exception as e:
                return render_template_string(str(e))
            finally:
                db_op.DB.session.remove()
        return Login
    return login_check

def acl_ip(func):
    @wraps(func)
    def check_ip(*args, **kwargs):
        try:
            if request.headers['X-Forwarded-For']:
                ip = request.headers['X-Forwarded-For']
        except:
            ip = request.remote_addr
        if '172.16.' not in ip:
            loging.write(ip)
            return render_template_string('非法IP地址访问!')
        return func(*args, **kwargs)
    return check_ip





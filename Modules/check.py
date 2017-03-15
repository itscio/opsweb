#-*- coding: utf-8 -*-
from flask import request,g ,session,render_template_string,redirect,url_for
import datetime,time
import db_op
import redis
from functools import wraps
import loging
from rediscluster import RedisCluster
import socket
from random import choice
import __init__
app = __init__.app
PID = choice([i for i in xrange(655350)])
HOST = socket.gethostbyname(socket.gethostname())
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
Redis = redis.StrictRedis(host=redis_host, port=redis_port)
nodes = app.config.get('NODES_PRODUCE')
RC = RedisCluster(startup_nodes=nodes, decode_responses=True)
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
#登陆检查
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
#访问ip限制
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
#分布式全局锁
def scheduler_lock():
    try:
        if RC.exists('host_lock'):
            if HOST == RC.get('host_lock') and PID == int(RC.get('pid_lock')):
                RC.expire('host_lock',30)
                RC.expire('pid_lock', 30)
                loging.write('lock_info:host>>%s  pid>>%s unlock......' % (HOST,PID))
            else:
                raise AssertionError
        else:
            RC.set('host_lock',HOST)
            RC.set('pid_lock',PID)
            RC.expire('host_lock',30)
            RC.expire('pid_lock', 30)
    except:
        pass
#进程排它锁
def proce_lock(func):
    @wraps(func)
    def LOCK(*args, **kwargs):
        try:
            if RC.exists('host_lock'):
                if HOST == RC.get('host_lock') and PID == int(RC.get('pid_lock')):
                    loging.write('host:%s  pid:%s   task:%s run......' % (HOST,PID, func.__name__))
                    return func(*args, **kwargs)
                else:
                    loging.write('host:%s  pid:%s   task:%s sleep......' % (HOST, PID, func.__name__))
                    return None
            return None
        except Exception as e:
            loging.write(e)
    return LOCK





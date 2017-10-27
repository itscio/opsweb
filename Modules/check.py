#-*- coding: utf-8 -*-
from flask import request,g ,session,render_template_string,redirect,url_for,flash
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
logging = loging.Error()
PID = choice([i for i in range(65535)])
HOST = socket.gethostbyname(socket.gethostname())
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
Redis = redis.StrictRedis(host=redis_host, port=redis_port)
nodes = app.config.get('NODES_PRODUCE')
RC = RedisCluster(startup_nodes=nodes, decode_responses=True)
white_list = app.config.get('WHITE_LIST')
task_servers = app.config.get('TASK_SERVERS')
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
def login_required(grade = 0):
    def login_check(func):
        @wraps(func)
        def Login(*args, **kwargs):
            user = request.cookies.get('user')
            ID = request.cookies.get('ID')
            Error_Key = '%s:%s' %(user,ID)
            try:
                if user and ID:
                    if Redis.get('%s_lock' %user):
                        Redis.set(Error_Key,'该帐号异常登陆,已被锁定1分钟!')
                        return redirect(url_for('message.message'))
                    if request.cookies.get('ID') == Redis.get('OP_ID_%s' % user):
                        g.user = user
                        g.secret_key = request.cookies.get('secret_key')
                        db = db_op.idc_users
                        val = db.query.with_entities(db.grade).filter(db.name == user).all()
                        g.grade = int(val[0][0]) if val else 10
                        if g.grade > grade:
                            Redis.set(Error_Key,'无权限访问该页面!')
                            return redirect(url_for('message.message'))
                        return func(*args, **kwargs)
                    else:
                        for info in ('user', 'ID', 'session'):
                            session[info] = ''
                        Redis.set(Error_Key,'该帐号已在其他地方登陆,请确认账号安全!')
                        return redirect(url_for('message.message'))
                else:
                    Redis.set(Error_Key,'认证已过期,请重新登陆!')
                    return redirect(url_for('message.message'))
            except Exception as e:
                Redis.set(Error_Key,str(e))
                return redirect(url_for('message.message'))
            finally:
                db_op.DB.session.remove()
        return Login
    return login_check
#访问ip限制
def acl_ip(func):
    @wraps(func)
    def check_ip(*args, **kwargs):
        ip_check = []
        try:
            if request.headers['X-Forwarded-For']:
                src_ip = request.headers['X-Forwarded-For']
            else:
                src_ip = request.remote_addr
        except:
            src_ip = request.remote_addr
        if ',' in src_ip:
            src_ip = src_ip.split(',')[0]
        for ip in white_list:
            if '/' in ip:
                mask = ip.split('/')[1]
                if mask == '32':
                    ip = ip.split('.')
                if mask == '24':
                    ip = ip.split('.')[:3]
                if mask == '16':
                    ip = ip.split('.')[:2]
                if mask == '8':
                    ip = ip.split('.')[:1]
                if src_ip.startswith('.'.join(ip)):
                    ip_check.append(True)
            else:
                if ip == src_ip:
                    ip_check.append(True)
        if not ip_check:
            return render_template_string('%s 该IP地址未被授权访问!' % src_ip)
        return func(*args, **kwargs)
    return check_ip
#分布式全局锁
def scheduler_lock():
    try:
        if HOST in task_servers:
            if RC.exists('host_lock') and RC.get('pid_lock'):
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
        else:
            raise AssertionError
    except:
        pass
#进程排它锁
def proce_lock(func):
    @wraps(func)
    def LOCK(*args, **kwargs):
        try:
            if RC.exists('host_lock') and RC.get('pid_lock'):
                if HOST == RC.get('host_lock') and PID == int(RC.get('pid_lock')):
                    loging.write('host:%s  pid:%s   task:%s run......' % (HOST,PID, func.__name__))
                    return func(*args, **kwargs)
                else:
                    return None
            return None
        except Exception as e:
            if e:
                logging.error(str(e))
    return LOCK
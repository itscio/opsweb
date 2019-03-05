#-*- coding: utf-8 -*-
from flask import Flask,request,g,render_template_string,redirect,url_for,flash,session
import datetime
import time
from  Modules import db_op,loging,db_idc
import redis
from functools import wraps
import socket
from random import choice
from sqlalchemy import and_,distinct
from collections import defaultdict
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/security.conf')
app.config.from_pyfile('../conf/task.conf')
app.config.from_pyfile('../conf/main.conf')
logging = loging.Error()
DB = SQLAlchemy(app)
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
RC= Redis = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
redis_data = app.config.get('REDIS_DATA')
RC_CLUSTER = redis.StrictRedis(host=redis_data, port=redis_port,decode_responses=True)
white_list = app.config.get('WHITE_LIST')
task_servers = app.config.get('TASK_SERVERS')
HOST = socket.gethostbyname(socket.gethostname())
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
#用户登录鉴权
def login_required(grade = None):
    def login_check(func):
        @wraps(func)
        def Login(*args, **kwargs):
            db_auth = db_op.user_auth
            try:
                user = Redis.get('OP_user_%s' %request.cookies.get('user'))
                openid = Redis.get('OP_openid_%s' %request.cookies.get('openid'))
                dingId = Redis.get('OP_dingId_%s' %request.cookies.get('dingId'))
                token = Redis.get('OP_token_%s' %request.cookies.get('token'))
                Error_Key = 'error_%s' % (token)
            except:
                return redirect(url_for('logout.logout'))
            else:
                try:
                    if user and token and dingId and openid:
                        if token == Redis.get('OP_verify_%s' %dingId):
                            g.user = user
                            g.openid = openid
                            g.dingId = dingId
                            g.secret_key = request.cookies.get('secret_key')
                            g.token = token
                            val = db_auth.query.with_entities(db_auth.grade).filter(and_(db_auth.dingId == dingId,db_auth.token == token,db_auth.openid == openid)).all()
                            g.grade = val[0][0].split(',') if val else ('11',)
                            if str(grade) in g.grade:
                                grades = g.grade
                                g.ip = request.headers.get('X-Forwarded-For')
                                if not g.ip:
                                    g.ip = request.remote_addr
                                if ',' in g.ip:
                                    g.ip = g.ip.split(',')[0]
                                session['remote_ip'] = g.ip
                                Redis.sadd('active_users', dingId)
                                Redis.expire('active_users', 30)
                                g.active_users = Redis.scard('active_users')
                                g.date = time.strftime('%Y-%m-%d', time.localtime())
                                g.ym = time.strftime('%Y', time.localtime())
                                g.weather = RC_CLUSTER.hgetall('weather_inofs')
                                #新发现物理服务器
                                try:
                                    db_server = db_idc.idc_servers
                                    discovery = db_server.query.with_entities(db_server.ip, db_server.ssh_port).filter(
                                        db_server.status == '新发现').all()
                                    if discovery:
                                        tables = ['机房', 'IP', 'ssh_poort']
                                        discovery = [list(info) for info in discovery]
                                        for infos in discovery:
                                            infos.insert(0, '未知')
                                        discovery.insert(0, tables)
                                    g.discovery = discovery
                                except Exception as e:
                                    logging.error(e)
                                # 生成用户权限对应的页面菜单
                                try:
                                    for key in ('navMenu', 'nav_val','submenu', 'sub_val'):
                                        if g.Base_Menu[key]:
                                            pass
                                except:
                                    DB = db_op.op_menu
                                    nav_val = defaultdict()
                                    sub_val = defaultdict()
                                    navMenu = DB.query.with_entities(distinct(DB.Menu_name)).filter(and_(DB.Menu == 'navMenu', DB.grade.in_(grades))).order_by(DB.Menu_id).all()
                                    navMenu = [Menu[0] for Menu in navMenu]
                                    for Menu in navMenu:
                                        val = DB.query.with_entities(DB.id_name, DB.module_name,DB.action_name).filter(and_(DB.grade.in_(grades),DB.Menu_name==Menu)).order_by(DB.sub_id).all()
                                        if val:
                                            nav_val[Menu] = val
                                    submenu = DB.query.with_entities(distinct(DB.Menu_name)).filter(and_(DB.Menu == 'submenu', DB.grade.in_(grades))).order_by(DB.Menu_id).all()
                                    submenu = [menu[0] for menu in submenu]
                                    for Menu in submenu:
                                        val = DB.query.with_entities(DB.module_name, DB.action_name).filter(and_(DB.grade.in_(grades), DB.Menu_name == Menu)).order_by(DB.sub_id).all()
                                        if val:
                                            sub_val[Menu] = val
                                    g.Base_Menu = {'navMenu': navMenu, 'nav_val': nav_val,'submenu': submenu, 'sub_val': sub_val}
                                return func(*args, **kwargs)
                            else:
                                flash('未授权访问该页面!')
                                return redirect(url_for('login.login'))
                        else:
                            flash('该帐号已在其他地方登陆,请确认账号安全!')
                            return redirect(url_for('login.login'))
                    else:
                        return redirect(url_for('login.login'))
                except Exception as e:
                    Redis.set(Error_Key,str(e))
                    return redirect(url_for('error.error'))
            finally:
                db_op.DB.session.remove()
                db_idc.DB.session.remove()
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
#任务执行锁
def proce_lock(func):
    @wraps(func)
    def LOCK(*args, **kwargs):
        try:
            if HOST in task_servers:
                time.sleep(choice([i for i in range(1,10)]))
                if RC.exists('task_%s'%func.__name__):
                    raise AssertionError
                RC.set('task_%s' %func.__name__, HOST)
                RC.expire('task_%s' % func.__name__,15)
                return func(*args, **kwargs)
            else:
                raise AssertionError
        except:
            pass
    return LOCK
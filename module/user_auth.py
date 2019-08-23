#-*- coding: utf-8 -*-
from flask import Flask,request,g,redirect,url_for,session
import time
from  module import db_op,loging
import redis
from functools import wraps
from sso_cas import CASClient
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_,distinct
from collections import defaultdict
app = Flask(__name__)
logging = loging.Error()
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/cas.conf')
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
Redis = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
redis_data = app.config.get('REDIS_DATA')
RC_CLUSTER = redis.StrictRedis(host=redis_data, port=redis_port,decode_responses=True)
cas_url = app.config.get('CAS_URL')
#用户登录鉴权
def login_required(grade = None):
    def login_check(func):
        @wraps(func)
        def Login(*args, **kwargs):
            try:
                user = Redis.get('OP_user_%s' %request.cookies.get('user'))
                dingId = Redis.get('OP_dingId_%s' %request.cookies.get('dingId'))
                token = request.cookies.get('token')
                ticket = Redis.get('OP_ticket_%s' % request.cookies.get('ticket'))
            except:
                pass
            else:
                try:
                    if user and dingId and token and ticket:
                        if Redis.exists('OP_logout_ticket_%s' % ticket):
                            if token == Redis.get('OP_token_%s' %dingId):
                                g.user = user
                                g.dingId = dingId
                                g.secret_key = request.cookies.get('secret_key')
                                g.token = token
                                db_sso = db_op.user_sso
                                val = db_sso.query.with_entities(db_sso.grade,db_sso.mail,db_sso.mobilePhone,db_sso.department).filter(db_sso.dingunionid == dingId).all()
                                if val:
                                    g.grade,g.mail,g.phone,g.department = val[0]
                                    g.grade = g.grade.split(',')
                                    if str(grade) in g.grade:
                                        g.ip = request.headers.get('X-Forwarded-For')
                                        if not g.ip:
                                            g.ip = request.remote_addr
                                        if ',' in g.ip:
                                            g.ip = g.ip.split(',')[0]
                                        session['remote_ip'] = g.ip
                                        tm = time.strftime('%Y%m%d', time.localtime())
                                        Redis.sadd('op_active_users_%s' %tm, dingId)
                                        g.active_users = Redis.scard('op_active_users_%s' %tm)
                                        g.date = time.strftime('%Y-%m-%d', time.localtime())
                                        g.ym = time.strftime('%Y', time.localtime())
                                        # 生成用户权限对应的页面菜单
                                        try:
                                            for key in ('navMenu', 'nav_val', 'submenu', 'sub_val'):
                                                if g.Base_Menu[key]:
                                                    pass
                                        except:
                                            grades = g.grade
                                            DB = db_op.op_menu
                                            nav_val = defaultdict()
                                            sub_val = defaultdict()
                                            navMenu = DB.query.with_entities(distinct(DB.Menu_name)).filter(
                                                and_(DB.Menu == 'navMenu', DB.grade.in_(grades))).order_by(
                                                DB.Menu_id).all()
                                            if navMenu:
                                                navMenu = [Menu[0] for Menu in navMenu]
                                                for Menu in navMenu:
                                                    val = DB.query.with_entities(DB.id_name, DB.module_name,
                                                                                 DB.action_name).filter(
                                                        and_(DB.grade.in_(grades), DB.Menu_name == Menu)).order_by(
                                                        DB.sub_id).all()
                                                    if val:
                                                        nav_val[Menu] = val
                                            submenu = DB.query.with_entities(distinct(DB.Menu_name)).filter(
                                                and_(DB.Menu == 'submenu', DB.grade.in_(grades))).order_by(
                                                DB.Menu_id).all()
                                            if submenu:
                                                submenu = [menu[0] for menu in submenu]
                                                for Menu in submenu:
                                                    val = DB.query.with_entities(DB.module_name, DB.action_name).filter(
                                                        and_(DB.grade.in_(grades), DB.Menu_name == Menu)).order_by(
                                                        DB.sub_id).all()
                                                    if val:
                                                        sub_val[Menu] = val
                                            g.Base_Menu = {'navMenu': navMenu, 'nav_val': nav_val, 'submenu': submenu,
                                                           'sub_val': sub_val}
                                        return func(*args, **kwargs)
                except Exception as e:
                    logging.error(e)
                    return redirect(url_for('error'))
            finally:
                db_op.DB.session.remove()
            return redirect(url_for('logout.logout'))
        return Login
    return login_check

#用户单点注销
def cas_logout():
    cas_client = CASClient(cas_url)
    return cas_client
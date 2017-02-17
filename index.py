#-*- coding: utf-8 -*-
import time
import datetime
from flask import Blueprint,render_template,g,request,make_response,render_template_string
from Modules import loging,check ,produce,db_op
import string
import random
from sqlalchemy import and_,distinct
import __init__
app = __init__.app
page_index=Blueprint('index',__name__)
@page_index.route('/index')
def index():
    DB = db_op.rota
    date = time.strftime('%Y-%m-%d',time.localtime())
    new_date = datetime.date.today()+datetime.timedelta(1)
    ym = time.strftime('%Y.%m',time.localtime())
    if '@' in g.user:
        g.user = g.user.split('@')[0]
    data=[g.user]
    try:
        # 生成今日和明日的运维排班
        users = []
        duty = u'报警值班'
        pools = [u'李晓辉',u'周福成']
        for t in (date,new_date):
            VAL = DB.query.with_entities(DB.name).filter(and_(DB.date == t,DB.duty == duty)).all()
            if VAL:
                user = VAL[0][0]
            else:
                user = random.choice(pools)
                c = DB(name = user,duty = duty,date = t)
                db_op.DB.session.add(c)
                db_op.DB.session.commit()
            pools.remove(user)
            users.append(user)
        data.extend(users)
        ip=request.headers.get('X-Forwarded-For')
        if not ip :
            ip = request.remote_addr
        #获取页面菜单
        DB = db_op.op_menu
        nav_val = {}
        sub_val = {}
        Menu_val = DB.query.with_entities(DB.Menu_name, DB.id_name, DB.module_name, DB.action_name).filter(DB.grade >= g.grade).all()
        navMenu = DB.query.with_entities(distinct(DB.Menu_name)).filter(and_(DB.Menu == 'navMenu',DB.grade >= g.grade)).order_by(DB.Menu_id).all()
        navMenu = [Menu[0] for Menu in navMenu]
        for Menu in navMenu:
            val = [val[1:] for val in Menu_val if Menu in val]
            if val:
                nav_val[Menu] = val
        submenu = DB.query.with_entities(distinct(DB.Menu_name)).filter(and_(DB.Menu == 'submenu',DB.grade >= g.grade)).order_by(DB.Menu_id).all()
        submenu = [menu[0] for menu in submenu]
        for menu in submenu:
            val = [val[2:] for val in Menu_val if menu in val]
            if val:
                sub_val[menu] = val
        app_resp = make_response(render_template('index.html',datas=data,Year=ym,navMenu=navMenu,nav_val=nav_val,submenu=submenu,sub_val=sub_val,ip=ip))
        app_resp.set_cookie('secret_key',produce.Produce(length=6,chars=string.digits))
        return app_resp
    except Exception as e:
        loging.write(str(e))
        return render_template_string('获取数据异常!')
@page_index.before_request
@check.login_required(grade=10,page='index')
def check_login(error=None):
    produce.Async_log(g.user, request.url)
@page_index.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
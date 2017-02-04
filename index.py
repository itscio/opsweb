#-*- coding: utf-8 -*-
import time
import datetime
from flask import Blueprint,render_template,g,request,make_response,render_template_string
from Modules import loging,check ,produce,db_op
import string
import random
from sqlalchemy import and_
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
		#值班人员名单
        pools = [u'xxx', u'xxx',u'xxx']
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
        app_resp = make_response(render_template('index.html',datas=data,Year=ym,grade = g.grade,ip=ip))
        app_resp.set_cookie('secret_key',produce.Produce(length=6,chars=string.digits))
        return app_resp
    except Exception as e:
        loging.write(str(e))
        return render_template_string('获取数据异常!')
@page_index.before_request
@check.login_required(grade=2,page='index')
def check_login(error=None):
    produce.Async_log(g.user, request.url)
@page_index.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
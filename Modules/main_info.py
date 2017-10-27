#-*- coding: utf-8 -*-
import time
import datetime
from flask import g,request
from Modules import loging,db_op
import random
from functools import wraps
from sqlalchemy import and_,distinct
from rediscluster import RedisCluster
import __init__
app = __init__.app
logging = loging.Error()
nodes = app.config.get('NODES_PRODUCE')
RC = RedisCluster(startup_nodes=nodes,decode_responses=True,)
def main_info(func):
    @wraps(func)
    def info(*args, **kwargs):
        DB = db_op.rota
        g.main_infos = None
        date = time.strftime('%Y-%m-%d',time.localtime())
        ym = time.strftime('%Y',time.localtime())
        new_date = datetime.date.today()+datetime.timedelta(1)
        user = request.cookies.get('user')
        db = db_op.idc_users
        val = db.query.with_entities(db.grade).filter(db.name == user).all()
        grade = int(val[0][0]) if val else 10
        if user and  '@' in user:
            user = user.split('@')[0]
        data=[user]
        try:
            # 生成今日和明日的运维排班
            users = []
            duty = u'运维值班'
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
            if ',' in ip:
                ip = ip.split(',')[0]
            #获取页面菜单
            DB = db_op.op_menu
            nav_val = {}
            sub_val = {}
            Menu_val = DB.query.with_entities(DB.Menu_name, DB.id_name, DB.module_name, DB.action_name).filter(DB.grade >= grade).all()
            navMenu = DB.query.with_entities(distinct(DB.Menu_name)).filter(and_(DB.Menu == 'navMenu',DB.grade >= grade)).order_by(DB.Menu_id).all()
            navMenu = [Menu[0] for Menu in navMenu]
            for Menu in navMenu:
                val = [val[1:] for val in Menu_val if Menu in val]
                if val:
                    nav_val[Menu] = val
            submenu = DB.query.with_entities(distinct(DB.Menu_name)).filter(and_(DB.Menu == 'submenu',DB.grade >= grade)).order_by(DB.Menu_id).all()
            submenu = [menu[0] for menu in submenu]
            for menu in submenu:
                val = [val[2:] for val in Menu_val if menu in val]
                if val:
                    sub_val[menu] = val
            g.main_infos = {'datas':data,'navMenu':navMenu,'nav_val':nav_val,'submenu':submenu,'sub_val':sub_val,'ip':ip,'ym':ym}
            return func(*args, **kwargs)
        except Exception as e:
            loging.write(e)
            return func(*args, **kwargs)
    return info
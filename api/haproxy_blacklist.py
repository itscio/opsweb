#-*- coding: utf-8 -*-
from flask import Blueprint,jsonify,request
from Modules import db_op,check
import datetime
import time
import __init__
app = __init__.app
limiter = __init__.limiter
page_haproxy_blacklist = Blueprint('haproxy_blacklist', __name__)
@page_haproxy_blacklist.route('/haproxy_blacklist')
@limiter.limit("60/minute")
@check.acl_ip
def haproxy_blacklist():
    def Get_arg(arg):
        #解析请求参数
        if arg in request.args:
            return  request.args[arg].encode('utf-8')
        else:
            return None
    try:
        db = db_op.haproxy_blacklist
        ip = Get_arg('ip')
        if ip:
            tt = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime())
            if len(ip.strip().split('.')) == 4:
                expire_day = Get_arg('expire_day')
                expire_hour = Get_arg('expire_hour')
                expire_minute = Get_arg('expire_minute')
                tm = datetime.datetime.now() + datetime.timedelta(minutes=5)
                if expire_minute:
                    tm = datetime.datetime.now() + datetime.timedelta(minutes=int(expire_minute))
                if expire_hour :
                    tm = datetime.datetime.now() + datetime.timedelta(hours=int(expire_hour))
                if expire_day:
                    tm = datetime.datetime.now() + datetime.timedelta(days=int(expire_day))
                expire_time = tm.strftime('%Y-%m-%d %H:%M:%S')
                action = Get_arg('action')
                if action:
                    if 'delete' == action:
                        db.query.filter(db.ip == ip).update({db.stats: '2'})
                        db_op.DB.session.commit()
                        return jsonify({'result': '%s delete success!' % ip})
                else:
                    v = db(addtime = tt,ip=ip,stats='1',expire = expire_time,rule='black list api interface')
                    db_op.DB.session.add(v)
                    db_op.DB.session.commit()
                    return jsonify({'result': '%s add success!' % ip})
            else:
                return jsonify({'result':'%s format error!' % ip})
        else:
            return jsonify({'result':"IP Null!"})
    except Exception as e:
        return jsonify({'result':str(e)})

@page_haproxy_blacklist.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
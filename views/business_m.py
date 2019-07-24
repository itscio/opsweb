#-*- coding: utf-8 -*-
from flask import Blueprint,request,render_template,g,jsonify
import redis
from module import loging, db_op,user_auth,tools,Task
from flask_sqlalchemy import SQLAlchemy
import conf
app = conf.app
DB = SQLAlchemy(app)
logging = loging.Error()
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
Redis = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
page_business_monitor = Blueprint('business_monitor', __name__)
@page_business_monitor.route('/business_monitor')
@page_business_monitor.route('/business_monitor/<int:id>')
@page_business_monitor.route('/business_monitor/<lock>/<int:id>')
def business_monitor(id=None,lock=None):
    db_business_m = db_op.business_monitor
    tables = ['监控接口','接口状态','最新检测时间','上次报警时间','故障线路IP','手工检测','暂停监控']
    vals  = db_business_m.query.with_entities(db_business_m.id,db_business_m.url,db_business_m.code,
                                              db_business_m.update_time,db_business_m.alarm_time,
                                              db_business_m.error_ip).filter(db_business_m.lock == 0).all()
    codes = {0:'健康',1:'故障'}
    vals = [list(val) for val in vals]
    for val in vals:
        val[2] = codes[int(val[2])]
    if id and not lock:
        url = db_business_m.query.with_entities(db_business_m.url).filter(db_business_m.id == id).all()
        if url:
            url = url[0][0]
            try:
                result = Task.business_monitor(url)
                if result:
                    return jsonify({'status': 'error','infos':"接口服务故障!"})
                else:
                    return jsonify({'status': 'ok', 'infos':"接口服务正常!"})
            except:
                return jsonify({'status':'error','infos':'检测执行失败!'})
    if lock and id:
        try:
            project = db_business_m.query.with_entities(db_business_m.project).filter(db_business_m.id == id).all()
            if project:
                project = project[0][0]
            db_business_m.query.filter(db_business_m.id==id).update({db_business_m.lock:1})
            db_op.DB.session.commit()
            return jsonify({'status': 'ok', 'infos': "%s接口监控将暂时关闭!" %project})
        except:
            return jsonify({'status': 'error', 'infos': "%s接口监控关闭失败!" %project})
    return render_template('business_monitor.html',vals = vals,codes=codes,tables=tables)
@page_business_monitor.before_request
@user_auth.login_required(grade=1)
def check_login(exception = None):
    tools.Async_log(g.user, request.url)
@page_business_monitor.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
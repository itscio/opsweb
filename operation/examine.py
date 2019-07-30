#-*- coding: utf-8 -*-
from flask import Flask,Blueprint,request,render_template,g,jsonify,Flask
from module import user_auth,db_op,loging,tools
from sqlalchemy import desc
import redis
import time
from flask_mail import Mail
from flask_mail import Message
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_
app = Flask(__name__)
mail = Mail(app)
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/mail.conf')
app.config.from_pyfile('../conf/tokens.conf')
logging = loging.Error()
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
dt = time.strftime('%Y%m%d', time.localtime())
sender = app.config.get('MAIL_DEFAULT_SENDER')
receiver = app.config.get('DEFAULT_RECEIVER')
work_token = app.config.get('WORK_TOKEN')
Redis = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
page_examine = Blueprint('examine', __name__)
@page_examine.route('/publish_record')
def publish_record():
    db = db_op.publish_records
    vals = []
    try:
        vals = db.query.with_entities(db.date,db.time,db.user,db.project,db.version,db.package_url,db.describe,db.channel,
                                      db.result,db.flow_number).order_by(desc(db.id)).all()
        vals = [list(val) for val in vals]
        tables = ['日期','时间','申请人','项目','版本号','代码地址','变更描述','来源','执行结果','流水号']
    except Exception as e:
        logging.error(e)
    return render_template('publish_record.html',tables = tables,values = vals)

@page_examine.route('/op_log')
def op_log():
    td = time.strftime('%Y-%m-%d', time.localtime())
    Key = 'op_http_log_%s' % td
    tables = ['日期', '时间', 'IP', '用户', '访问页面']
    vals = []
    try:
        values = Redis.hgetall(Key)
        if values:
            values = sorted(values.items(), key=lambda item:item[0], reverse=True)
            for val in values:
                info = eval(val[1])
                info.extend([td,val[0]])
                vals.append(info)
    except Exception as e:
        logging.error(e)
    return render_template('op_log.html',tables = tables,vals = vals)

@page_examine.route('/ensure_application')
def ensure_application():
    try:
        db_work_order = db_op.work_order
        db_publish_application = db_op.publish_application
        db_sso = db_op.user_sso
        msg = None
        source = 'ensure_application'
        Key = 'new_application_work_number_%s' % dt
        #验证票据
        actions = {'complete': '已完成', 'deny': '已拒绝', 'rollback': '已回滚'}
        ticket = tools.http_args(request,'ticket')
        action = tools.http_args(request,'action')
        work_number = tools.http_args(request,'work_number')
        if ticket or (action == 'activate' and work_number):
            if ticket:
                work_number = Redis.get('work_order_ticket_%s' %ticket)
            if work_number:
                val = db_work_order.query.filter(db_work_order.work_number == int(work_number)).all()
                if val:
                    val = db_work_order.query.filter(and_(db_work_order.work_number == int(work_number),
                                                    db_work_order.source == source,db_work_order.status=='未受理')).all()
                    if val:
                        db_work_order.query.filter(db_work_order.work_number==int(work_number)).update({db_work_order.dingid:g.dingId,
                                                                                                        db_work_order.status:'受理中'})
                        db_op.DB.session.commit()
                        Redis.sadd(Key, work_number)
                        Redis.delete('work_order_ticket_%s' % ticket)
                        msg = "%s工单已受理!" %work_number
                    else:
                        msg = "工单暂时无法受理!"
                else:
                    msg = "无效的请求验证地址!"
            else:
                msg = "无效的请求验证地址!"
        #验证执行状态
        if action and work_number:
            moment = None
            if action in actions:
                if action == 'deny':
                    moment = tools.http_args(request,'moment')
                val = db_work_order.query.filter(and_(db_work_order.work_number == int(work_number),
                                                      db_work_order.source==source
                                                      ,db_work_order.status=='受理中')).all()
                if val:
                    db_work_order.query.filter(db_work_order.work_number == int(work_number)).update({
                         db_work_order.status:actions[action]})
                    db_op.DB.session.commit()
                    Redis.srem(Key, work_number)
                    if Redis.exists('op_send_mail_html_%s' %work_number):
                        dingid = db_publish_application.query.with_entities(db_publish_application.dingid).filter(db_publish_application.work_number==work_number).all()
                        mailer = db_sso.query.with_entities(db_sso.mail).filter(db_sso.dingunionid==dingid[0][0]).all()
                        if mailer:
                            Msg = Message("%s工单进度通知"%work_number, sender=sender, recipients=[mailer[0][0]],cc=[receiver],charset='utf-8')
                            mail_html = Redis.get('op_send_mail_html_%s' %work_number)
                            alarm_html = '<p style="color:red">工单当前进度:%s</p>' %actions[action]
                            if action == 'deny':
                                if moment:
                                    alarm_html = "%s<p>拒绝说明:%s</p>" %(alarm_html,moment)
                            Msg.html = '%s%s' % (mail_html,alarm_html)
                            with app.app_context():
                                mail.send(Msg)
                    msg = "%s工单当前状态:%s!" % (work_number, actions[action])
                else:
                    msg = "无效操作!"
    except Exception as e:
        logging.error(e)
        if not msg:
            msg = "未知异常错误!"
    finally:
        if action == 'deny':
            return jsonify({'status': 'ok'})
        #获取最新数据
        tables = ('工单号','日期','项目名称','版本','描述','申请人','执行人','详情','状态','操作')
        users = db_sso.query.with_entities(db_sso.dingunionid, db_sso.realName).all()
        users = {info[0]: info[1:] for info in users}
        projects = db_publish_application.query.with_entities(db_publish_application.work_number,db_publish_application.date,
                                                              db_publish_application.project,
                                                              db_publish_application.version,db_publish_application.describe,db_publish_application.dingid).all()
        projects = {info[0]: info[1:] for info in projects}
        work_orders = db_work_order.query.with_entities(db_work_order.work_number,
                                                        db_work_order.dingid,
                                                        db_work_order.status).filter(db_work_order.source==source).order_by(desc(db_work_order.id)).all()
        if action and work_number:
            if action == 'query':
                work_orders = db_work_order.query.with_entities(db_work_order.work_number,
                                                                db_work_order.dingid,
                                                                db_work_order.status).filter(and_(
                    db_work_order.source == source,db_work_order.work_number==work_number)).all()
        if work_orders:
            work_orders = [list(info) for info in work_orders]
            for info in work_orders:
                info.extend(projects[info[0]][:-1])
                info.extend(users[projects[info[0]][-1]])
                if info[1]:
                    info.append(users[info[1]][0])
                else:
                    info.append('')
        new_work_number = Redis.smembers(Key)
    return render_template('ensure_work_order.html',tables=tables,work_orders=work_orders,msg=msg,new_work_number=new_work_number,total='代码上线工单管理')

@page_examine.route('/ensure_server_auth')
def ensure_server_auth():
    try:
        db_work_order = db_op.work_order
        db_server_auth = db_op.server_auth
        db_sso = db_op.user_sso
        msg = None
        source = 'ensure_server_auth'
        Key = 'new_server_auth_work_number_%s' % dt
        actions = {'complete':'已完成','deny':'审批拒绝','agree':'审批通过'}
        action = tools.http_args(request,'action')
        work_number = tools.http_args(request,'work_number')
        #验证票据
        ticket = tools.http_args(request,'ticket')
        if ticket or (action == 'activate' and work_number):
            if ticket:
                work_number = Redis.get('work_order_ticket_%s' %ticket)
            if work_number:
                val = db_work_order.query.filter(db_work_order.work_number == int(work_number)).all()
                if val:
                    val = db_work_order.query.filter(and_(db_work_order.work_number == int(work_number),
                                                    db_work_order.source == source,db_work_order.status =='审批通过')).all()
                    if val:
                        db_work_order.query.filter(and_(db_work_order.work_number==int(work_number),
                                                        db_work_order.source==source)).update({db_work_order.dingid:g.dingId,
                                                                                                        db_work_order.status:'受理中'})
                        db_op.DB.session.commit()
                        Redis.sadd(Key, work_number)
                        Redis.delete('work_order_ticket_%s' % ticket)
                        msg = "%s工单已受理!" % work_number
                    else:
                        msg = "工单暂时无法受理!"
                else:
                    msg = "无效的请求验证地址!"
            else:
                msg = "无效的请求验证地址!"
        #验证执行状态
        if action and work_number:
            if action in actions:
                if action in ('deny','agree'):
                    if g.grade[0] != '0':
                        msg = '当前用户无审批权限!'
                        raise AssertionError
                val = db_work_order.query.filter(and_(db_work_order.work_number == int(work_number),
                                                      db_work_order.source==source,
                                                      db_work_order.status.in_(('待审批','受理中')))).all()
                if val:
                    db_work_order.query.filter(and_(db_work_order.work_number == int(work_number),
                                                    db_work_order.source==source)).update({
                         db_work_order.status:actions[action]})
                    db_op.DB.session.commit()
                    Redis.srem(Key,work_number)
                    #完成发送邮件
                    if Redis.exists('op_send_mail_html_%s' %work_number):
                        dingid = db_server_auth.query.with_entities(db_server_auth.dingid).filter(
                            db_server_auth.work_number == work_number).all()
                        mailer = db_sso.query.with_entities(db_sso.mail).filter(db_sso.dingunionid == dingid[0][0]).all()
                        if mailer:
                            Msg = Message("%s工单进度通知" % work_number, sender=sender, recipients=[mailer[0][0]], cc=[receiver],charset='utf-8')
                            mail_html = Redis.get('op_send_mail_html_%s' %work_number)
                            alarm_html = '<p style="color:red">工单当前进度:%s</p>' %actions[action]
                            Msg.html = '%s%s' % (mail_html, alarm_html)
                            if action == 'agree':
                                Msg.html = '%s%s%s' % (mail_html,alarm_html,Redis.get('op_send_mail_url_%s' % work_number))
                            with app.app_context():
                                mail.send(Msg)
                    if Redis.exists('op_send_dingding_msg_%s' % work_number) and action in ('deny','agree'):
                        text = eval(Redis.get('op_send_dingding_msg_%s' % work_number))
                        text.append("##### 审批结果:%s" %actions[action])
                        if action == 'agree':
                            text.append("##### %s" %Redis.get('op_send_dingding_url_%s' % work_number))
                        tools.dingding_msg(text, token=work_token)
                    msg = "%s工单当前状态:%s!" %(work_number,actions[action])
                else:
                    msg = "无效操作!"
    except Exception as e:
        logging.error(e)
        if not msg:
            msg = "未知异常错误!"
    finally:
        #获取最新数据
        tables = ('工单号','日期','申请人','部门','服务器列表','申请权限','所属用途','执行人','详情','状态','操作')
        users = db_sso.query.with_entities(db_sso.dingunionid, db_sso.realName, db_sso.department).all()
        users = {info[0]: info[1:] for info in users}
        servers = db_server_auth.query.with_entities(db_server_auth.work_number,
                                                             db_server_auth.date,
                                                             db_server_auth.servers,
                                                             db_server_auth.auth_level,
                                                             db_server_auth.purpose,
                                                             db_server_auth.dingid).all()
        servers = {info[0]: info[1:] for info in servers}
        work_orders = db_work_order.query.with_entities(db_work_order.work_number,
                                                        db_work_order.dingid,
                                                        db_work_order.status).filter(
            db_work_order.source == source).order_by(desc(db_work_order.id)).all()
        if action and work_number:
            if action == 'query':
                work_orders = db_work_order.query.with_entities(db_work_order.work_number,
                                                        db_work_order.dingid,
                                                        db_work_order.status).filter(and_(
                    db_work_order.source==source,db_work_order.work_number==work_number)).all()
        if work_orders:
            work_orders = [list(info) for info in work_orders]
            for info in work_orders:
                info.extend(servers[info[0]][:-1])
                info.insert(4, users[servers[info[0]][-1]][0])
                info.insert(5, users[servers[info[0]][-1]][-1])
                if info[1]:
                    info.append(users[info[1]][0])
                else:
                    info.append('')
        new_work_number = Redis.smembers(Key)
    return render_template('ensure_server_auth.html',tables=tables,work_orders=work_orders,msg=msg,new_work_number=new_work_number,total='服务器权限工单管理')

@page_examine.route('/ensure_sql_execute')
def ensure_sql_execute():
    try:
        db_work_order = db_op.work_order
        db_sql_execute = db_op.sql_execute
        db_sso = db_op.user_sso
        msg = None
        source = 'ensure_sql_execute'
        Key = 'new_sql_execute_work_number_%s' % dt
        #验证票据
        actions = {'complete': '已完成', 'deny': '已拒绝'}
        ticket = tools.http_args(request,'ticket')
        action = tools.http_args(request,'action')
        work_number = tools.http_args(request,'work_number')
        if ticket or (action == 'activate' and work_number):
            if ticket:
                work_number = Redis.get('work_order_ticket_%s' %ticket)
            if work_number:
                val = db_work_order.query.filter(db_work_order.work_number == int(work_number)).all()
                if val:
                    val = db_work_order.query.filter(and_(db_work_order.work_number == int(work_number),
                                                    db_work_order.source == source,db_work_order.status=='未受理')).all()
                    if val:
                        db_work_order.query.filter(and_(db_work_order.work_number==int(work_number),
                                                        db_work_order.source==source)).update({db_work_order.dingid:g.dingId,
                                                                                                        db_work_order.status:'受理中'})
                        db_op.DB.session.commit()
                        Redis.sadd(Key, work_number)
                        Redis.delete('work_order_ticket_%s' % ticket)
                        msg = "%s工单已受理!" %work_number
                    else:
                        msg = "工单暂时无法受理!"
                else:
                    msg = "无效的请求验证地址!"
            else:
                msg = "无效的请求验证地址!"
        #验证执行状态
        if action and work_number:
            moment = None
            if action in actions:
                if action == 'deny':
                    moment = tools.http_args(request,'moment')
                val = db_work_order.query.filter(and_(db_work_order.work_number == int(work_number),
                                                      db_work_order.source==source
                                                      ,db_work_order.status=='受理中')).all()
                if val:
                    db_work_order.query.filter(and_(db_work_order.work_number == int(work_number),
                                                    db_work_order.source==source)).update({
                         db_work_order.status:actions[action]})
                    db_op.DB.session.commit()
                    Redis.srem(Key, work_number)
                    if Redis.exists('op_send_mail_html_%s' %work_number):
                        dingid = db_sql_execute.query.with_entities(db_sql_execute.dingid).filter(db_sql_execute.work_number==work_number).all()
                        mailer = db_sso.query.with_entities(db_sso.mail).filter(db_sso.dingunionid==dingid[0][0]).all()
                        if mailer:
                            Msg = Message("%s工单进度通知"%work_number, sender=sender, recipients=[mailer[0][0]],cc=[receiver],charset='utf-8')
                            mail_html = Redis.get('op_send_mail_html_%s' %work_number)
                            alarm_html = '<p style="color:red">工单当前进度:%s</p>' %actions[action]
                            if action == 'deny':
                                if moment:
                                    alarm_html = "%s<p>拒绝说明:%s</p>" %(alarm_html,moment)
                            Msg.html = '%s%s' % (mail_html,alarm_html)
                            with app.app_context():
                                mail.send(Msg)
                    msg = "%s工单当前状态:%s!" % (work_number, actions[action])
                else:
                    msg = "无效操作!"
    except Exception as e:
        logging.error(e)
        if not msg:
            msg = "未知异常错误!"
    finally:
        if action == 'deny':
            return jsonify({'status': 'ok'})
        #获取最新数据
        tables = ('工单号','日期','服务器','端口','数据库','变更描述','申请人','执行人','详情','状态','操作')
        users = db_sso.query.with_entities(db_sso.dingunionid, db_sso.realName).all()
        users = {info[0]: info[1:] for info in users}
        sql_executes = db_sql_execute.query.with_entities(db_sql_execute.work_number,db_sql_execute.date,
                                                      db_sql_execute.host,db_sql_execute.port,db_sql_execute.database,
                                                      db_sql_execute.describe,
                                                      db_sql_execute.dingid).all()
        sql_executes = {info[0]: info[1:] for info in sql_executes}
        work_orders = db_work_order.query.with_entities(db_work_order.work_number,
                                                        db_work_order.dingid,
                                                        db_work_order.status).filter(db_work_order.source==source).order_by(desc(db_work_order.id)).all()
        if action and work_number:
            if action == 'query':
                work_orders = db_work_order.query.with_entities(db_work_order.work_number,
                                                                db_work_order.dingid,
                                                                db_work_order.status).filter(and_(
                    db_work_order.source == source,db_work_order.work_number==work_number)).all()
        if work_orders:
            work_orders = [list(info) for info in work_orders]
            for info in work_orders:
                info.extend(sql_executes[info[0]][:-1])
                info.extend(users[sql_executes[info[0]][-1]])
                if info[1]:
                    info.append(users[info[1]][0])
                else:
                    info.append('')
        new_work_number = Redis.smembers(Key)
    return render_template('ensure_sql_execute.html',tables=tables,work_orders=work_orders,msg=msg,new_work_number=new_work_number,total='线上SQL执行工单管理')

@page_examine.route('/ensure_project_offline')
def ensure_project_offline():
    try:
        db_work_order = db_op.work_order
        db_project_offline = db_op.project_offline
        db_sso = db_op.user_sso
        msg = None
        source = 'ensure_project_offline'
        Key = 'new_project_offline_work_number_%s' % dt
        #验证票据
        actions = {'complete': '已完成', 'deny': '已拒绝'}
        ticket = tools.http_args(request,'ticket')
        action = tools.http_args(request,'action')
        work_number = tools.http_args(request,'work_number')
        if ticket or (action == 'activate' and work_number):
            if ticket:
                work_number = Redis.get('work_order_ticket_%s' %ticket)
            if work_number:
                val = db_work_order.query.filter(db_work_order.work_number == int(work_number)).all()
                if val:
                    val = db_work_order.query.filter(and_(db_work_order.work_number == int(work_number),
                                                    db_work_order.source == source,db_work_order.status=='未受理')).all()
                    if val:
                        db_work_order.query.filter(db_work_order.work_number==int(work_number)).update({db_work_order.dingid:g.dingId,
                                                                                                        db_work_order.status:'受理中'})
                        db_op.DB.session.commit()
                        Redis.sadd(Key, work_number)
                        Redis.delete('work_order_ticket_%s' % ticket)
                        msg = "%s工单已受理!" %work_number
                    else:
                        msg = "工单暂时无法受理!"
                else:
                    msg = "无效的请求验证地址!"
            else:
                msg = "无效的请求验证地址!"
        #验证执行状态
        if action and work_number:
            moment = None
            if action in actions:
                if action == 'deny':
                    moment = tools.http_args(request,'moment')
                val = db_work_order.query.filter(and_(db_work_order.work_number == int(work_number),
                                                      db_work_order.source== source
                                                      ,db_work_order.status=='受理中')).all()
                if val:
                    db_work_order.query.filter(db_work_order.work_number == int(work_number)).update({
                         db_work_order.status:actions[action]})
                    db_op.DB.session.commit()
                    Redis.srem(Key, work_number)
                    if Redis.exists('op_send_mail_html_%s' %work_number):
                        dingid = db_project_offline.query.with_entities(db_project_offline.dingid).filter(db_project_offline.work_number==work_number).all()
                        mailer = db_sso.query.with_entities(db_sso.mail).filter(db_sso.dingunionid==dingid[0][0]).all()
                        if mailer:
                            Msg = Message("%s工单进度通知"%work_number, sender=sender, recipients=[mailer[0][0]],cc=[receiver],charset='utf-8')
                            mail_html = Redis.get('op_send_mail_html_%s' %work_number)
                            alarm_html = '<p style="color:red">工单当前进度:%s</p>' %actions[action]
                            if action == 'deny':
                                if moment:
                                    alarm_html = "%s<p>拒绝说明:%s</p>" %(alarm_html,moment)
                            Msg.html = '%s%s' % (mail_html,alarm_html)
                            with app.app_context():
                                mail.send(Msg)
                    msg = "%s工单当前状态:%s!" % (work_number, actions[action])
                else:
                    msg = "无效操作!"
    except Exception as e:
        logging.error(e)
        if not msg:
            msg = "未知异常错误!"
    finally:
        if action == 'deny':
            return jsonify({'status': 'ok'})
        #获取最新数据
        tables = ('工单号','日期','项目名称','描述','申请人','执行人','详情','状态','操作')
        users = db_sso.query.with_entities(db_sso.dingunionid, db_sso.realName).all()
        users = {info[0]: info[1:] for info in users}
        projects = db_project_offline.query.with_entities(db_project_offline.work_number,db_project_offline.date,
                                                          db_project_offline.project,db_project_offline.describe,db_project_offline.dingid).all()
        projects = {info[0]: info[1:] for info in projects}
        work_orders = db_work_order.query.with_entities(db_work_order.work_number,
                                                        db_work_order.dingid,
                                                        db_work_order.status).filter(db_work_order.source==source).order_by(desc(db_work_order.id)).all()
        if action and work_number:
            if action == 'query':
                work_orders = db_work_order.query.with_entities(db_work_order.work_number,
                                                                db_work_order.dingid,
                                                                db_work_order.status).filter(and_(
                    db_work_order.source == source,db_work_order.work_number==work_number)).all()
        if work_orders:
            work_orders = [list(info) for info in work_orders]
            for info in work_orders:
                info.extend(projects[info[0]][:-1])
                info.extend(users[projects[info[0]][-1]])
                if info[1]:
                    info.append(users[info[1]][0])
                else:
                    info.append('')
        new_work_number = Redis.smembers(Key)
    return render_template('ensure_project_offline.html',tables=tables,work_orders=work_orders,msg=msg,new_work_number=new_work_number,total='项目下线工单管理')

@page_examine.route('/ensure_other_work')
def ensure_other_work():
    try:
        db_work_order = db_op.work_order
        db_other_work = db_op.other_work
        db_sso = db_op.user_sso
        msg = None
        source = 'ensure_other_work'
        Key = 'new_other_work_work_number_%s' % dt
        #验证票据
        actions = {'complete': '已完成', 'deny': '已拒绝','refuse':'审批拒绝','agree':'审批通过'}
        ticket = tools.http_args(request,'ticket')
        action = tools.http_args(request,'action')
        work_number = tools.http_args(request,'work_number')
        if ticket or (action == 'activate' and work_number):
            if ticket:
                work_number = Redis.get('work_order_ticket_%s' %ticket)
            if work_number:
                val = db_work_order.query.filter(db_work_order.work_number == int(work_number)).all()
                if val:
                    val = db_work_order.query.filter(and_(db_work_order.work_number == int(work_number),
                                                    db_work_order.source == source,db_work_order.status=='审批通过')).all()
                    if val:
                        db_work_order.query.filter(and_(db_work_order.work_number==int(work_number),
                                                        db_work_order.source==source)).update({db_work_order.dingid:g.dingId,
                                                                                                        db_work_order.status:'受理中'})
                        db_op.DB.session.commit()
                        Redis.sadd(Key, work_number)
                        Redis.delete('work_order_ticket_%s' % ticket)
                        msg = "%s工单已受理!" %work_number
                    else:
                        msg = "工单暂时无法受理!"
                else:
                    msg = "无效的请求验证地址!"
            else:
                msg = "无效的请求验证地址!"
        #验证执行状态
        if action and work_number:
            moment = None
            if action in actions:
                if action in ('refuse','agree'):
                    if g.grade[0] != '0':
                        msg = '当前用户无审批权限!'
                        raise AssertionError
                if action == 'deny':
                    moment = tools.http_args(request,'moment')
                val = db_work_order.query.filter(and_(db_work_order.work_number == int(work_number),
                                                      db_work_order.source==source
                                                      ,db_work_order.status.in_(('待审批','受理中')))).all()
                if val:
                    db_work_order.query.filter(and_(db_work_order.work_number == int(work_number),
                                                    db_work_order.source==source)).update({
                         db_work_order.status:actions[action]})
                    db_op.DB.session.commit()
                    Redis.srem(Key, work_number)
                    if Redis.exists('op_send_mail_html_%s' %work_number):
                        try:
                            dingid = db_other_work.query.with_entities(db_other_work.dingid).filter(db_other_work.work_number==work_number).all()
                            mailer = db_sso.query.with_entities(db_sso.mail).filter(db_sso.dingunionid==dingid[0][0]).all()
                            if mailer:
                                receiver = Redis.get('op_other_work_receiver_%s' % work_number)
                                Msg = Message("%s工单进度通知"%work_number, sender=sender, recipients=[mailer[0][0]],
                                              cc=[receiver],charset='utf-8')
                                mail_html = Redis.get('op_send_mail_html_%s' %work_number)
                                alarm_html = '<p style="color:red">工单当前进度:%s</p>' %actions[action]
                                if action == 'deny':
                                    if moment:
                                        alarm_html = "%s<p>拒绝说明:%s</p>" %(alarm_html,moment)
                                Msg.html = '%s%s' % (mail_html, alarm_html)
                                if action == 'agree':
                                    Msg.html = '%s%s%s' % (mail_html,alarm_html,Redis.get('op_send_ensure_url_%s' % work_number))
                                with app.app_context():
                                    mail.send(Msg)
                        except Exception as e:
                            logging.error(e)
                    msg = "%s工单当前状态:%s!" % (work_number, actions[action])
                else:
                    msg = "无效操作!"
    except Exception as e:
        logging.error(e)
        if not msg:
            msg = "未知异常错误!"
    finally:
        if action == 'deny':
            return jsonify({'status': 'ok'})
        #获取最新数据
        tables = ('工单号','日期','事项标题','事项描述','申请人','执行人','详情','状态','操作')
        users = db_sso.query.with_entities(db_sso.dingunionid, db_sso.realName).all()
        users = {info[0]: info[1:] for info in users}
        other_works = db_other_work.query.with_entities(db_other_work.work_number,db_other_work.date,db_other_work.title,
                                                         db_other_work.describe,
                                                         db_other_work.dingid).all()
        other_works = {info[0]: info[1:] for info in other_works}
        work_orders = db_work_order.query.with_entities(db_work_order.work_number,
                                                        db_work_order.dingid,
                                                        db_work_order.status).filter(db_work_order.source==source).order_by(desc(db_work_order.id)).all()
        if action and work_number:
            if action == 'query':
                work_orders = db_work_order.query.with_entities(db_work_order.work_number,
                                                                db_work_order.dingid,
                                                                db_work_order.status).filter(and_(
                    db_work_order.source == source,db_work_order.work_number==work_number)).all()
        if work_orders:
            work_orders = [list(info) for info in work_orders]
            for info in work_orders:
                info.extend(other_works[info[0]][:-1])
                info.extend(users[other_works[info[0]][-1]])
                if info[1]:
                    info.append(users[info[1]][0])
                else:
                    info.append('')
        new_work_number = Redis.smembers(Key)
    return render_template('ensure_other_work.html',tables=tables,work_orders=work_orders,msg=msg,new_work_number=new_work_number,total='运维其它事项工单管理')

@page_examine.before_request
@user_auth.login_required(grade=1)
def check_login(error=None):
    tools.Async_log(g.user, request.url)
@page_examine.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
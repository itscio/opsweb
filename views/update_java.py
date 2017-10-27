#-*- coding: utf-8 -*-
import redis
from flask import Blueprint,render_template,render_template_string,g,flash,request
from Modules import check,MyForm,db_op,loging,Mysql,produce,java_update,main_info
import __init__
app = __init__.app
page_update_java = Blueprint('update_java',__name__)
redisHost = app.config.get('REDIS_HOST')
redisPort = app.config.get('REDIS_PORT')
myRedis = redis.StrictRedis(host=redisHost,port=redisPort)
@page_update_java.route('/update_java_query', methods = ['GET','POST'])
@check.login_required(grade=10)
def update_java_query():
    K = '%s_%s' %(g.user,g.secret_key)
    messageKey = '%s_update_java' % K
    Key_incr = '%s_incr' % messageKey
    myRedis.expire(messageKey,30)
    if myRedis.lrange(messageKey,0,-1):
        data = myRedis.rpop(messageKey)
        if '_End_' in data:
            myRedis.expire(messageKey,3)
        return render_template_string(data)
    else:
        myRedis.incr(Key_incr, 1)
        if int(myRedis.get(Key_incr)) > 10000:
            myRedis.delete(Key_incr)
            return render_template_string("_End_")
        return render_template_string("")
@page_update_java.route('/update_java',methods = ['GET','POST'])
@check.login_required(grade=0)
@main_info.main_info
def update_java():
    produce.Async_log(g.user, request.url)
    K = '%s_%s' %(g.user,g.secret_key)
    messageKey = '%s_update_java' % K
    publish_key = '%s_update_key' % K
    form = MyForm.MyForm_updateJboss()
    if form.submit.data:
        try:
            if form.text.data:
                if myRedis.exists(messageKey):
                    raise flash('上线操作过于频繁,请稍等%s秒......' %myRedis.ttl(messageKey))
                myRedis.lpush(messageKey, 'check env......')
                tags = form.text.data.strip().splitlines()
                assert len(tags)==1,'Can only execute a project at a time!'
                project = form.text.data.strip()
                warname = project.split('-')[0]
                Action = form.selectAction.data
                Gray = form.Gray.data
                Type = 1
                dbTable = db_op.java_list
                #灰度发布
                if Gray:
                    ServerList = dbTable.query.with_entities(dbTable.ip, dbTable.user).filter(db_op.DB.and_(dbTable.project == warname, dbTable.type == Type,dbTable.Gray == '1')).limit(1).all()
                    if not ServerList:
                        ServerList = dbTable.query.with_entities(dbTable.ip, dbTable.user).filter(db_op.DB.and_(dbTable.project == warname, dbTable.type == Type)).limit(1).all()
                        if ServerList:
                            for ip, username in ServerList:
                                dbTable.query.filter(db_op.DB.and_(dbTable.ip == ip, dbTable.user == username)).update({dbTable.Gray:'1'})
                        else:
                            flash('%s Not found' % warname)
                            return render_template('Message_static.html',Main_Infos=g.main_infos)
                else:
                    ServerList = dbTable.query.with_entities(dbTable.ip,dbTable.user).filter(db_op.DB.and_(dbTable.project == warname,dbTable.type == Type)).all()
                if ServerList:
                    myRedis.lpush(messageKey, '    --->check env pass!')
                    myRedis.lpush(messageKey, '-' * 80 + '\n')
                    information = {}
                    information['warname'] = warname
                    information['project'] = project
                    information['ServerList'] = ServerList
                    information['Action'] = Action
                    information['Gray'] = Gray
                    myRedis.lpush(publish_key,information)
                    mysql_operation = Mysql.mysql_op(g.user,Action,Type,project,Gray)
                    mysql_operation.op_operation()
                    Scheduler = produce.Scheduler_publish()
                    Scheduler = Scheduler.Scheduler_mem(java_update.java_update,publish_key,messageKey)
                    Scheduler.start()
                else:
                    flash('%s Not found' % warname)
                    return render_template('Message_static.html',Main_Infos=g.main_infos)
        except Exception as e:
                flash(e)
                return render_template('Message_static.html',Main_Infos=g.main_infos)
        return render_template('java_update_show.html',Main_Infos=g.main_infos)
    return render_template('java_update.html',Main_Infos=g.main_infos,form=form)

@page_update_java.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()

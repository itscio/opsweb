#-*- coding: utf-8 -*-
import redis
from flask import Blueprint,render_template,render_template_string,g,flash,request,redirect,url_for
from Modules import check,MyForm,db_op,loging,Mysql,produce
import time
import string
import __init__
app = __init__.app
page_publish_java = Blueprint('publish_java',__name__)
Mobile = app.config.get('MOBILE')
redisHost = app.config.get('REDIS_HOST')
redisPort = app.config.get('REDIS_PORT')
myRedis = redis.StrictRedis(host=redisHost,port=redisPort)
@page_publish_java.route('/publish_java_query', methods = ['GET','POST'])
@check.login_required(grade=2)
def publish_java_query():
    K = '%s_%s' %(g.user,g.secret_key)
    messageChannelKey = '%s_publish_java' % K
    data = myRedis.rpop(messageChannelKey)
    return render_template_string(data or "")
@page_publish_java.route('/qrcode_java/<User>/<Grade>')
def Qrcode(User = None,Grade = None):
    try:
        if User and Grade == '2':
            verify_key = "{0}_{1}".format(User,Grade)
            code = produce.Produce(length=6, chars=string.digits)
            myRedis.set(verify_key,code)
            myRedis.expire(verify_key, 900)
            # send sms
            result = produce.send_sms(content='上线码:{0} 申请人:{1} 15分钟内有效!'.format(code,User), mobile=Mobile)
            if isinstance(result, dict):
                if result['code'] == 200:
                    INFO = '上线码已成功发送给领导!'
                else:
                    INFO = '上线码发送失败!'
            else:
                INFO = '上线码发送失败!'
        else:
            INFO = "无权请求上线码!"
    except Exception as e:
        INFO = str(e)
    return render_template('qrcode.html', INFO=INFO)
@page_publish_java.route('/publish_java',methods = ['GET','POST'])
@check.login_required(grade=2)
def publish_java():
    produce.Async_log(g.user, request.url)
    K = '%s_%s' %(g.user,g.secret_key)
    messageKey = '%s_publish_java' % K
    taskKey = 'publish_java'
    qrcode_url = "https://xxx.baihe.com/xxx_java/{0}/{1}".format(g.user, g.grade)
    form = MyForm.MyForm_publishJboss()
    if form.submit.data:
        Action = form.selectAction.data
        Type = int(form.selectType.data)
        Gray = form.Gray.data
        Way = form.selectWay.data
        code = form.code.data
        work = form.selectwork.data
        grade = form.selectgrade.data
        changelog = form.changelog.data
        tags = form.text.data.strip().splitlines()
        if tags and changelog:
            try:
                assert len(tags) == 1, '错误:只能同时上线一个项目!'
                warTagName = tags[0]
                version = '0.0.0'
                if Action == 'restart':
                    warname = warTagName
                elif Way == 'SVN':
                    assert '.war.zip' in warTagName, '错误:格式错误!格式应为: baihe-xxxx-x.x.x.war.zip'
                    warname = warTagName.split('-')[:-1]
                    version = warTagName.split('-')[-1].replace('.war.zip','')
                    warname = '-'.join(warname) + '.war'
                elif Way == 'GIT':
                    warname = "{0}.war".format(warTagName.split('/')[-1])
            except Exception as e:
                flash(e)
            else:
                myRedis.lpush(messageKey, 'check env......')
                try:
                    # 用户权限判断
                    if g.grade == 2:
                        if code:
                            verify_key = "{0}_{1}".format(g.user,g.grade)
                            verify_code = myRedis.get(verify_key)
                            if verify_code == str(code):
                                myRedis.lpush(messageKey, '    --->verify code pass!')
                                myRedis.delete(verify_key)
                            else:
                                flash('上线码验证错误!')
                                return redirect(url_for('publish_java.publish_java'))
                        else:
                            flash('上线码不能为空!')
                            return redirect(url_for('publish_java.publish_java'))
                    myRedis.lpush(messageKey, '    --->check env pass!')
                    myRedis.lpush(messageKey, '-' * 80 + '\n')
                    dbTable = db_op.java_list
                    #灰度发布
                    if Gray:
                        ServerList = dbTable.query.with_entities(dbTable.ip, dbTable.user).filter(db_op.DB.and_(dbTable.project == warname, dbTable.type == Type,dbTable.Gray == '1')).limit(1).all()
                        if not ServerList:
                            ServerList = dbTable.query.with_entities(dbTable.ip, dbTable.user).filter(db_op.DB.and_(dbTable.project == warname, dbTable.type == Type)).limit(1).all()
                            loging.write(ServerList[:])
                            if ServerList:
                                for ip, username in ServerList:
                                    dbTable.query.filter(db_op.DB.and_(dbTable.ip == ip, dbTable.user == username)).update({dbTable.Gray:'1'})
                            else:
                                raise flash('%s 没有在上线列表中找到!' % warname)
                    else:
                        ServerList = dbTable.query.with_entities(dbTable.ip,dbTable.user).filter(db_op.DB.and_(dbTable.project == warname,dbTable.type == Type)).all()
                    if ServerList:
                        information = {}
                        information['warname'] = warname
                        information['warTagName'] = warTagName
                        information['ServerList'] = ServerList
                        information['Action'] = Action
                        information['key'] = messageKey
                        information['Gray'] = Gray
                        information['Type'] = Type
                        information['Way']  = Way
                        myRedis.delete(messageKey)
                        myRedis.lpush(taskKey,information)
                        mysql_operation = Mysql.mysql_op(g.user,Action,Type,warname,version,Gray,work,grade,changelog)
                        mysql_operation.op_operation()
                        Scheduler = produce.Scheduler_publish()
                        Scheduler = Scheduler.Scheduler_mem(Scheduler.job_publish_java)
                        Scheduler.start()
                    else:
                        raise flash('%s 没有在上线列表中找到!' % warname)
                except Exception as e:
                    if 'old' not in str(e):
                        flash(e)
                    myRedis.lpush(messageKey, 'End')
                    return render_template('Message.html')
                return render_template('java_publish_show.html')
        else:
            flash("错误:文本框内容不能为空!")
    return render_template('java_publish.html',form=form,qrcode_url=qrcode_url)

@page_publish_java.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()

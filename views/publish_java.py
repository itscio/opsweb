#-*- coding: utf-8 -*-
import redis
from flask import Blueprint,render_template,render_template_string,g,flash,request
from Modules import check,MyForm,db_op,loging,Mysql,produce,java_publish
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
@check.login_required(grade=10)
def publish_java_query():
    K = '%s_%s' %(g.user,g.secret_key)
    messageChannelKey = '%s_publish_java' % K
    data = myRedis.rpop(messageChannelKey)
    return render_template_string(data or "")
@page_publish_java.route('/qrcode_java/<User>/<Grade>')
def Qrcode(User = None,Grade = None):
    try:
        if User and Grade:
            if User and int(Grade) >= 2:
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
                INFO = "无需申请上线码!"
        else:
            INFO = "非法请求信息!"
    except Exception as e:
        INFO = str(e)
    return render_template('qrcode.html', INFO=INFO)
@page_publish_java.route('/publish_java',methods = ['GET','POST'])
@check.login_required(grade=10)
def publish_java():
    produce.Async_log(g.user, request.url)
    K = '%s_%s' %(g.user,g.secret_key)
    messageKey = '%s_publish_java' % K
    publish_key = '%s_publish_key' % K
    qrcode_url = "https://op.baihe.com/qrcode_java/{0}/{1}".format(g.user, g.grade)
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
        myRedis.lpush(messageKey, 'check env......')
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
                try:
                    publish_time = time.strftime("%H", time.localtime())
                    if code:
                        verify_key = "{0}_{1}".format(g.user, g.grade)
                        verify_code = myRedis.get(verify_key)
                        if verify_code == str(code):
                            myRedis.lpush(messageKey, '    --->verify code pass!')
                            myRedis.delete(verify_key)
                        else:
                            raise flash('上线码验证错误!')
                    else:
                        # 用户权限判断
                        if g.grade >= 2 and Type == 1 and int(grade) >=5:
                            raise flash('需申请验证码!')
                        if g.grade >= 2 and int(grade) <= 4 and Type == 1 and (int(publish_time) >= 17 or int(publish_time) <= 9):
                            raise flash('仅允许在10-17点时间段进行自助操作，需申请验证码!')
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
                        if Type == 1:
                            ServerList.append(('172.16.4.188','java'))
                    if ServerList:
                        information = {}
                        information['warname'] = warname
                        information['warTagName'] = warTagName
                        information['ServerList'] = ServerList
                        information['Action'] = Action
                        information['Gray'] = Gray
                        information['Type'] = Type
                        information['Way']  = Way
                        myRedis.delete(messageKey)
                        myRedis.lpush(publish_key,information)
                        mysql_operation = Mysql.mysql_op(g.user,Action,Type,warname,version,Gray,work,grade,changelog)
                        mysql_operation.op_operation()
                        Scheduler = produce.Scheduler_publish()
                        Scheduler = Scheduler.Scheduler_mem(java_publish.java_publish,publish_key,messageKey)
                        Scheduler.start()
                    else:
                        raise flash('%s 没有在上线列表中找到!' % warname)
                except Exception as e:
                    if 'old' not in str(e):
                        flash(e)
                else:
                    return render_template('java_publish_show.html')
        else:
            flash("错误:文本框内容不能为空!")
    return render_template('java_publish.html',form=form,qrcode_url=qrcode_url)

@page_publish_java.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()

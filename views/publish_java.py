#-*- coding: utf-8 -*-
import redis
from flask import Blueprint,render_template,render_template_string,g,flash,request
from Modules import check,MyForm,db_op,loging,Mysql,produce,java_publish,Md5,main_info
from rediscluster import RedisCluster
import time
import string
import __init__
app = __init__.app
logging = loging.Error()
page_publish_java = Blueprint('publish_java',__name__)
Mobile = app.config.get('PHP_MOBILE')
JAVA_Mobile = app.config.get('JAVA_MOBILE')
nodes = app.config.get('NODES_PRODUCE')
myRedis = RedisCluster(startup_nodes=nodes,decode_responses=True)
crypto_key = app.config.get('CRYPTO_KEY')
@page_publish_java.route('/publish_java_query', methods = ['GET','POST'])
@check.login_required(grade=10)
def publish_java_query():
    K = '%s_%s' %(g.user,g.secret_key)
    messageKey = '%s_publish_java' % K
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
@page_publish_java.route('/qrcode_java/<User>/<Grade>/<project>/<project_level>')
def Qrcode(User = None,Grade = None,project=None,project_level = None):
    try:
        tw = int(time.strftime('%w', time.localtime()))
        publish_time = int(time.strftime("%H", time.localtime()))
        crypto = Md5.crypto(crypto_key)
        if User and Grade:
            db = db_op.idc_users
            User = crypto.decrypt(User)
            project = crypto.decrypt(project)
            if db.query.filter(db.name == User).all() and int(Grade) >= 2:
                if tw in (0,6) or publish_time >= 17 or publish_time < 9:
                    verify_key = "{0}_{1}".format(User,project)
                    code = str(produce.Produce(length=6, chars=string.digits))
                    if '0' in code:
                        code.replace('0','1')
                    myRedis.set(verify_key,code)
                    myRedis.expire(verify_key, 900)
                    # send sms
                    mobile = JAVA_Mobile
                    if int(project_level) >= 7:
                        mobile = Mobile
                    result = produce.send_sms(content='上线码:{0} 上线项目:{1} 申请人:{2} 15分钟内有效!'.format(code,project,User), mobile=mobile)
                    if isinstance(result, dict):
                        if result['code'] == 200:
                            INFO = '上线码已成功发送给JAVA领导!'
                            if int(project_level) >= 7:
                                INFO = '上线码已成功发送给曾总!'
                        else:
                            INFO = '上线码发送失败!'
                    else:
                        INFO = '上线码发送失败!'
                else:
                    INFO = "只允许在工作日17点之后或者周末全天申请!"
            else:
                INFO = "该账号无权申请上线码!"
        else:
            INFO = '非法请求信息!'
    except Exception as e:
        INFO = str(e)
    return render_template('qrcode.html',INFO=INFO)
@page_publish_java.route('/publish_java',methods = ['GET','POST'])
@check.login_required(grade=10)
@main_info.main_info
def publish_java():
    produce.Async_log(g.user, request.url)
    K = '%s_%s' %(g.user,g.secret_key)
    messageKey = '%s_publish_java' % K
    publish_key = '%s_publish_key' % K
    qrcode_url = None
    form = MyForm.MyForm_publishJboss()
    if form.submit.data:
        Action = form.selectAction.data
        Type = int(form.selectType.data)
        Gray = form.Gray.data
        Way = form.selectWay.data
        code = form.code.data
        work = form.selectwork.data
        changelog = form.changelog.data
        tags = form.text.data.strip().splitlines()
        if tags and changelog:
            try:
                if myRedis.exists(messageKey):
                    raise flash('上线操作过于频繁,请稍等%s秒......' %myRedis.ttl(messageKey))
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
                    project_db = db_op.project_level
                    project_level = project_db.query.with_entities(project_db.level).filter(project_db.project == warname).all()
                    # 测外不强制项目等级
                    if Type == 2:
                        if project_level:
                            project_level = int(project_level[0][0])
                        else:
                            project_level = 1
                    else:
                        if project_level:
                            project_level = int(project_level[0][0])
                            crypto = Md5.crypto(crypto_key)
                            qrcode_url = "https://op.baihe.com/qrcode_java/{0}/{1}/{2}/{3}".format(crypto.encrypt(g.user),g.grade,crypto.encrypt(warname),project_level)
                        else:
                            raise flash('没有找到该项目的对应项目等级!')
                    publish_time = time.strftime("%H", time.localtime())
                    if code:
                        verify_key = "{0}_{1}".format(g.user,warname)
                        verify_code = myRedis.get(verify_key)
                        if verify_code == str(code):
                            myRedis.lpush(messageKey, '    --->verify code pass!')
                            myRedis.expire(messageKey,30)
                            myRedis.delete(verify_key)
                        else:
                            raise flash('%s 该上线码验证不通过!' %str(code))
                    else:
                        # 用户权限及行为判断
                        tw = int(time.strftime('%w', time.localtime(time.time())))
                        if g.grade >= 2 and Type == 1 and Action == 'publish':
                            if project_level >= 5:
                                raise flash('该项目等级为%s级,需申请上线码!' % project_level)
                            if tw in (2, 4):
                                if project_level <= 4 and (int(publish_time) >= 17 or int(publish_time) <= 9):
                                    raise flash('仅允许在10-17点时间段进行上线操作，需申请上线码!')
                            else:
                                raise flash('4级及以下常规项目只限在周二和周四上线,修复BUG需申请上线码!')
                        if g.grade >= 2 and Action == 'rollback':
                            raise flash('没有权限进行回滚操作!')
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
                                raise flash('%s 没有在上线列表中找到!' % warname)
                    else:
                        ServerList = dbTable.query.with_entities(dbTable.ip,dbTable.user).filter(db_op.DB.and_(dbTable.project == warname,dbTable.type == Type)).all()
                        if Type == 1:
                            ServerList.append(('172.16.4.188','java'))
                    if ServerList:
                        myRedis.lpush(messageKey, 'check security policy......')
                        myRedis.expire(messageKey, 30)
                        information = {}
                        information['warname'] = warname
                        information['warTagName'] = warTagName
                        information['ServerList'] = ServerList
                        information['Action'] = Action
                        information['Gray'] = Gray
                        information['Type'] = Type
                        information['Way']  = Way
                        myRedis.lpush(publish_key,information)
                        mysql_operation = Mysql.mysql_op(g.user,Action,Type,warname,version,Gray,work,project_level,changelog)
                        mysql_operation.op_operation()
                        Scheduler = produce.Scheduler_publish()
                        Scheduler = Scheduler.Scheduler_mem(java_publish.java_publish,publish_key,messageKey)
                        Scheduler.start()
                        myRedis.lpush(messageKey, '    --->check pass!')
                        myRedis.lpush(messageKey, '-' * 80 + '\n')
                    else:
                        raise flash('%s 没有在上线列表中找到!' % warname)
                except Exception as e:
                    if 'old' not in str(e):
                        flash(e)
                    if qrcode_url:
                        return render_template('java_publish.html',Main_Infos=g.main_infos, form=form, qrcode_url=qrcode_url)
                else:
                    return render_template('java_publish_show.html',Main_Infos=g.main_infos)
        else:
            flash("错误:文本框内容不能为空!")
    return render_template('java_publish.html',Main_Infos=g.main_infos,form=form,qrcode_url=qrcode_url)

@page_publish_java.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()

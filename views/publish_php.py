#-*- coding: utf-8 -*-
import redis
from flask import Blueprint,render_template,render_template_string,g,flash,request
from Modules import check,MyForm,db_op,Mysql,produce,loging,php_publish,Md5,main_info
from rediscluster import RedisCluster
import re
from sqlalchemy import and_
import string
import time
import __init__
app = __init__.app
Mobile = app.config.get('PHP_MOBILE')
PHP_Mobile = app.config.get('PHP_MOBILE')
crypto_key = app.config.get('CRYPTO_KEY')
nodes = app.config.get('NODES_PRODUCE')
Redis = RedisCluster(startup_nodes=nodes,decode_responses=True)
page_publish_php = Blueprint('publish_php',__name__)
@page_publish_php.route('/publish_query',methods = ['GET', 'POST'])
@check.login_required(grade=10)
def publish_query():
    K = '%s_%s' %(g.user,g.secret_key)
    Key = '%s_publish_php' %K
    Key_incr = '%s_incr' % Key
    Redis.expire(Key,30)
    if Redis.lrange(Key,0,-1):
        data = Redis.rpop(Key)
        if '_End_' in data:
            Redis.expire(Key,3)
        return render_template_string(data)
    else:
        Redis.incr(Key_incr, 1)
        if int(Redis.get(Key_incr)) >10000:
            Redis.delete(Key_incr)
            return render_template_string("_End_")
        return render_template_string("")
@page_publish_php.route('/qrcode_php/<User>/<Grade>/<project>/<project_level>')
def Qrcode(User = None,Grade = None,project=None,project_level = None):
    try:
        tw = int(time.strftime('%w', time.localtime()))
        publish_time = int(time.strftime("%H", time.localtime()))
        crypto = Md5.crypto(crypto_key)
        if User and Grade and project_level:
            db = db_op.idc_users
            User =  crypto.decrypt(User)
            project = crypto.decrypt(project)
            if db.query.filter(db.name == User).all() and int(Grade) >= 2:
                if tw in (0,6) or publish_time >= 17 or publish_time < 9:
                    verify_key = "{0}_{1}".format(User,project)
                    code = str(produce.Produce(length=6, chars=string.digits))
                    if '0' in code:
                        code.replace('0','1')
                    Redis.set(verify_key,code)
                    Redis.expire(verify_key, 900)
                    # send sms
                    mobile = PHP_Mobile
                    if int(project_level) >= 7:
                        mobile = Mobile
                    result = produce.send_sms(content='上线码:{0} 上线项目:{1} 申请人:{2} 15分钟内有效!'.format(code,project,User), mobile=mobile)
                    if isinstance(result, dict):
                        if result['code'] == 200:
                            INFO = '上线码已成功发送给PHP领导!'
                            if int(project_level) >= 7:
                                INFO = '上线码已成功发送给曾总!'
                        else:
                            INFO = '上线码发送失败!'
                    else:
                        INFO = '上线码发送失败!'
                else:
                    INFO =  "只允许在工作日17点之后或者周末全天申请!"
            else:
                INFO = "该账号无权申请上线码!"
        else:
            INFO = '非法请求信息!'
    except Exception as e:
        INFO = str(e)
    return render_template('qrcode.html',INFO=INFO)
@page_publish_php.route('/publish_php',methods = ['GET', 'POST'])
@check.login_required(grade=10)
@main_info.main_info
def publish_php():
    produce.Async_log(g.user, request.url)
    K = '%s_%s' %(g.user,g.secret_key)
    Key = '%s_publish_php' %K
    publish_key = '%s_publish_key' %K
    qrcode_url = None
    form = MyForm.MyForm_php()
    if form.submit.data:
        try:
            if Redis.exists(Key):
                raise flash('上线操作过于频繁,请稍等%s秒......' %Redis.ttl(Key))
            if form.text.data and form.changelog.data:
                action = form.selectaction.data
                Type = int(form.selecttype.data)
                Way = form.selectWay.data
                if Type == 1:
                    platfrom = '线上'
                if Type == 2:
                    platfrom = '测外'
                Tags = form.text.data.strip().splitlines()
                Gray = form.Gray.data
                code = form.code.data
                work = form.selectwork.data
                changelog = form.changelog.data
                if Way == 'SVN':
                    if len(Tags) > 1:
                        raise flash('错误:只能同时上线一个项目!')
                    else:
                        for line in Tags:
                            if line.startswith('#') or not line.split():
                                continue
                            m = re.match(r'[0-9]', line)
                            if m:
                                raise flash('错误:不能以数字开头!')
                            if not line.startswith('/'):
                                raise flash('错误:' + line + '路径必须以"/"开头!')
                            path = line.strip()
                            path = path.replace('\\', '/')
                            App = path.split('/')
                            if len(App)<4:
                                raise flash('错误:路径错误，无法获取项目名!')
                            App = App[3]
                            if len(path.split('-')) >= 2:
                                version = path.split('-')[-1]
                            else:
                                raise flash('错误:项目名称格式错误!')
                            if version.endswith('.zip'):
                                version = version.replace('.zip', '')
                elif Way == 'GIT':
                    if len(Tags) != 2:
                        raise flash('错误:GIT上线格式不对!')
                    elif not Tags[0].strip().startswith('http://'):
                        raise flash('错误:' + Tags[0] + '路径需以"http://"开头!')
                    elif not Tags[0].strip().endswith('.git'):
                        raise flash('错误:' + Tags[0] + '应该以".git"结尾!')
                    elif not Tags[1].strip().startswith('tag-'):
                        raise flash('错误:输入的tag版本号格式错误!')
                    path = ';'.join(Tags)
                    path = path.replace('http://git.baihe.com/', '/')
                    App = Tags[0].strip().split('/')[-1]
                    App = App.split('.')[0]
                    version = Tags[1].split('-')[-1]
            else:
                raise flash('错误:文本框内容不能为空!')
        except Exception as e:
            if 'old' not in str(e):
                flash(e)
        else:
            try:
                project_db = db_op.project_level
                project_level = project_db.query.with_entities(project_db.level).filter(project_db.project == App).all()
                #测外不强制项目等级
                if Type == 2:
                    if project_level:
                        project_level = int(project_level[0][0])
                    else:
                        project_level = 1
                else:
                    if project_level:
                        project_level = int(project_level[0][0])
                        crypto = Md5.crypto(crypto_key)
                        qrcode_url = "https://op.baihe.com/qrcode_php/{0}/{1}/{2}/{3}".format(crypto.encrypt(g.user),g.grade,crypto.encrypt(App),project_level)
                    else:
                        raise flash('没有找到该项目的对应项目等级!')
                publish_time = time.strftime("%H", time.localtime())
                if code:
                    verify_key = "{0}_{1}".format(g.user,App)
                    verify_code = Redis.get(verify_key)
                    if verify_code == str(code):
                        Redis.lpush(Key, '    --->verify code pass!')
                        Redis.expire(Key, 30)
                        Redis.delete(verify_key)
                        code_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                        db = db_op.publish_code
                        db_op.DB.session.add(
                            db(project=App, code=str(code), platfrom=platfrom, user=g.user, Time=code_time))
                        db_op.DB.session.commit()
                    else:
                        raise flash('%s 该上线码验证不通过!' %str(code))
                else:
                    # 用户权限及行为判断
                    tw = int(time.strftime('%w',time.localtime(time.time())))
                    if g.grade >= 2 and Type == 1 and action == 'publish':
                        if project_level >= 5:
                            raise flash('该项目等级为%s级,需申请上线码!' % project_level)
                        if tw in (2,4):
                            if project_level <= 4 and (int(publish_time) >= 17 or int(publish_time) <= 9):
                                raise flash('仅允许在10-17点时间段进行上线操作，需申请上线码!')
                        else:
                            raise flash('4级及以下常规项目只限在周二和周四上线,修复BUG需申请上线码!')
                    if g.grade >= 2 and action == 'rollback':
                        raise flash('没有权限进行回滚操作!')
                db = db_op.php_list
                if Gray:
                    if App == 'baihePhpGlobalLibrary_publish':
                        val = db.query.with_entities(db.ip).filter(and_(db.Gray == '1',db.operation == 'baihe')).limit(1).all()
                        if not val:
                            val = db.query.with_entities(db.ip).filter(and_(db.type == '%i' % Type,db.operation == 'baihe')).limit(1).all()
                    elif App == 'Baihe':
                        val = db.query.with_entities(db.ip).filter(and_(db.Gray == '1',db.operation == 'hunli')).limit(1).all()
                        if not val:
                            val = db.query.with_entities(db.ip).filter(and_(db.type == '%i' % Type,db.operation == 'hunli')).limit(1).all()
                    else:
                        val = db.query.with_entities(db.ip).filter(and_(db.Gray == '1',db.project == '%s' % App)).limit(1).all()
                        if not val:
                            val = db.query.with_entities(db.ip).filter(and_(db.project == '%s' % App, db.type == '%i' % Type)).limit(1).all()
                    if val:
                        sip = [v[0].encode('UTF-8') for v in val if v]
                        db.query.filter(and_(db.project == App, db.ip == sip[0])).update({db.Gray: '1'})
                    else:
                        raise flash('%s 没有在上线列表中找到!' % App)
                else:
                    if App == 'baihePhpGlobalLibrary_publish':
                        val = db.query.with_entities(db.ip).filter(and_(db.type == '%i' %Type,db.operation == 'baihe')).all()
                    elif App == 'Baihe':
                        val = db.query.with_entities(db.ip).filter(and_(db.type == '%i' %Type,db.operation == 'hunli')).all()
                    else:
                        val = db.query.with_entities(db.ip).filter(and_(db.project == '%s' %App,db.type == '%i' %Type)).all()
                    if val:
                        val = set(val)
                        sip = [v[0].encode('UTF-8') for v in val if v]
                        if Type == 1:
                            sip.append('172.16.4.188')
                    else:
                        raise flash('%s 没有在上线列表中找到!' %App)
                Redis.lpush(Key, 'check security policy......')
                Redis.expire(Key, 30)
                Info = {}
                Info['action'] = action
                Info['path'] = path
                Info['app'] = App
                Info['sip'] = sip
                Info['gray'] = Gray
                Info['Type'] = Type
                Info['Way'] = Way
                Redis.lpush(publish_key,Info)
                mysql_operation = Mysql.mysql_op(g.user,action,Type,App,version,Gray,work,project_level,changelog)
                mysql_operation.op_operation()
                Scheduler = produce.Scheduler_publish()
                Scheduler = Scheduler.Scheduler_mem(php_publish.php_publish,publish_key,Key)
                Scheduler.start()
                Redis.lpush(Key,'    --->check pass!')
                Redis.lpush(Key,'-'*80+'\n')
            except Exception as e:
                if 'old' not in str(e):
                    flash(e)
                if qrcode_url:
                    return render_template('php_publish.html',Main_Infos=g.main_infos, form=form, qrcode_url=qrcode_url)
            else:
                return render_template('php_publish_show.html',Main_Infos=g.main_infos)
    return render_template('php_publish.html',Main_Infos=g.main_infos,form=form,qrcode_url = qrcode_url)

@page_publish_php.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
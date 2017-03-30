#-*- coding: utf-8 -*-
import redis
from flask import Blueprint,render_template,render_template_string,g,flash,request
from Modules import check,MyForm,db_op,Mysql,produce,loging,php_publish
import re
from sqlalchemy import and_
import string
import time
import __init__
app = __init__.app
Mobile = app.config.get('MOBILE')
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
Redis = redis.StrictRedis(host=redis_host, port=redis_port)
page_publish_php = Blueprint('publish_php',__name__)
@page_publish_php.route('/publish_query',methods = ['GET', 'POST'])
@check.login_required(grade=10)
def publish_query():
    K = '%s_%s' %(g.user,g.secret_key)
    Key = '%s_publish_php' %K
    return render_template_string( Redis.rpop(Key) or "")

@page_publish_php.route('/qrcode_php/<User>/<Grade>')
def Qrcode(User = None,Grade = None):
    try:
        if User and Grade:
            if User and int(Grade) >= 2:
                verify_key = "{0}_{1}".format(User,Grade)
                code = produce.Produce(length=6, chars=string.digits)
                Redis.set(verify_key,code)
                Redis.expire(verify_key, 900)
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
                INFO =  "无需申请上线码!"
        else:
            INFO = "非法请求信息!"
    except Exception as e:
        INFO = str(e)
    return render_template('qrcode.html',INFO=INFO)
@page_publish_php.route('/publish_php',methods = ['GET', 'POST'])
@check.login_required(grade=10)
def publish_php():
    produce.Async_log(g.user, request.url)
    K = '%s_%s' %(g.user,g.secret_key)
    Key = '%s_publish_php' %K
    publish_key = '%s_publish_key' %K
    form = MyForm.MyForm_php()
    qrcode_url = "https://op.baihe.com/qrcode_php/{0}/{1}".format(g.user,g.grade)
    if form.submit.data:
        try:
            if Redis.exists(Key):
                raise flash('项目上线操作正在执行,不能并行上线操作.请稍候......')
            Redis.lpush(Key, 'check env......')
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
                grade = form.selectgrade.data
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
                pass
        else:
            try:
                publish_time = time.strftime("%H", time.localtime())
                if code:
                    verify_key = "{0}_{1}".format(g.user, g.grade)
                    verify_code = Redis.get(verify_key)
                    if verify_code == str(code):
                        Redis.lpush(Key, '    --->verify code pass!')
                        Redis.delete(verify_key)
                        code_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                        db = db_op.publish_code
                        db_op.DB.session.add(
                            db(project=App, code=str(code), platfrom=platfrom, user=g.user, Time=code_time))
                        db_op.DB.session.commit()
                    else:
                        raise flash('上线码验证错误!')
                else:
                    # 用户权限判断
                    if g.grade >= 2 and Type == 1 and int(grade) >=5:
                        raise flash('需申请验证码!')
                    if g.grade >= 2 and int(grade) <=4 and Type == 1 and (int(publish_time) >= 17 or int(publish_time) <= 9):
                        raise flash('仅允许在10-17点时间段进行自助操作，需申请验证码!')
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
                Info = {}
                Info['action'] = action
                Info['path'] = path
                Info['app'] = App
                Info['sip'] = sip
                Info['gray'] = Gray
                Info['Type'] = Type
                Info['Way'] = Way
                Redis.lpush(Key,'    --->check env pass!')
                Redis.lpush(Key,'-'*80+'\n')
                Redis.lpush(publish_key,str(Info))
                mysql_operation = Mysql.mysql_op(g.user,action,Type,App,version,Gray,work,grade,changelog)
                mysql_operation.op_operation()
                Scheduler = produce.Scheduler_publish()
                Scheduler = Scheduler.Scheduler_mem(php_publish.php_publish,publish_key,Key)
                Scheduler.start()
            except Exception as e:
                if 'old' not in str(e):
                    flash(e)
            else:
                return render_template('php_publish_show.html')
    return render_template('php_publish.html',form=form,qrcode_url = qrcode_url )

@page_publish_php.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
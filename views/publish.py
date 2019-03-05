#-*- coding: utf-8 -*-
import redis
from flask import Blueprint,render_template,render_template_string,g,flash,request,session
from Modules import check,MyForm,db_op,produce,loging,task_publish,tools,init
import time
import string
import importlib
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)
limiter = init.web_limiter()
limiter = limiter.limiter
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/sql.conf')
DB = SQLAlchemy(app)
logging = loging.Error()
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
Redis = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
page_publish = Blueprint('publish',__name__)
@page_publish.route('/publish_log/<int:flow_number>')
@check.login_required(grade=2)
def publish_log(flow_number=None):
    produce.Async_log(g.user, request.url)
    db_publish_log = db_op.publish_log
    try:
        if flow_number:
            flow_logs = db_publish_log.query.with_entities(db_publish_log.record).filter(db_publish_log.fid == int(flow_number)).all()
            if flow_logs:
                flow_logs = flow_logs[0][0].splitlines()
        else:
            flow_logs = None
    except Exception as e:
        logging.error(e)
    return render_template("publish_log.html",flow_logs = flow_logs)

@page_publish.route('/publish_query',methods = ['GET', 'POST'])
@check.login_required(grade=10)
def publish_query():
    try:
        K = '%s_%s' %(g.user,session['secret_key'])
        Msg_Key = '%s_publish_msg' %K
        Key_incr = '%s_incr' % Msg_Key
        Redis.expire(Msg_Key,30)
        if Redis.lrange(Msg_Key,0,-1):
            data = Redis.rpop(Msg_Key)
            if '_End_' in data:
                Redis.expire(Msg_Key,3)
            return render_template_string(data)
        else:
            Redis.incr(Key_incr, 1)
            if int(Redis.get(Key_incr)) >10000:
                Redis.delete(Key_incr)
                return render_template_string("_End_")
            return render_template_string("")
    except Exception as e:
        logging.error(e)

@page_publish.route('/publish',methods = ['GET', 'POST'])
@check.login_required(grade=2)
def publish():
    produce.Async_log(g.user, request.url)
    importlib.reload(MyForm)
    secret_key= tools.Produce(length=8, chars=string.digits)
    session['secret_key'] = secret_key
    K = '%s_%s' %(g.user,secret_key)
    Msg_Key = '%s_publish_msg' %K
    form = MyForm.MyForm_publish()
    if form.submit.data:
        try:
            if Redis.exists(Msg_Key):
                raise flash('上线操作过于频繁,请稍等%s秒......' %Redis.ttl(Msg_Key))
            package_url = form.package_url.data
            describe = form.describe.data
            package_md5 = form.package_md5.data
            package_type = form.package_type.data
            publish_type = form.publish_type.data
            check_url = form.check_url.data
            restart = form.restart.data
            execute = form.execute.data
            rb_project = form.project.data
            rb_version = form.version.data
            gray = form.gray.data
            if execute == 'rollback':
                if not rb_project and not rb_version:
                    raise logging.error("choice can not be empty!")
            if execute == 'publish':
                if not package_url or not package_md5 or not check_url or not describe:
                    raise logging.error("input can not be empty!")
                Package_name = package_url.split('/')[-1]
                package_name = Package_name.replace('.zip', '')
                rb_project = '-'.join(package_name.split('-')[:-1])
            INFOS = {'package_url': package_url, 'package_md5': package_md5, 'package_type': package_type,
                     'publish_type': publish_type,'user':g.user,'describe':describe.replace('"','').replace("'",''),'gray':int(gray),
                     'restart': restart, 'execute': execute, 'check_url': check_url.replace('https','http'), 'project': rb_project,
                     'version': rb_version,'channel':'web','callback_url':'None','token':'None','timestamp' :int(time.time())}
            #启动代码分发控制中心
            Scheduler = produce.Scheduler_publish()
            Scheduler = Scheduler.Scheduler_mem(task_publish.Publish_center,[INFOS,Msg_Key,K])
            Scheduler.start()
            return render_template('publish_show.html')
        except Exception as e:
            if 'old-style' not in str(e):
                logging.error(e)
    return render_template('publish.html',form=form)
@page_publish.teardown_request
def db_remove(exception):
    db_op.DB.session.remove()
#-*- coding: utf-8 -*-
import redis
from flask import Flask,Blueprint,render_template,render_template_string,g,flash,request,redirect,url_for
from module import user_auth,MyForm,db_op,loging,task_publish,tools,produce
import time
import conf
import string
import importlib
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/redis.conf')
limiter = conf.WebLimiter()
limiter = limiter.limiter
logging = loging.Error()
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
Redis = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
page_publish = Blueprint('publish',__name__)
@page_publish.route('/publish_log/<int:flow_number>')
@user_auth.login_required(grade=2)
def publish_log(flow_number=None):
    tools.Async_log(g.user, request.url)
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
        return redirect(url_for('error'))
    return render_template("publish_log.html",flow_logs = flow_logs)

@page_publish.route('/publish_query/<secret_key>',methods = ['GET', 'POST'])
@user_auth.login_required(grade=10)
def publish_query(secret_key=None):
    try:
        Msg_Key = 'op_publish_msg_%s' %secret_key
        Key_incr = '%s_incr' % Msg_Key
        Redis.expire(Msg_Key,30)
        if Redis.lrange(Msg_Key,0,-1):
            data = Redis.rpop(Msg_Key)
            if '_End_' in str(data):
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
        return render_template_string(e)

@page_publish.route('/publish',methods = ['GET', 'POST'])
@user_auth.login_required(grade=2)
def publish():
    try:
        tools.Async_log(g.user, request.url)
        importlib.reload(MyForm)
        secret_key= tools.Produce(length=12, chars=string.digits)
        Msg_Key = 'op_publish_msg_%s' %secret_key
        form = MyForm.MyFormPublish()
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
                Scheduler = produce.SchedulerPublish()
                Scheduler = Scheduler.Scheduler_mem(task_publish.Publish_center,[INFOS,Msg_Key,secret_key])
                Scheduler.start()
                return render_template('publish_show.html',secret_key=secret_key)
            except Exception as e:
                if 'old-style' not in str(e):
                    logging.error(e)
    except Exception as e:
        logging.error(e)
        return redirect(url_for('error'))
    return render_template('publish.html',form=form)
@page_publish.teardown_request
def db_remove(exception):
    db_op.DB.session.remove()
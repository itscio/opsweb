#-*- coding: utf-8 -*-
from flask import Blueprint,render_template,g,request,flash,render_template_string,session
from Modules import check,loging,produce,tools,MyForm,k8s_resource,db_op
from flask import Flask
import time
from sqlalchemy import desc
from flask_sqlalchemy import SQLAlchemy
import os
from importlib import reload
import redis
app = Flask(__name__)
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/docker.conf')
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
dockerfile_path = app.config.get('DOCKERFILE_PATH')
docker_registry = app.config.get('REGISTRY')
Redis = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
logging = loging.Error()
DB = SQLAlchemy(app)
config,contexts,config_file = tools.k8s_conf()
config.load_kube_config(config_file, context=contexts[0])
page_k8s_deploy = Blueprint('k8s_deploy',__name__)
db_k8s = db_op.k8s_deploy
@page_k8s_deploy.route('/deploy_query/<redis_key>')
@check.login_required(grade=10)
def deploy_query(redis_key = None):
    try:
        Key_incr = '%s_incr' % redis_key
        Redis.expire(redis_key,30)
        if Redis.lrange(redis_key,0,-1):
            data = Redis.rpop(redis_key)
            if '_End_' in data:
                Redis.expire(redis_key,3)
            return render_template_string(data)
        else:
            Redis.incr(Key_incr, 1)
            if int(Redis.get(Key_incr)) >10000:
                Redis.delete(Key_incr)
                return render_template_string("_End_")
            return render_template_string("")
    except Exception as e:
        logging.error(e)

@page_k8s_deploy.route('/deployment_create',methods = ['GET','POST'])
@check.login_required(grade=2)
def deployment_create():
    produce.Async_log(g.user, request.url)
    reload(MyForm)
    form = MyForm.Form_k8s_deploy()
    if form.submit.data:
        project = form.projects.data
        version = form.version.data
        object = form.object.data
        container_port = form.container_port.data
        ingress_port = form.ingress_port.data
        replicas = form.replicas.data
        request_cpu = form.request_cpu.data
        limit_cpu = form.limit_cpu.data
        request_mem = form.request_mem.data
        limit_mem = form.limit_mem.data
        domain = form.domain.data
        re_requests = {}
        re_limits = {}
        try:
            if object and version and  container_port and replicas:
                if object.endswith('.war') or object.endswith('.jar'):
                    dm_name = object.split('.')[0]
                    image = "%s/%s:%s" %(docker_registry,dm_name,version)
                    docker_file = "%s/%s" %(dockerfile_path,dm_name)
                    if os.path.exists(docker_file):
                        container_port = [int(port) for port in container_port.split(',')]
                        if request_cpu and limit_cpu and request_mem and limit_mem:
                            if float(request_cpu) > float(limit_cpu) or float(request_mem) > float(limit_mem):
                                raise flash('限制资源不能小于请求资源!')
                            else:
                                re_requests = {'cpu': request_cpu, 'memory':'%sG' %request_mem}
                                re_limits = {'cpu': limit_cpu, 'memory':'%sG' %limit_mem}
                        if ingress_port:
                            if int(ingress_port) not in [int(port) for port in container_port]:
                                raise flash('对外服务端口必须是服务端口其中之一!')
                        redis_key = 'op_k8s_create_%s' % time.strftime('%Y%m%d%H%M%S', time.localtime())
                        session['redis_key'] = redis_key
                        Scheduler = produce.Scheduler_publish()
                        Scheduler = Scheduler.Scheduler_mem(k8s_resource.object_deploy, [project,dm_name,version, image,
                                                                                         container_port, ingress_port,replicas,
                                                                                         domain,re_requests, re_limits,redis_key])
                        Scheduler.start()
                        return render_template('deploy_show.html')
                    else:
                        flash("%s文件路径不存在!" %docker_file)
                else:
                    flash("%s包名应以.war或者.jar结尾!" %object)
            else:
                flash('必填项参数不完整!')
            return render_template('Message.html')
        except Exception as e:
            logging.error(e)
    return render_template('k8s_deploy.html',form=form)

@page_k8s_deploy.route('/image_update',methods = ['GET','POST'])
@check.login_required(grade=2)
def image_update():
    try:
        produce.Async_log(g.user, request.url)
        reload(MyForm)
        form = MyForm.Form_k8s_update()
        if form.submit.data:
            deployment = form.deployment.data
            version = form.version.data
            if version:
                new_image = "%s/%s:%s" %(docker_registry,deployment,version)
                new_replicas = form.replicas.data
                redis_key = 'op_k8s_update_%s' % time.strftime('%Y%m%d%H%M%S', time.localtime())
                session['redis_key'] = redis_key
                Scheduler = produce.Scheduler_publish()
                Scheduler = Scheduler.Scheduler_mem(k8s_resource.object_update, [new_image, new_replicas,version, redis_key])
                Scheduler.start()
                return render_template('deploy_show.html')
    except Exception as e:
        logging.error(e)
    return render_template('k8s_update.html',form=form)

@page_k8s_deploy.route('/deployment_delete',methods = ['GET','POST'])
@check.login_required(grade=2)
def deployment_delete():
    try:
        produce.Async_log(g.user, request.url)
        # Delete deployment
        dm_name = "weatherv3"
        values = db_k8s.query.with_entities(db_k8s.project, db_k8s.image, db_k8s.container_port, db_k8s.replicas,
                                            db_k8s.re_requests,db_k8s.re_limits).filter(db_k8s.deployment==dm_name).order_by(desc(db_k8s.id)).limit(1).all()
        if values:
            project, image, container_port, replicas,re_requests,re_limits = values[0]
            k8s = k8s_resource.k8s_object(dm_name, image, container_port, replicas, re_requests, re_limits)
            if k8s.delete_deployment():
                v = db_k8s(project=project, image=image, container_port=container_port, replicas=replicas, re_requests=re_requests,
                           re_limits=re_limits, action='delete',
                           update_date=time.strftime('%Y-%m-%d', time.localtime()),
                           update_time=time.strftime('%H:%M:%S', time.localtime()))
                db_op.DB.session.add(v)
                db_op.DB.session.commit()
    except Exception as e:
        logging.error(e)
    finally:
        return render_template('Message.html')

@page_k8s_deploy.teardown_request
def db_remove(exception):
    db_op.DB.session.remove()
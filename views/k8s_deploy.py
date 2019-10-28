#-*- coding: utf-8 -*-
from flask import Flask,Blueprint,render_template,g,request,flash,render_template_string,url_for,redirect
from module import user_auth,loging,tools,MyForm,k8s_resource,db_op,produce
import time
from flask_sqlalchemy import SQLAlchemy
import os
from kubernetes import client
from importlib import reload
import redis
from sqlalchemy import distinct,and_
from collections import defaultdict
app = Flask(__name__)
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/git.conf')
app.config.from_pyfile('../conf/docker.conf')
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
dockerfile_path = app.config.get('DOCKERFILE_PATH')
docker_registry = app.config.get('REGISTRY')
Redis = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
logging = loging.Error()
config,contexts,config_file = tools.k8s_conf()
config.load_kube_config(config_file, context=contexts[0])
page_k8s_deploy = Blueprint('k8s_deploy',__name__)
config,contexts,config_file = tools.k8s_conf()
namespace = "default"
@page_k8s_deploy.route('/deploy_query/<redis_key>')
@user_auth.login_required(grade=10)
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
        return redirect(url_for('error'))

@page_k8s_deploy.route('/deployment_create',methods = ['GET','POST'])
@user_auth.login_required(grade=1)
def deployment_create():
    tools.Async_log(g.user, request.url)
    reload(MyForm)
    form = MyForm.FormK8sDeploy()
    mounts = defaultdict()
    labels = defaultdict()
    if form.submit.data:
        context = form.contexts.data
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
        healthcheck = form.healthcheck.data
        label_project=form.label_project.data
        label_deploy = form.label_deploy.data
        mount_path = form.mount_path.data
        mount_name = form.mount_name.data
        sidecar = form.sidecar.data
        docker_args = form.docker_args.data
        if docker_args:
            docker_args = docker_args.splitlines()
        run_args = form.run_args.data
        run_args = run_args.splitlines()
        re_requests = {'cpu': 1, 'memory':'2G'}
        re_limits = {'cpu': 2, 'memory':'4G'}
        if mount_path:
            mounts[mount_path] = mount_name
        if label_project:
            labels['project'] = label_project
        if label_project:
            labels['deploy'] = label_deploy
        try:
            if object and version  and replicas:
                if object.endswith('.war') or object.endswith('.tar.gz') or object.endswith('.jar'):
                    dm_name = object.split('.')[0]
                    image = "%s/%s:%s" %(docker_registry[context],dm_name,version)
                    docker_file = "%s/%s" %(dockerfile_path,dm_name)
                    if not os.path.exists(docker_file):
                        os.makedirs(docker_file)
                    if container_port:
                        container_port = [int(port) for port in container_port.split(',')]
                    if request_cpu and limit_cpu and request_mem and limit_mem:
                        if float(request_cpu) > float(limit_cpu) or float(request_mem) > float(limit_mem):
                            raise flash('限制资源不能小于请求资源!')
                        else:
                            re_requests = {'cpu': request_cpu, 'memory':'%sG' %request_mem}
                            re_limits = {'cpu': limit_cpu, 'memory':'%sG' %limit_mem}
                    if domain and not ingress_port:
                        raise flash('域名配置后还需配置容器对外服务端口!')
                    redis_key = 'op_k8s_create_%s' % time.strftime('%Y%m%d%H%M%S', time.localtime())
                    Scheduler = produce.SchedulerPublish()
                    Scheduler = Scheduler.Scheduler_mem(k8s_resource.object_deploy, [context,project,object,version, image,
                                                                                     docker_args,run_args,container_port,
                                                                                     ingress_port,replicas,
                                                                                     domain,re_requests,mounts,labels,
                                                                                     healthcheck,sidecar,re_limits,
                                                                                     redis_key])
                    Scheduler.start()
                    return render_template('deploy_show.html',redis_key=redis_key)
                else:
                    flash("%s包名应以.war或者.tar.gz结尾或者.jar结尾!" %object)
            else:
                flash('必填项参数不完整!')
            return render_template('Message.html')
        except Exception as e:
            logging.error(e)
            return redirect(url_for('error'))
    return render_template('k8s_deploy.html',form=form)

@page_k8s_deploy.route('/image_update',methods = ['GET','POST'])
@user_auth.login_required(grade=6)
def image_update():
    try:
        tools.Async_log(g.user, request.url)
        reload(MyForm)
        form = MyForm.FormK8sUpdate()
        db_deploy = db_op.k8s_deploy
        rollback = False
        if form.submit.data:
            deployment = form.deployment.data
            version = form.version.data
            context = form.contexts.data
            action = form.action.data
            if version:
                image = "%s/%s:%s" % (docker_registry[context], deployment, version)
                if action =='rollback':
                    rollback = True
                    val = db_deploy.query.filter(db_deploy.image==image).all()
                    if not val:
                        flash('%s版本镜像不存在!' %version)
                        return render_template('Message.html')
                redis_key = 'op_k8s_update_%s' % time.strftime('%Y%m%d%H%M%S', time.localtime())
                Scheduler = produce.SchedulerPublish()
                Scheduler = Scheduler.Scheduler_mem(k8s_resource.object_update, [context,image,version,rollback,redis_key,'web'])
                Scheduler.start()
                return render_template('deploy_show.html',redis_key=redis_key)
    except Exception as e:
        logging.error(e)
        return redirect(url_for('error'))
    return render_template('k8s_update.html',form=form)

@page_k8s_deploy.route('/hpa_apply',methods = ['GET','POST'])
@user_auth.login_required(grade=1)
def hpa_apply():
    try:
        reload(MyForm)
        form = MyForm.FormK8sHpa()
        if form.submit.data:
            context = form.contexts.data
            deployment = form.deployment.data
            max_replica = form.max_replica.data
            min_replica = form.min_replica.data
            cpu_value = form.cpu_value.data
            if max_replica and min_replica and cpu_value:
                exist_hpa = []
                config.load_kube_config(config_file,context)
                api_instance = client.AutoscalingV1Api()
                try:
                    ret = api_instance.list_horizontal_pod_autoscaler_for_all_namespaces()
                    for i in ret.items:
                        exist_hpa.append(i.spec.scale_target_ref.name)
                    if deployment in exist_hpa:
                        #配置已存在进行更新
                        api_instance.patch_namespaced_horizontal_pod_autoscaler(
                            name='%s-hpa'%deployment, namespace=namespace,
                            body=client.V1HorizontalPodAutoscaler(
                            spec=client.V1HorizontalPodAutoscalerSpec(
                                max_replicas=int(max_replica),
                                min_replicas=int(min_replica),
                                target_cpu_utilization_percentage=int(cpu_value),
                                scale_target_ref=client.V1CrossVersionObjectReference(
                                    api_version='extensions/v1beta1',
                                    kind='Deployment',
                                    name=deployment))
                            ))
                    else:
                        # 配置不存在进行创建
                        api_instance.create_namespaced_horizontal_pod_autoscaler(
                            namespace=namespace,
                            body=client.V1HorizontalPodAutoscaler(
                                metadata=client.V1ObjectMeta(
                                    name='%s-hpa'%deployment,
                                    namespace=namespace),
                            spec=client.V1HorizontalPodAutoscalerSpec(
                                max_replicas=int(max_replica),
                                min_replicas=int(min_replica),
                                target_cpu_utilization_percentage=int(cpu_value),
                                scale_target_ref=client.V1CrossVersionObjectReference(
                                    api_version='extensions/v1beta1',
                                    kind='Deployment',
                                    name=deployment))
                            ))
                    return redirect(url_for('k8s.hpa'))
                except Exception as e:
                    logging.error(e)
    except Exception as e:
        logging.error(e)
        return redirect(url_for('error'))
    return render_template('k8s_hpa.html', form=form)

@page_k8s_deploy.route('/ingress_apply',methods = ['GET','POST'])
@user_auth.login_required(grade=1)
def ingress_apply():
    form = MyForm.FormK8sIngress()
    namespace = "default"
    msg = None
    if form.submit.data:
        try:
            domains = form.domains.data
            ingress_port = form.service_port.data
            service_name = form.service_name.data
            context = form.contexts.data
            db_ingress = db_op.k8s_ingress
            config.load_kube_config(config_file,context)
            api_instance = client.ExtensionsV1beta1Api()
            domains = [domain.strip() for domain in domains.splitlines() if domain]
            try:
                # ingress信息写入数据库
                for ingress_domain in domains:
                    path = None
                    if '/' in ingress_domain:
                        ingress_domain = ingress_domain.split('/')[0]
                        path = '/{}'.format('/'.join(ingress_domain.split('/')[1:]))
                    v = db_ingress(name='nginx-ingress', context=context,namespace=namespace, domain=ingress_domain, path=path,
                                   serviceName=service_name, servicePort=int(ingress_port))
                    db_op.DB.session.add(v)
                    db_op.DB.session.commit()
            except Exception as e:
                logging.error(e)
            else:
                # 从数据库读取ingress信息
                Rules = []
                domain_infos = db_ingress.query.with_entities(distinct(db_ingress.domain)).all()
                domain_infos = [ domain[0] for domain in domain_infos]
                for domain in domain_infos:
                    paths = []
                    Rules_infos = db_ingress.query.with_entities(db_ingress.path,
                                                                 db_ingress.serviceName, db_ingress.servicePort
                                                                 ).filter(and_(db_ingress.domain == domain,
                                                                               db_ingress.context==context)).all()
                    for infos in Rules_infos:
                        path, serviceName, servicePort = infos
                        if path:
                            paths.append(client.V1beta1HTTPIngressPath(client.V1beta1IngressBackend(
                                service_name=serviceName,
                                service_port=int(servicePort)
                            ), path=path))
                    if paths:
                        Rules.append(client.V1beta1IngressRule(host=domain,
                                                               http=client.V1beta1HTTPIngressRuleValue(
                                                                   paths=paths)))
                    else:
                        path, serviceName, servicePort = Rules_infos[0]
                        Rules.append(client.V1beta1IngressRule(host=domain,
                                                               http=client.V1beta1HTTPIngressRuleValue(
                                                                   paths=[client.V1beta1HTTPIngressPath(
                                                                       client.V1beta1IngressBackend(
                                                                           service_name=serviceName,
                                                                           service_port=int(servicePort)
                                                                       ))])
                                                               ))
                spec = client.V1beta1IngressSpec(rules=Rules)
                ingress = client.V1beta1Ingress(
                    api_version='extensions/v1beta1',
                    kind='Ingress',
                    metadata=client.V1ObjectMeta(name='nginx-ingress',
                                                 namespace=namespace,
                                                 annotations={'kubernetes.io/ingress.class': 'nginx'}),spec=spec)
                api_instance.patch_namespaced_ingress(body=ingress, namespace=namespace,name='nginx-ingress')
        except Exception as e:
            logging.error(e)
            msg = 'ingress配置失败!'
        else:
            msg = 'ingress配置完成!'
        finally:
            db_op.DB.session.remove()
    return render_template('k8s_ingress.html',form=form,msg=msg)

@page_k8s_deploy.route('/k8s_project_delete')
@user_auth.login_required(grade=1)
def k8s_project_delete():
    return render_template('ajax_content.html',url = url_for('k8s_manage.k8s_project_offline'))

@page_k8s_deploy.teardown_request
def db_remove(exception):
    db_op.DB.session.remove()
#-*- coding: utf-8 -*-
from flask import Flask,Blueprint,g,request,jsonify,render_template,redirect,url_for
from module import user_auth,loging,tools,db_idc,db_op,k8s_resource
from kubernetes import client
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import distinct,desc,and_
import redis
from collections import defaultdict
app = Flask(__name__)
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/redis.conf')
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
RC = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
logging = loging.Error()
config,contexts,config_file = tools.k8s_conf()
page_k8s_manage = Blueprint('k8s_manage',__name__)
db_k8s = db_op.k8s_deploy
namespace = "default"
@page_k8s_manage.route('/pod_manage/<pod>/<namespace>/<action>')
def pod_manage(pod = None,namespace=None,action=None):
    try:
        if pod:
            if action == 'delete':
                api_instance = client.CoreV1Api()
                api_instance.delete_namespaced_pod(name=pod,
                                                   namespace=namespace,
                                                   body=client.V1DeleteOptions())
                return jsonify({'status':'ok','infos':'%s %s 成功!' %(pod,action)})
        return jsonify({'status':'fail','infos':'操作失败!'})
    except Exception as e:
        logging.error(e)
        return redirect(url_for('error'))
@page_k8s_manage.route('/modify_k8s_hpa', methods=['POST','DELETE'])
def modify_k8s_hpa():
    infos = None
    status = None
    try:
        Infos = request.get_json()
        api_instance = client.AutoscalingV1Api()
        if request.method == 'POST':
            try:
                api_instance.patch_namespaced_horizontal_pod_autoscaler(name=Infos['name'], namespace=namespace,
                                                                          body=client.V1HorizontalPodAutoscaler(
                                                                              spec=client.V1HorizontalPodAutoscalerSpec(
                                                                                  max_replicas=int(Infos['max_update']),
                                                                                  target_cpu_utilization_percentage=int(Infos['cpu_update'].replace('%','')),
                                                                                  scale_target_ref=client.V1CrossVersionObjectReference(
                                                                                      kind='Deployment',
                                                                                      name=Infos['target_ref']))))
            except Exception as e:
                logging.error(e)
                infos = '修改参数失败!'
            else:
                status = 'ok'
                infos = '修改参数成功!'
        if request.method == 'DELETE':
            try:
                api_instance.delete_namespaced_horizontal_pod_autoscaler(name=Infos['name'], namespace=namespace,body=client.V1DeleteOptions())
            except Exception as e:
                logging.error(e)
                infos = '删除%s失败!' %Infos['name']
            else:
                status = 'ok'
                infos = '删除%s成功!' %Infos['name']
    except Exception as e:
        logging.error(e)
    finally:
        return jsonify({'status':status,'infos':infos})

@page_k8s_manage.route('/k8s_project_offline')
@page_k8s_manage.route('/k8s_project_offline/<context>/<dm_name>/<offline>')
def k8s_project_offline(context=None,dm_name=None,offline=None):
    try:
        tools.Async_log(g.user, request.url)
        busi_data = defaultdict()
        mounts = None
        labels = None
        healthcheck = None
        sidecar = None
        tables = ('项目', '业务','集群', '代码包', '最近上线日期', '最近上线时间', '操作')
        # offline project
        if dm_name and context and offline:
            values = db_k8s.query.with_entities(db_k8s.project, db_k8s.image, db_k8s.container_port, db_k8s.replicas,
                                                db_k8s.re_requests,db_k8s.re_limits).filter(db_k8s.deployment==dm_name).order_by(desc(db_k8s.id)).limit(1).all()
            if values:
                id,project, image, container_port, replicas,re_requests,re_limits = values[0]

                k8s = k8s_resource.k8s_object(context,dm_name, image, container_port, replicas,mounts,labels,healthcheck,sidecar, re_requests, re_limits)
                if k8s.delete_hpa() and k8s.delete_ingress() and k8s.delete_service() and k8s.delete_deployment():
                    db_k8s.query.filter(db_k8s.deployment==dm_name).update({db_k8s.action:'delete'})
                    db_op.DB.session.commit()
                    return jsonify({'result': 'offline project %s success!' % dm_name})
            return jsonify({'result':'offline project %s fail!' %dm_name})
        db_k8s_deploy = db_op.k8s_deploy
        db_project = db_op.project_list
        db_business = db_op.business
        projects = db_k8s_deploy.query.with_entities(distinct(db_k8s_deploy.deployment)).all()
        projects = [project[0] for project in projects]
        dm_names = []
        for context in contexts:
            config.load_kube_config(config_file,context)
            v1 = client.AppsV1Api()
            ret = v1.list_deployment_for_all_namespaces()
            names = [[i.metadata.name] for i in ret.items if i.metadata.name in projects]
            dm_names.extend(names)
            for dm_name in names:
                vals = db_k8s_deploy.query.with_entities(db_k8s_deploy.project,db_k8s_deploy.context,db_k8s_deploy.war,db_k8s_deploy.update_date,
                                                         db_k8s_deploy.update_time).filter(and_(db_k8s_deploy.deployment==dm_name[0],
                                                                                                db_k8s_deploy.context==context)
                                                                                           ).order_by(desc(db_k8s_deploy.id)).all()
                if vals:
                    dm_name.extend(vals[0])
                    vals = db_project.query.with_entities(db_project.business_id).filter(db_project.project == vals[0][0]).limit(1).all()
                    if vals:
                        business = db_business.query.with_entities(db_business.business).filter(db_business.id==vals[0][0]).all()
                        if business:
                            dm_name[1] = business[0][0]
                            busi_data[business[0][0]] = vals[0][0]
        return render_template('k8s_offline.html',dm_names=dm_names,tables=tables,busi_data=busi_data)
    except Exception as e:
        logging.error(e)
        return redirect(url_for('error'))

@page_k8s_manage.before_request
@user_auth.login_required(grade=1)
def check_login(error=None):
    tools.Async_log(g.user, request.url)

@page_k8s_manage.teardown_request
def db_remove(error=None):
    db_idc.DB.session.remove()
    db_op.DB.session.remove()
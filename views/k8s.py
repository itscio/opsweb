#-*- coding: utf-8 -*-
from flask import Blueprint,render_template,g,request,make_response
from module import user_auth,loging,tools,MyForm,db_idc,db_op
from flask import Flask
from kubernetes import client
from collections import defaultdict
from flask_sqlalchemy import SQLAlchemy
import time,datetime
from tcpping import tcpping
import redis
from functools import reduce
from pyecharts import Line
from importlib import reload
from sqlalchemy import desc,and_
app = Flask(__name__)
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/sql.conf')
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
RC = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
logging = loging.Error()
config,contexts,config_file = tools.k8s_conf()
page_k8s = Blueprint('k8s',__name__)
@page_k8s.route('/k8s/pods')
def pods():
    valus = defaultdict()
    v1 = client.CoreV1Api()
    namespace = []
    image = []
    phases = []
    tables = ('POD_NAME','创建日期', 'POD_IP', 'POD_PORTS', 'namespace', 'containers', 'NODE', '镜像地址','状态','管理')
    keys = ('start_time','pod_ip','ports', 'namespace', 'container', 'node_name','image','phase')
    ret = v1.list_pod_for_all_namespaces()
    for i in ret.items:
        phase = 'unknown'
        pod_ports = 'None'
        try:
            podports = []
            if i.spec.containers[0].ports:
                for ports in i.spec.containers:
                    if ports.ports:
                        for port in ports.ports:
                            podports.append(str(port.container_port))
            if podports:
                pod_ports = ','.join(podports)

        except Exception as e:
            logging.error(e)
        try:
            if i.status.container_statuses:
                if i.status.container_statuses[-1].state.running:
                    phase = 'Running'
                else:
                    if i.status.container_statuses[-1].state.waiting:
                        phase = i.status.container_statuses[-1].state.waiting.reason
        except Exception as e:
            logging.error(e)
        start_time = i.status.start_time
        try:
            start_time = start_time + datetime.timedelta(hours=8)
            start_time = start_time.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            logging.error(e)
        try:
            valus[i.metadata.name] = {'pod_ip':i.status.pod_ip,
                                    'namespace':i.metadata.namespace,
                                    'node_name':i.spec.node_name,
                                     'container':len(i.spec.containers),
                                    'image':';'.join([images.image for images in i.spec.containers]),
                                    'phase':phase,
                                    'ports':pod_ports,
                                    'start_time':start_time
                                    }
        except Exception as e:
            logging.error(e)
        try:
            namespace.append(i.spec.node_name)
            for images in i.spec.containers:
                image.append(images.image)
            phases.append(phase)
        except Exception as e:
            logging.error(e)
    counts = [len(valus),len(set(namespace)),len(set(image)),float('%.2f' %((float(phases.count('Running'))/len(valus))*100))]
    return render_template('k8s-resource.html', valus=valus, tables=tables, keys=keys, counts=counts, resource='Pods')

@page_k8s.route('/k8s/deployment')
def deployment():
    try:
        valus = defaultdict()
        v1 = client.AppsV1Api()
        tables = ('name','namespace', 'replicas', 'strategy', 'containers','cpu_limit','mem_limit','available')
        keys  = ('namespace', 'replicas', 'strategy', 'containers','cpu_limit','mem_limit','available')
        ret = v1.list_deployment_for_all_namespaces()
        for i in ret.items:
            try:
                containers = []
                for info in i.spec.template.spec.containers:
                    containers.append(info.name)
                if not i.status.unavailable_replicas:
                    available = 100
                else:
                    available = int((float(i.spec.replicas)-float(i.status.unavailable_replicas))/float(i.spec.replicas)*100)
                cpu_limit = 'None'
                mem_limit = 'None'
                limits = i.spec.template.spec.containers[0].resources.limits
                if limits:
                    if 'cpu' in limits:
                        cpu_limit = limits['cpu']
                    if 'memory' in limits:
                        mem_limit = limits['memory']
                valus[i.metadata.name]={
                    'namespace':i.metadata.namespace,
                    'replicas':i.spec.replicas,
                    'strategy':i.spec.strategy.type,
                    'containers':containers,
                    'cpu_limit':cpu_limit,
                    'mem_limit':mem_limit,
                    'available':available
                }

            except Exception as e:
                logging.error(e)
        return render_template('k8s-resource.html', valus=valus, tables=tables, keys=keys, resource='Deployment')
    except Exception as e:
        logging.error(e)

@page_k8s.route('/k8s/daemonset')
def daemonset():
    try:
        valus = defaultdict()
        v1 = client.AppsV1Api()
        tables = ('name','namespace', 'images', 'mount_path', 'cpu_limit','mem_limit','number_ready')
        keys  = ('namespace', 'images', 'mount_path', 'cpu_limit','mem_limit','number_ready')
        ret = v1.list_daemon_set_for_all_namespaces()
        for i in ret.items:
            try:
                mount_path = []
                for path in i.spec.template.spec.containers[0].volume_mounts:
                    mount_path.append(path.mount_path)
                number_ready = i.status.number_ready
                if number_ready == 0:
                    number_ready = 1
                cpu_limit = 'None'
                mem_limit = 'None'
                limits = i.spec.template.spec.containers[0].resources.limits
                if limits:
                    if 'cpu' in limits:
                        cpu_limit = limits['cpu']
                    if 'memory' in limits:
                        mem_limit = limits['memory']
                valus[i.metadata.name]={
                    'namespace':i.metadata.namespace,
                    'images':i.spec.template.spec.containers[0].image,
                    'mount_path':mount_path,
                    'cpu_limit':cpu_limit,
                    'mem_limit':mem_limit,
                    'number_ready': number_ready
                }
            except Exception as e:
                logging.error(e)
        return render_template('k8s-resource.html', valus=valus, tables=tables, keys=keys, resource='Daemonset')
    except Exception as e:
        logging.error(e)

@page_k8s.route('/k8s/service')
def service():
    try:
        valus = defaultdict()
        v1 = client.CoreV1Api()
        tables = ('name','namespace', 'cluster_ip', 'port', 'target_port','node_port','selector')
        keys = ('namespace', 'cluster_ip', 'port', 'target_port', 'node_port', 'selector')
        ret = v1.list_service_for_all_namespaces()
        for i in ret.items:
            try:
                node_port = []
                port = []
                target_port = []
                for info in i.spec.ports:
                    node_port.append(str(info.node_port))
                    port.append(str(info.port))
                    target_port.append(str(info.target_port))
                valus[i.metadata.name]={
                    'namespace':i.metadata.namespace,
                    'cluster_ip':i.spec.cluster_ip,
                    'node_port':','.join(set(node_port)),
                    'port': ','.join(set(port)),
                    'target_port': ','.join(set(target_port)),
                    'selector': i.spec.selector
                }
            except Exception as e:
                logging.error(e)
        return render_template('k8s-resource.html', valus=valus, tables=tables, keys=keys, resource='Service')
    except Exception as e:
        logging.error(e)

@page_k8s.route('/k8s/ingress')
def ingress():
    try:
        valus = []
        v1 = client.ExtensionsV1beta1Api()
        keys = tables = ('name','request','domain', 'service_name', 'service_port')
        ret = v1.list_ingress_for_all_namespaces()
        for i in ret.items:
            try:
                for rule in i.spec.rules:
                    valus.append([i.metadata.name,
                                  'http',
                                  rule.host,
                                  rule.http.paths[0].backend.service_name,
                                  rule.http.paths[0].backend.service_port
                                  ])
            except Exception as e:
                logging.error(e)
        return render_template('k8s-resource.html', valus=valus, tables=tables, keys=keys, resource='Ingress')
    except Exception as e:
        logging.error(e)

@page_k8s.route('/k8s/hpa')
def hpa():
    try:
        reload(MyForm)
        form = MyForm.FormData()
        td = time.strftime('%Y-%m-%d',time.localtime())
        if 'select_date' in request.cookies:
            td = request.cookies['select_date']
        valus = []
        line = None
        db_k8s_deploy = db_op.k8s_deploy
        db_project = db_op.project_list
        Key = 'op_k8s_ingress_log'
        keys = tables = ('name','deployment','最大副本','最小副本', '当前副本', 'CPU阀值','CPU当前值','QPS当前值','管理')
        config.load_kube_config(config_file, g.context)
        v1 = client.AutoscalingV1Api()
        ret = v1.list_horizontal_pod_autoscaler_for_all_namespaces()
        for i in ret.items:
            rps = 0
            RPS = []
            try:
                project = db_k8s_deploy.query.with_entities(db_k8s_deploy.project).filter(and_(
                    db_k8s_deploy.deployment==i.spec.scale_target_ref.name,db_k8s_deploy.context==g.context)).limit(1).all()
                if project:
                    domains = db_project.query.with_entities(db_project.domain).filter(db_project.project==project[0][0]).limit(1).all()
                    if domains:
                        domains = [domain[0] for domain in domains if domain]
                        if domains[0]:
                            for domain in domains[0].split(','):
                                vals = RC.hgetall('%s_%s_%s' % (Key, domain, td))
                                vals = sorted(vals.items(), key=lambda item: item[0])
                                if vals:
                                    RPS.append(int(int(vals[-1][-1])/60))
                            if RPS:
                                rps = RPS[0]
                                if len(RPS) >1:
                                    rps = reduce(lambda x,y:x+y,RPS)
            except Exception as e:
                logging.error(e)
            try:
                valus.append([i.metadata.name,
                             i.spec.scale_target_ref.name,
                             i.spec.max_replicas,
                             i.spec.min_replicas,
                             i.status.current_replicas,
                             '{0}%'.format(i.spec.target_cpu_utilization_percentage),
                             '{0}%'.format(i.status.current_cpu_utilization_percentage),
                              rps]
                             )
            except Exception as e:
                logging.error(e)
        if valus:
            Key = 'op_hpa_chart_%s_%s' % (g.context,td)
            infos = RC.hgetall(Key)
            infos = sorted(infos.items(), key=lambda item: item[0].split('_')[-1])
            line = Line('HPA动态伸缩实时状态', width='110%', height='250px', title_pos='8%', title_text_size=14)
            for project in valus:
                attr = []
                vals = []
                for info in infos:
                    if project[0] in info[0]:
                        attr.append(str(info[0].split('_')[-1]))
                        vals.append(int(info[1]))
                if attr and vals:
                    line.add(project[0], attr, vals, is_toolbox_show=False, is_smooth=True, mark_point=["max", "min"],
                          mark_point_symbolsize=60,legend_pos='20%',is_datazoom_show=True, datazoom_range=[v for v in range(100, 10)],
                                     datazoom_type='both',)
        return render_template('k8s-resource.html', valus=valus, tables=tables, keys=keys, line=line,form=form,resource='HPA')
    except Exception as e:
        logging.error(e)

@page_k8s.route('/k8s/nodes')
@page_k8s.route('/k8s/nodes/<context>')
def nodes(context=None):
    NODES = defaultdict()
    try:
        if context:
            g.context = context
            config.load_kube_config(config_file, context)
        v1 = client.CoreV1Api()
        ret = v1.list_node(watch=False)
        tables = ('节点','角色','flannel','CPU','CPU使用率','内存','内存使用率','硬盘','标签','版本','状态')
        keys = ('node_type','flannel','cpu','cpu_load','memory','mem_used','storage','lables','version','status')
        db_zabbix = db_idc.zabbix_info
        for i in ret.items:
            if 'node-role.kubernetes.io/master' in i.metadata.labels:
                node_type = 'master'
            else:
                node_type = 'node'
            flannel = '-'
            cpu_load = '-'
            mem_used = '-'
            if 'flannel.alpha.coreos.com/backend-type' in i.metadata.annotations:
                flannel = i.metadata.annotations['flannel.alpha.coreos.com/backend-type']
            values = db_zabbix.query.with_entities(db_zabbix.cpu_load,db_zabbix.mem_use).filter(db_zabbix.hostname==i.metadata.name).all()
            if values:
                cpu_load,mem_used = values[0]
            labels = {key:i.metadata.labels[key] for key in i.metadata.labels if key not in ('beta.kubernetes.io/arch',
                                                                                             'beta.kubernetes.io/os',
                                                                                             'kubernetes.io/hostname',
                                                                                             'node-role.kubernetes.io/master')}
            storage = None
            if 'ephemeral-storage' in i.status.allocatable:
                storage = '%iG' %round(int(i.status.allocatable['ephemeral-storage'])/1024/1024/1024)
            memory = None
            if 'memory' in i.status.allocatable:
                memory = '%iG' %round(int(i.status.allocatable['memory'].split('Ki')[0])/1024/1024)
            NODES[i.metadata.name] = {
                'node_type':node_type,
                'flannel':flannel,
                'cpu':i.status.allocatable['cpu'],
                'cpu_load':'{0}%'.format(cpu_load),
                'memory':memory,
                'mem_used':'{0}%'.format(mem_used),
                'storage':storage,
                'lables': labels,
                'version':i.status.node_info.kubelet_version,
                'status':i.status.conditions[-1].type
            }
        app_resp = make_response(render_template('k8s-nodes.html', NODES=NODES, tables=tables, keys=keys))
        if context:
            app_resp.set_cookie('active_context', context, path='/')
        return app_resp
    except Exception as e:
        logging.error(e)

@page_k8s.route('/k8s/nodes_show')
def nodes_show():
    form = MyForm.FormK8sContexts()
    return render_template('k8s-nodes-show.html',form=form)

@page_k8s.route('/k8s/endpoints')
def endpoints():
    tables = ('endpoints', 'host', 'port', '状态')
    VAULES = defaultdict()
    try:
        v1 = client.CoreV1Api()
        ret = v1.list_namespaced_endpoints('default')
        for i in ret.items:
            try:
                Infos = []
                for infos in i.subsets:
                    try:
                        for info in infos.addresses:
                            try:
                                ip_header = '.'.join(str(info.ip).split('.')[:2])
                                if '{}.'.format(ip_header) in ('',''):
                                    if tcpping(host=info.ip, port=infos.ports[0].port, timeout=3):
                                        Infos.append([info.ip,True])
                                    else:
                                        Infos.append([info.ip,False])
                            except:
                                continue
                    except:
                        continue
                if Infos:
                    VAULES[i.metadata.name] = [Infos,infos.ports[0].port]
            except:
                continue
    except Exception as e:
        logging.error(e)
    return render_template('k8s-endpoints.html',VAULES=VAULES,tables=tables)

@page_k8s.route('/k8s/events')
def events():
    tables=('datetime','kind','name','namespace','message','reason','type')
    db_events = db_op.k8s_events
    events = db_events.query.with_entities(db_events.date_time,db_events.kind,db_events.name,db_events.namespace,
                                           db_events.message,db_events.reason,db_events.type).filter(
        db_events.context==g.context).order_by(
        desc(db_events.date_time)).limit(500).all()
    return render_template('k8s_events.html',events=events,tables=tables)

@page_k8s.route('/k8s/pv')
def pv():
    tables=('pv_name','storage','access_modes','server','path','pv_claim','status')
    v1 = client.CoreV1Api()
    ret = v1.list_persistent_volume()
    pvs = defaultdict()
    for i in ret.items:
        val = []
        try:
            val.append(i.spec.capacity['storage'])
            val.append(i.spec.access_modes[0])
            if i.spec.glusterfs:
                val.append(i.spec.glusterfs.endpoints)
                val.append(i.spec.glusterfs.path)
            if i.spec.nfs:
                val.append(i.spec.nfs.server)
                val.append(i.spec.nfs.path)
            if i.spec.claim_ref:
                val.append(i.spec.claim_ref.name)
            else:
                val.append(None)
            val.append(i.status.phase)
        except Exception as e:
            logging.error(e)
        else:
            if val:
                pvs[i.metadata.name] = val
    return render_template('k8s_pv.html', pvs=pvs, tables=tables)

@page_k8s.before_request
@user_auth.login_required(grade=1)
def check_login(error=None):
    tools.Async_log(g.user, request.url)
    _, active_contexts = config.list_kube_config_contexts(config_file)
    g.context = active_contexts['name']
    if 'active_context' in request.cookies:
        g.context = request.cookies['active_context']
    config.load_kube_config(config_file, g.context)

@page_k8s.teardown_request
def db_remove(error=None):
    db_idc.DB.session.remove()
    db_op.DB.session.remove()
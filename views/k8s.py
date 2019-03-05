#-*- coding: utf-8 -*-
from flask import Blueprint,render_template,g,request
from Modules import check,loging,produce,tools,MyForm,db_idc
from flask import Flask
from kubernetes import client, config
from collections import defaultdict,OrderedDict
from flask_sqlalchemy import SQLAlchemy
import time
import redis
from pyecharts import Line
app = Flask(__name__)
app.config.from_pyfile('../conf/sql.conf')
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/redis.conf')
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
RC = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
logging = loging.Error()
config,contexts,config_file = tools.k8s_conf()
page_k8s = Blueprint('k8s',__name__)
@page_k8s.route('/k8s/pods')
@page_k8s.route('/k8s/pods/<context>')
def pods(context=None):
    form = MyForm.Form_k8s_contexts()
    valus = defaultdict()
    if context and context != 'moji':
        config.load_kube_config(config_file,context)
    else:
        _,active_contexts = config.list_kube_config_contexts(config_file)
        context = active_contexts['name']
    v1 = client.CoreV1Api()
    namespace = []
    image = []
    phases = []
    ret = v1.list_pod_for_all_namespaces()
    for i in ret.items:
        try:
            pod_ports = []
            tables = ('POD_NAME','POD_IP','POD_PORTS','namespace','containers','NODE','镜像地址','运行状态')
            keys = ('pod_ip','ports','namespace','container','node_name','image','phase')
            if i.spec.containers[0].ports:
                for ports in i.spec.containers:
                    if ports.ports:
                        for port in ports.ports:
                            pod_ports.append(str(port.container_port))
            if pod_ports:
                pod_ports = ','.join(pod_ports)
            else:
                pod_ports = 'None'
            if i.status.container_statuses[-1].state.running:
                phase = 'Running'
            else:
                phase = 'Running'
                if i.status.container_statuses[-1].state.waiting:
                    phase = i.status.container_statuses[-1].state.waiting.reason
            valus[i.metadata.name] = {'pod_ip':i.status.pod_ip,
                                    'namespace':i.metadata.namespace,
                                    'node_name':i.spec.node_name,
                                     'container':len(i.spec.containers),
                                    'image':';'.join([images.image for images in i.spec.containers]),
                                    'phase':phase,
                                    'ports':pod_ports
                                    }
            namespace.append(i.spec.node_name)
            for images in i.spec.containers:
                image.append(images.image)
            phases.append(phase)
        except Exception as e:
            logging.error(e)
    counts = [len(valus),len(set(namespace)),len(set(image)),float('%.2f' %((float(phases.count('Running'))/len(valus))*100))]
    return render_template('k8s-resource.html', valus=valus, tables=tables, keys=keys, counts=counts, form=form,
                           context=context, resource='Pods')

@page_k8s.route('/k8s/deployment')
@page_k8s.route('/k8s/deployment/<context>')
def deployment(context=None):
    try:
        form = MyForm.Form_k8s_contexts()
        valus = defaultdict()
        if context and context != 'moji':
            config.load_kube_config(config_file, context)
        else:
            _, active_contexts = config.list_kube_config_contexts(config_file)
            context = active_contexts['name']
        v1 = client.AppsV1Api()
        tables = ('name','namespace', 'replicas', 'strategy', 'containers','dns_policy','service_account','available')
        keys  = ('namespace', 'replicas', 'strategy', 'containers','dns_policy','service_account','available')
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
                valus[i.metadata.name]={
                    'namespace':i.metadata.namespace,
                    'replicas':i.spec.replicas,
                    'strategy':i.spec.strategy.type,
                    'containers':containers,
                    'dns_policy':i.spec.template.spec.dns_policy,
                    'service_account': i.spec.template.spec.service_account,
                    'available':available
                }
            except Exception as e:
                logging.error(e)
    except Exception as e:
        logging.error(e)
    return render_template('k8s-resource.html',valus=valus,tables=tables,keys=keys,form=form,context= context,resource='Deployment')

@page_k8s.route('/k8s/daemonset')
@page_k8s.route('/k8s/daemonset/<context>')
def daemonset(context=None):
    try:
        form = MyForm.Form_k8s_contexts()
        valus = defaultdict()
        if context and context != 'moji':
            config.load_kube_config(config_file, context)
        else:
            _, active_contexts = config.list_kube_config_contexts(config_file)
            context = active_contexts['name']
        v1 = client.AppsV1Api()
        tables = ('name','namespace', 'images', 'mount_path', 'dns_policy','service_account','number_ready')
        keys  = ('namespace', 'images', 'mount_path', 'dns_policy','service_account','number_ready')
        ret = v1.list_daemon_set_for_all_namespaces()
        for i in ret.items:
            try:
                mount_path = []
                for path in i.spec.template.spec.containers[0].volume_mounts:
                    mount_path.append(path.mount_path)
                number_ready = i.status.number_ready
                if number_ready == 0:
                    number_ready = 1
                valus[i.metadata.name]={
                    'namespace':i.metadata.namespace,
                    'images':i.spec.template.spec.containers[0].image,
                    'mount_path':mount_path,
                    'dns_policy':i.spec.template.spec.dns_policy,
                    'service_account':i.spec.template.spec.service_account,
                    'number_ready': number_ready
                }
            except Exception as e:
                logging.error(e)
    except Exception as e:
        logging.error(e)
    return render_template('k8s-resource.html',valus=valus,tables=tables,keys=keys,form=form,context= context,resource='Daemonset')

@page_k8s.route('/k8s/service')
@page_k8s.route('/k8s/service/<context>')
def service(context=None):
    try:
        form = MyForm.Form_k8s_contexts()
        valus = defaultdict()
        if context and context != 'moji':
            config.load_kube_config(config_file, context)
        else:
            _, active_contexts = config.list_kube_config_contexts(config_file)
            context = active_contexts['name']
        v1 = client.CoreV1Api()
        tables = ('name','namespace', 'cluster_ip', 'port', 'target_port','node_port','selector')
        keys  = ('namespace', 'cluster_ip', 'port', 'target_port', 'node_port', 'selector')
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
    except Exception as e:
        logging.error(e)
    return render_template('k8s-resource.html',valus=valus,tables=tables,keys=keys,form=form,context= context,resource='Service')

@page_k8s.route('/k8s/ingress')
@page_k8s.route('/k8s/ingress/<context>')
def ingress(context=None):
    try:
        form = MyForm.Form_k8s_contexts()
        valus = []
        if context and context != 'moji':
            config.load_kube_config(config_file, context)
        else:
            _, active_contexts = config.list_kube_config_contexts(config_file)
            context = active_contexts['name']
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
    except Exception as e:
        logging.error(e)
    return render_template('k8s-resource.html',valus=valus,tables=tables,keys=keys,form=form,context= context,resource='Ingress')

@page_k8s.route('/k8s/hpa')
@page_k8s.route('/k8s/hpa/<context>')
def hpa(context=None):
    try:
        form = MyForm.Form_k8s_contexts()
        valus = []
        if context and context != 'moji':
            config.load_kube_config(config_file, context)
        else:
            _, active_contexts = config.list_kube_config_contexts(config_file)
            context = active_contexts['name']
        v1 = client.AutoscalingV1Api()
        keys = tables = ('name','最大副本','最小副本', '当前副本', 'CPU阀值','CPU当前值')
        ret = v1.list_horizontal_pod_autoscaler_for_all_namespaces()
        for i in ret.items:
            try:

                valus.append([i.spec.scale_target_ref.name,
                             i.spec.max_replicas,
                             i.spec.min_replicas,
                             i.status.current_replicas,
                             '{0}%'.format(i.spec.target_cpu_utilization_percentage),
                             '{0}%'.format(i.status.current_cpu_utilization_percentage)]
                             )
            except Exception as e:
                logging.error(e)
        td = time.strftime('%Y-%m-%d', time.localtime())
        Key = 'op_hpa_chart_%s' % td
        infos = RC.hgetall(Key)
        infos = sorted(infos.items(), key=lambda item: item[0].split('_')[-1])
        line = Line('HPA动态伸缩实时状态', width='110%', height='250px', title_pos='center', title_text_size=14)
        for project in valus:
            attr = []
            vals = []
            for info in infos:
                if project[0] in info[0]:
                    attr.append(str(info[0].split('_')[-1]))
                    vals.append(int(info[1]))
            line.add(project[0], attr, vals, is_toolbox_show=False, is_smooth=True, mark_point=["max", "min"],
                  mark_point_symbolsize=60,legend_pos='60%',is_datazoom_show=True, datazoom_range=[v for v in range(100, 10)],
                             datazoom_type='both',)
    except Exception as e:
        logging.error(e)
    return render_template('k8s-resource.html',valus=valus,tables=tables,keys=keys,form=form,line=line,context= context,resource='HPA')

@page_k8s.route('/k8s/nodes')
def nodes():
    NODES = defaultdict()
    for context in contexts:
        if context != 'moji':
            nodes = OrderedDict()
            config.load_kube_config(config_file, context)
            v1 = client.CoreV1Api()
            ret = v1.list_node(watch=False)
            tables = ('节点','角色','flannel','CPU','CPU使用率','内存','内存使用率','硬盘','最大容器数量','版本')
            keys = ('node_type','flannel','cpu','cpu_load','memory','mem_used','storage','pods','version')
            db_zabbix = db_idc.zabbix_info
            for i in ret.items:
                if 'node-role.kubernetes.io/master' in i.metadata.labels:
                    node_type = 'master'
                else:
                    node_type = 'node'
                cpu_load = mem_used = '-'
                values = db_zabbix.query.with_entities(db_zabbix.cpu_load,db_zabbix.mem_use).filter(db_zabbix.hostname==i.metadata.name).all()
                if values:
                    cpu_load,mem_used = values[0]
                nodes[i.metadata.name] = {
                    'node_type':node_type,
                    'flannel':i.metadata.annotations['flannel.alpha.coreos.com/backend-type'],
                    'cpu':i.status.allocatable['cpu'],
                    'cpu_load':'{0}%'.format(cpu_load),
                    'memory':i.status.allocatable['memory'],
                    'mem_used':'{0}%'.format(mem_used),
                    'storage':i.status.allocatable['ephemeral-storage'],
                     'pods': i.status.allocatable['pods'],
                    'version':i.status.node_info.kubelet_version,
                }
            NODES[context] = nodes
    return render_template('k8s-nodes.html',NODES=NODES,tables=tables,keys=keys)

@page_k8s.before_request
@check.login_required(grade=1)
def check_login(error=None):
    produce.Async_log(g.user, request.url)

@page_k8s.teardown_request
def db_remove(error=None):
    db_idc.DB.session.remove()
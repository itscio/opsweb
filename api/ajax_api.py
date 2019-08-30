#-*- coding: utf-8 -*-
from flask import Flask,Blueprint,jsonify,request,abort
from module import db_op,db_idc,loging,tools
import time
import redis
import urllib
import oss2
import conf
from kubernetes import client
from flask_sqlalchemy import SQLAlchemy
from module import user_auth
from sqlalchemy import distinct,desc
from collections import defaultdict
app = Flask(__name__)
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/oss.conf')
app.config.from_pyfile('../conf/sql.conf')
logging = loging.Error()
limiter = conf.WebLimiter()
limiter = limiter.limiter
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
RC = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
redis_data = app.config.get('REDIS_DATA')
RC_CLUSTER = redis.StrictRedis(host=redis_data, port=redis_port,decode_responses=True)
config,contexts,config_file = tools.k8s_conf()
page_ajax_api = Blueprint('ajax_api', __name__)
oss_id = app.config.get('OSS_ID')
oss_key = app.config.get('OSS_KEY')
oss_url = app.config.get('OSS_URL')
@page_ajax_api.route('/get_k8s_deployment/<context>')
@limiter.limit("60/minute")
def get_k8s_deployment(context=None):
    deployments = []
    db_deploy = db_op.k8s_deploy
    try:
        deployments = db_deploy.query.with_entities(distinct(db_deploy.deployment)).filter(
            db_deploy.context==context).all()
        if deployments:
            deployments = [deploy[0] for deploy in deployments]
    except Exception as e:
        logging.error(e)
    finally:
        db_op.DB.session.remove()
        return jsonify({'values': deployments})

@page_ajax_api.route('/get_k8s_services/<context>')
@limiter.limit("60/minute")
def get_k8s_services(context=None):
    values = defaultdict()
    services = []
    try:
        config.load_kube_config(config_file,context)
        v1 = client.CoreV1Api()
        ret = v1.list_namespaced_service(namespace='default')
        for i in ret.items:
            port = []
            for info in i.spec.ports:
                port.append(int(info.port))
            services.append(i.metadata.name)
            values[i.metadata.name] = port[0]
    except Exception as e:
        logging.error(e)
    finally:
        return jsonify({'values': values,'services':services})

@page_ajax_api.route('/get_business_bigdata/<host>',methods = ['GET', 'POST'])
@limiter.limit("60/minute")
def business_bigdata_host_get(host=None):
    if host:
        dt = time.strftime('%Y-%m-%d', time.localtime())
        uris = RC_CLUSTER.smembers('api_uri_lists_%s_%s' %(host, dt))
        uris = [uri.strip() for uri in uris if uri not in ('-','_')]
        return jsonify({'results':uris})
    else:
        return jsonify({'results':None})

@page_ajax_api.route('/get_project_version/<project>',methods = ['GET', 'POST'])
@limiter.limit("60/minute")
def get_project_version(project=None):
    try:
        if project:
            db_publish = db_op.publish_records
            vals  = db_publish.query.with_entities(distinct(db_publish.version)).filter(db_publish.project==project).order_by(desc(db_publish.version)).all()
            if vals:
                versions = [val[0] for val in vals]
                return jsonify({'results': versions})
            else:
                return jsonify({'results': None})
        else:
            return jsonify({'results': None})
    except Exception as e:
        logging.error(e)
        return jsonify({'results': None})

@page_ajax_api.route('/assets_info/<action>',methods = ['POST'])
@user_auth.login_required(grade=1)
def assets_info(action=None):
    try:
        if action == 'update':
            params = request.json
            if params:
                if 'hostname' in params and 'comment' in params:
                    hosname = params['hostname']
                    comment = params['comment']
                    db_server = db_idc.idc_servers
                    db_server.query.filter(db_server.hostname==hosname).update({db_server.comment:comment})
                    db_idc.DB.session.commit()
                    return jsonify({'results': 'success'})
        return abort(400)
    except Exception as e:
        logging.error(e)
        return abort(400)

@page_ajax_api.route('/alarm_load_whitelist/<action>/<hostname>',methods = ['GET', 'POST'])
@user_auth.login_required(grade=1)
def alarm_load_whitelist(hostname=None,action=None):
    result = {'status': 'error', 'infos': '确认失败!'}
    try:
        Key = "op_alarm_load_whitelist"
        if action == 'attention':
            RC_CLUSTER.sadd(Key,hostname)
        if action == 'cancel':
            RC_CLUSTER.srem(Key, hostname)
        if action in ('attention','cancel'):
            result = {'status': 'ok','infos':'确认成功!'}
    except Exception as e:
        logging.error(e)
    finally:
        return jsonify(result)

@page_ajax_api.route('/webssh_exec', methods=['POST'])
def webssh_exec():
    try:
        db_webssh = db_op.webssh_records
        info = str(request.get_data(),encoding='utf8').split('&')
        msg_id = info[1].split('=')[-1]
        dst_ip = info[2].split('=')[-1]
        ssh_port = info[3].split('=')[-1]
        exec = info[0].split('=')[-1]
        Key = 'op_webssh_exec_%s:%s' %(dst_ip,ssh_port)
        if exec != '%0D':
            exec = urllib.parse.unquote(exec,encoding='utf-8')
            RC.rpush(Key,exec)
        else:
            exec = ''.join(RC.lrange(Key,0,-1)).replace('+',' ')
            RC.delete(Key)
            user = RC.hget('op_webssh_session',msg_id)
            if not user:
                user = ''
            c = db_webssh(date=time.strftime('%Y-%m-%d',time.localtime()),
                          time=time.strftime('%H:%M:%S',time.localtime()),
                          msg_id=msg_id,user=user,dst_ip=dst_ip,sshport=ssh_port,exec=exec)
            db_op.DB.session.add(c)
            db_op.DB.session.commit()
    except Exception as e:
        logging.error(e)
    finally:
        return jsonify({'stats':200})

@page_ajax_api.route('/msg_id', methods=['POST'])
def msg_id():
    try:
        infos = request.get_json()
        user = RC.get('OP_user_%s' %infos['user'])
        RC.hset('op_webssh_session',infos['msg_id'],user)
    except Exception as e:
        logging.error(e)
    finally:
        return jsonify({'stats':200})

@page_ajax_api.route('/modify_ops_comment', methods=['POST'])
@user_auth.login_required(grade=1)
def modify_ops_comment():
    status = None
    infos = '同步备注信息失败!'
    try:
        infos = request.get_json()
        status = tools.modify_jumpserver_comment(infos['hostname'],infos['comment'])
        if int(status) == 200:
            status = 'ok'
            infos = '同步备注信息成功!'
    except Exception as e:
        logging.error(e)
    finally:
        return jsonify({'status':status,'infos':infos})

@page_ajax_api.route('/get_oss_version/<project>')
@user_auth.login_required(grade=1)
def get_oss_version(project=None):
    try:
        versions = []
        if project:
            tt = time.strftime('%Y',time.localtime())
            auth = oss2.Auth(oss_id, oss_key)
            bucket = oss2.Bucket(auth, oss_url, 'xxxxops')
            for obj in oss2.ObjectIterator(bucket):
                if obj.key.endswith('.war') or obj.key.endswith('.tar.gz') or obj.key.endswith('.jar'):
                    if obj.key.split('/')[-1].startswith(project):
                        try:
                            ver = obj.key.split(tt)[-1].split('-')
                            version = int('%s%s'%(tt,ver[0]))
                            version = '%s-%s' %(version,ver[1].split('.')[0])
                            versions.append(version)
                        except:
                            pass
            versions = list(set(versions))
            versions.sort(reverse=True)
            if len(versions) >10:
                versions = versions[:10]
    except Exception as e:
        logging.error(e)
    finally:
        return jsonify({project:versions})

@page_ajax_api.teardown_request
def db_remove(exception):
    db_op.DB.session.remove()
    db_idc.DB.session.remove()
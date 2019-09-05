#-*- coding: utf-8 -*-
from flask import Flask,Blueprint,jsonify,request,abort,g,render_template
from module import db_op,db_idc,loging,tools
import time
import redis
import urllib
import oss2
import module
from kubernetes import client
from flask_sqlalchemy import SQLAlchemy
from module import user_auth
from sqlalchemy import distinct,desc,func,and_,or_
from collections import defaultdict
app = Flask(__name__)
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/oss.conf')
app.config.from_pyfile('../conf/sql.conf')
app.config.from_pyfile('../conf/work_order.conf')
logging = loging.Error()
limiter = module.WebLimiter()
limiter = limiter.limiter
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
Redis = RC = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
redis_data = app.config.get('REDIS_DATA')
RC_CLUSTER = redis.StrictRedis(host=redis_data, port=redis_port,decode_responses=True)
config,contexts,config_file = tools.k8s_conf()
page_ajax_api = Blueprint('ajax_api', __name__)
oss_id = app.config.get('OSS_ID')
oss_key = app.config.get('OSS_KEY')
oss_url = app.config.get('OSS_URL')
source_types = app.config.get('SOURCE_TYPES')
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
    versions = []
    try:
        if project:
            tt = time.strftime('%Y',time.localtime())
            auth = oss2.Auth(oss_id, oss_key)
            bucket = oss2.Bucket(auth, oss_url, 'xxxops')
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

@page_ajax_api.route('/input_work_comment/<int:work_number>/<comment>')
@user_auth.login_required(grade=10)
def input_work_comment(work_number=None,comment=None):
    result = {'result':'fail'}
    try:
        if work_number and comment:
            tt = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime())
            db_work_comment = db_op.work_comment
            c = db_work_comment(date_time=tt,work_number=work_number,
                                dingid=g.dingId,user=g.user,comment=comment)
            db_op.DB.session.add(c)
            db_op.DB.session.commit()
            #记录工单问题备注通知信息
            db_work_order = db_op.work_order
            db_user_sso = db_op.user_sso
            infos = db_work_order.query.with_entities(db_work_order.applicant,db_work_order.reviewer,
                                                       db_work_order.dingid,db_work_order.source
                                                       ).filter(db_work_order.work_number==work_number).all()
            if infos:
                infos = [info for info in infos[0] if info]
                reviewer = db_user_sso.query.with_entities(db_user_sso.dingunionid).filter(db_user_sso.mail==infos[1]).all()
                infos[1] = reviewer[0][0]
                for dingid in infos[:-1]:
                    if g.dingId != dingid:
                        Redis.hset('op_work_comment_alarm_%s' % dingid, work_number,infos[-1])
            result = {'result': 'ok'}
    except Exception as e:
        logging.error(e)
    finally:
        return jsonify(result)

@page_ajax_api.route('/work_order_alarm')
@user_auth.login_required(grade=10)
def work_order_alarm():
    url = None
    text = None
    # 获取工单消息数
    alarms = Redis.hlen('op_work_comment_alarm_%s' % g.dingId)
    if alarms >0:
        url = '/work_comment_unread'
        text = f'你有{alarms}条工单问题备注消息未读!'
    else:
        # 获取未完结工单数
        db_work_order = db_op.work_order
        db_sso = db_op.user_sso
        mail = db_sso.query.with_entities(db_sso.mail).filter(db_sso.dingunionid==g.dingId).all()
        alarms = db_work_order.query.with_entities(func.count(db_work_order.work_number)
                                                   ).filter(and_(or_(db_work_order.dingid==g.dingId,
                                                                     db_work_order.reviewer==mail[0][0],
                                                                     db_work_order.approval == g.dingId),
                                                                 db_work_order.status.in_(('未审核','待审批','受理中'))))
        if alarms:
            try:
                if alarms[0][0] >0:
                    url = '/work_review/self'
                    if int(g.grade[0]) in (0,1):
                        url = '/work_norun/self'
                    alarms = alarms[0][0]
                    text = f'你有{alarms}条运维工单还未处理!'
            except Exception as e:
                logging.error(e)
    return render_template('work_order_alarm.html', url = url,text=text)

@page_ajax_api.route('/work_comment_unread')
@user_auth.login_required(grade=10)
def work_comment_unread():
    # 获取工单消息
    comments = Redis.hgetall('op_work_comment_alarm_%s' % g.dingId)
    return render_template('work_comment_unread.html', comments=comments,source_types=source_types)

@page_ajax_api.teardown_request
def db_remove(exception):
    db_op.DB.session.remove()
    db_idc.DB.session.remove()
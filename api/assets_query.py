#-*- coding: utf-8 -*-
from flask import Blueprint,jsonify,request
from module import db_op,db_idc,loging,Md5
from sqlalchemy import and_
import time
import conf
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import distinct
import redis
from flask import Flask
app = Flask(__name__)
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/sql.conf')
limiter = conf.web_limiter()
limiter = limiter.limiter
logging = loging.Error()
redis_data = app.config.get('REDIS_DATA')
redis_port = app.config.get('REDIS_PORT')
RC_CLUSTER = redis.StrictRedis(host=redis_data, port=redis_port,decode_responses=True)
redis_host = app.config.get('REDIS_HOST')
redis_password = app.config.get('REDIS_PASSWORD')
RC = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
page_assets_query = Blueprint('assets_query', __name__)
@page_assets_query.route('/assets_query',methods = ['POST'])
@limiter.limit("200/minute")
def assets_query():
    ip = None
    idcs = None
    status = 'None'
    try:
        db_servers = db_idc.idc_servers
        db_idc_id = db_idc.idc_id
        db_token = db_op.platform_token
        params = request.get_json()
        #服务器机房查询
        if params:
            if 'access_token' in params:
                access_token = params['access_token']
                # 验证token是否有效
                vals = db_token.query.filter(and_(db_token.token == access_token, db_token.expire > time.strftime('%Y-%m-%d', time.localtime()))).all()
                if vals:
                    #判断参数是否存在
                    if 'ip' in params:
                        ip = params['ip']
                        Key = 'op_query_idc_%s' % ip
                        if ip == 'all':
                            # 先在缓存中查询结果
                            if RC_CLUSTER.exists(Key):
                                idcs = eval(RC_CLUSTER.get(Key))
                            else:
                                # 获取全量idc信息id
                                idcs = db_servers.query.with_entities(db_servers.ip,db_servers.idc_id).all()
                                idcs = [list(idc) for idc in idcs if len(idc) ==2]
                                for i,info in enumerate(idcs):
                                    idc = db_idc_id.query.with_entities(db_idc_id.aid).filter(db_idc_id.id == int(info[-1])).all()
                                    if idc:
                                        info[-1] = idc[0][0]
                                    else:
                                        idcs.pop(i)
                                idcs = {idc[0]:idc[-1] for idc in idcs}
                                # 缓存查询结果
                                RC_CLUSTER.set(Key,idcs)
                                RC_CLUSTER.expire(Key,3600)
                        else:
                            # 先在缓存中查询结果
                            if RC_CLUSTER.exists(Key):
                                idcs = RC_CLUSTER.get(Key)
                            else:
                                # 获取idc信息id
                                idc_id = db_servers.query.with_entities(db_servers.idc_id).filter(db_servers.ip==ip).all()
                                if idc_id:
                                    #获取idc机房信息
                                    idc_info = db_idc_id.query.with_entities(db_idc_id.aid).filter(db_idc_id.id==int(idc_id[0][0])).all()
                                    if idc_info:
                                        idcs = idc_info[0][0]
                                        #缓存查询结果
                                        RC_CLUSTER.set(Key,idcs)
                                        RC_CLUSTER.expire(Key,3600)
        if idcs:
            status = 'ok'
    except Exception as e:
        status = 'error'
        logging.error(e)
    finally:
        return jsonify({'status': status, 'ip': ip, 'idc': idcs})

@page_assets_query.route('/project_get/<project>')
@limiter.limit("60/minute")
def project_get(project=None):
    try:
        rep = jsonify({'error': 'None', 'url': request.url})
        Key = 'op_project_get_%s' %time.strftime('%H%M%S',time.localtime())
        if project:
           db_project = db_op.project_list
           db_servers = db_idc.idc_servers
           if project == 'all_list':
               vals = db_project.query.with_entities(distinct(db_project.project)).all()
               projects = [val[0] for val in vals]
               rep = jsonify({project: projects, 'md5': Md5.Md5_make(str(projects)), 'url': request.url})
           else:
               projects = []
               vals = db_project.query.with_entities(db_project.ip,db_project.ssh_port).filter(db_project.project==project).all()
               if vals:
                   for ip,ssh_port in vals:
                       host_vals = db_servers.query.with_entities(db_servers.hostname,db_servers.ip).filter(and_(db_servers.ip==ip,db_servers.ssh_port==ssh_port)).all()
                       if host_vals:
                           RC.sadd(Key,list(host_vals[0]))
               for val in RC.smembers(Key):
                   projects.append(eval(val))
               RC.delete(Key)
               rep = jsonify({project:projects,'md5':Md5.Md5_make(str(projects)),'url':request.url})
    except Exception as e:
        rep = jsonify({'error':str(e),'url':request.url})
    finally:
        return rep

@page_assets_query.route('/hosts_get/<host>/<domain>')
@limiter.limit("60/minute")
def hosts_get(host=None,domain=None):
    try:
        rep = jsonify({host:{domain:'None'}, 'url': request.url})
        if host:
           db_hosts = db_idc.hosts
           db_servers = db_idc.idc_servers
           server_id = db_servers.query.with_entities(db_servers.id).filter(db_servers.ip == host).all()
           if server_id:
               vals = db_hosts.query.with_entities(db_hosts.host).filter(and_(db_hosts.server_id==int(server_id[0][0]),db_hosts.hostname==domain)).all()
               if vals:
                   hostname = db_servers.query.with_entities(db_servers.hostname).filter(db_servers.ip==vals[0][0]).all()
                   if hostname:
                       rep = jsonify({host:{domain:hostname[0][0]},'url':request.url})
    except Exception as e:
        logging.error(e)
    finally:
        return rep
@page_assets_query.teardown_request
def db_remove(exception):
    db_idc.DB.session.remove()
    db_op.DB.session.remove()
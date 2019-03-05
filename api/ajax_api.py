#-*- coding: utf-8 -*-
from flask import Blueprint,jsonify,request,redirect,url_for,abort
from Modules import db_op,db_idc,Md5,loging
from sqlalchemy import and_
from flask import Flask
import time,datetime
import redis
from flask_sqlalchemy import SQLAlchemy
from Modules import init,check
from sqlalchemy import distinct,desc
app = Flask(__name__)
app.config.from_pyfile('../conf/sql.conf')
DB = SQLAlchemy(app)
logging = loging.Error()
limiter = init.web_limiter()
limiter = limiter.limiter
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/security.conf')
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
RC = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
redis_data = app.config.get('REDIS_DATA')
RC_CLUSTER = redis.StrictRedis(host=redis_data, port=redis_port,decode_responses=True)
page_ajax_api = Blueprint('ajax_api', __name__)
@page_ajax_api.route('/zb_ensure/<id>')
@check.login_required(grade=1)
def zb_ensure(id=None):
    try:
        RC.sadd('zabbix_ensure',id)
        tm = datetime.datetime.now() - datetime.timedelta(minutes=1)
        tm = tm.strftime('%H:%M')
        Key = 'zabbix_triggers_%s' % tm
        RC.hdel(Key,id)
    except Exception as e:
        logging.error(e)
    finally:
        return redirect(url_for('index.index'))

@page_ajax_api.route('/project_get/<project>')
@limiter.limit("60/minute")
def project_get(project=None):
    try:
        Key = 'op_project_get_%s' %time.strftime('%H%M%S',time.localtime())
        projects = []
        if project:
           db_project = db_op.project_list
           db_servers = db_idc.idc_servers
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
        return rep
    except Exception as e:
        return jsonify({'error':str(e),'url':request.url})

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
@check.login_required(grade=1)
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

@page_ajax_api.teardown_request
def db_remove(exception):
    db_op.DB.session.remove()
    db_idc.DB.session.remove()
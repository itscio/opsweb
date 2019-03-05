#-*- coding: utf-8 -*-
from flask import Blueprint,request,jsonify
from Modules import loging,tools,k8s_resource,db_op,produce
from flask import Flask
import time
from sqlalchemy import and_
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)
app.config.from_pyfile('../conf/sql.conf')
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/docker.conf')
logging = loging.Error()
docke_registry = app.config.get('REGISTRY')
config,contexts,config_file = tools.k8s_conf()
config.load_kube_config(config_file, context=contexts[0])
page_deployment_deploy = Blueprint('deployment_deploy',__name__)
@page_deployment_deploy.route('/deployment_update',methods = ['POST'])
def deployment_update():
    db_token = db_op.platform_token
    params = request.json
    new_replicas = None
    msg = "image build fail!"
    try:
        if params:
            if 'project' in params and 'version' in params and 'access_token' in params:
                token = params['access_token']
                project = params['project']
                version = params['version']
                new_image = "%s/%s:%s" %(docke_registry,project.split('.')[0],version)
                if 'replicas' in params:
                    new_replicas = params['replicas']
                # 验证token是否有效
                vals = db_token.query.filter(and_(db_token.token == token, db_token.expire > time.strftime('%Y-%m-%d', time.localtime()))).all()
                if vals:
                    redis_key = 'op_k8s_update_%s' %time.strftime('%Y%m%d%H%M%S', time.localtime())
                    Scheduler = produce.Scheduler_publish()
                    Scheduler = Scheduler.Scheduler_mem(k8s_resource.object_update, [new_image, new_replicas,version,redis_key])
                    Scheduler.start()
                    msg = "http://op.moji.com/deploy_query/%s" %redis_key
                else:
                    msg = 'token deny!'
            else:
                msg = 'url params error!'
        else:
            msg = 'url params null!'
    except Exception as e:
        msg = e
    finally:
        return jsonify({'result': msg})
@page_deployment_deploy.teardown_request
def db_remove(exception):
    db_op.DB.session.remove()
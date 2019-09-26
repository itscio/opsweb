#-*- coding: utf-8 -*-
from flask import Flask,Blueprint,request,jsonify
from module import loging,tools,k8s_resource,db_op,produce
import time
from sqlalchemy import and_
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)
DB = SQLAlchemy(app)
logging = loging.Error()
app.config.from_pyfile('../conf/docker.conf')
docker_registry = app.config.get('REGISTRY')
config,contexts,config_file = tools.k8s_conf()
config.load_kube_config(config_file, context=contexts[0])
page_k8s_project_update = Blueprint('k8s_project_update',__name__)
@page_k8s_project_update.route('/k8s_project_update',methods = ['POST'])
def k8s_project_update():
    db_token = db_op.platform_token
    params = request.get_json()
    new_replicas = None
    msg = None
    project = None
    version = None
    try:
        if params:
            if 'project' in params and 'version' in params and 'access_token' in params and 'context' in params:
                token = params['access_token']
                project = params['project']
                version = params['version']
                context = params['context']
                new_image = "%s/%s:%s" %(docker_registry[context],project.split('.')[0],version)
                if 'replicas' in params:
                    new_replicas = params['replicas']
                # 验证token是否有效
                vals = db_token.query.filter(and_(db_token.token == token, db_token.expire > time.strftime('%Y-%m-%d',
                                                            time.localtime()))).all()
                if vals:
                    redis_key = 'op_k8s_update_%s' %time.strftime('%Y%m%d%H%M%S', time.localtime())
                    Scheduler = produce.SchedulerPublish()
                    Scheduler = Scheduler.Scheduler_mem(k8s_resource.object_update, [context,new_image,
                                                                                     new_replicas,version,
                                                                                     redis_key,'api'])
                    Scheduler.start()
                else:
                    msg = '授权验证不通过!'
            else:
                msg = '传递参数错误!'
        else:
            msg = '传递参数不能为空!'
    except Exception as e:
        msg = e
    finally:
        if msg:
            ops_token = app.config.get('OPS_TOKEN')
            text = ['**容器平台自动上线:**',"项目:%s" %project,"版本:%s" %version,"Error:%s" %msg, '**请确认请求正确!**']
            tools.dingding_msg(text,ops_token)
        return jsonify({'result':'ok'})

@page_k8s_project_update.teardown_request
def db_remove(exception):
    db_op.DB.session.remove()
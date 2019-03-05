#-*- coding: utf-8 -*-
import redis
import string
import time
from flask import Blueprint,jsonify,request
from Modules import Md5,db_op,produce,loging,task_publish,tools
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from Modules import init
from sqlalchemy import and_
app = Flask(__name__)
app.config.from_pyfile('../conf/sql.conf')
DB = SQLAlchemy(app)
limiter = init.web_limiter()
limiter = limiter.limiter
app.config.from_pyfile('../conf/redis.conf')
logging = loging.Error()
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
Redis = redis.StrictRedis(host=redis_host, port=redis_port,password=redis_password,decode_responses=True)
page_publish_code = Blueprint('publish_code',__name__)
@page_publish_code.route('/publish_code',methods = ['POST'])
@limiter.limit("15/minute")
def publish_code():
    try:
        timestamp = None
        db_token = db_op.platform_token
        params = request.json
        GRAY = {'Flase':0,'True':1}
        # 检查时间戳是否存在
        if 'timestamp' in params['data']:
            timestamp = params['data']['timestamp']
        else:
            return jsonify({'status': 'timestamp is null', 'timestamp': None})
        #md5对比验证数据
        new_md5 = Md5.Md5_make(params['data'])
        if new_md5 == params['data_md5']:
            params = params['data']
            token = params['access_token']
            #验证token是否有效
            vals = db_token.query.filter(and_(db_token.token==token,db_token.expire > time.strftime('%Y-%m-%d',time.localtime()))).all()
            if vals:
                user = params['proposer']
                package_url = params['package_url']
                #检查压缩包下载地址格式
                if not package_url.endswith('.zip') and not package_url.endswith('.war'):
                    return jsonify({'status': 'the package must be zip or war', 'timestamp': timestamp})
                #获取详细参数
                describe = params['describe']
                package_md5 = params['package_md5']
                package_type = params['package_type']
                publish_type = params['publish_type']
                restart = params['restart']
                execute = params['execute']
                check_url = params['check_url']
                rb_project = params['project_name']
                rb_version = params['project_version']
                callback_url = params['callback_url']
                gray = GRAY[params['gray']]
                #生成随机key种子
                K = '%s_%s' %(token,tools.Produce(length=8,chars=string.digits))
                Msg_Key = '%s_publish_msg' % K
                INFOS = {'package_url': package_url, 'package_md5': package_md5, 'package_type': package_type,
                         'publish_type': publish_type,'user':user,'describe':describe.replace('"','').replace("'",''),'gray':gray,
                         'restart': restart, 'execute': execute, 'check_url': check_url.replace('https','http'), 'project': rb_project,
                         'version': rb_version,'channel':'api','callback_url':callback_url,'token':token,'timestamp':timestamp}
                #启动代码分发控制中心
                Scheduler = produce.Scheduler_publish()
                Scheduler = Scheduler.Scheduler_mem(task_publish.Publish_center,[INFOS,Msg_Key,K])
                Scheduler.start()
                return jsonify({'status': 'ok', 'timestamp': timestamp})
            else:
                return jsonify({'status': 'token deny', 'timestamp': timestamp})
        else:
            return jsonify({'status': 'data_md5 error', 'timestamp': timestamp})
    except Exception as e:
        logging.error(e)
        return jsonify({'status': str(e), 'timestamp': timestamp})
    finally:
        db_op.DB.session.remove()
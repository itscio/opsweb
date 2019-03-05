#-*- coding: utf-8 -*-
from flask import Blueprint,jsonify,request
from Modules import db_op,db_idc,loging
from sqlalchemy import and_
import time
from flask import Flask
from Modules import init
from flask_sqlalchemy import SQLAlchemy
import redis
app = Flask(__name__)
app.config.from_pyfile('../conf/sql.conf')
DB = SQLAlchemy(app)
limiter = init.web_limiter()
limiter = limiter.limiter
logging = loging.Error()
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/security.conf')
redis_data = app.config.get('REDIS_DATA')
redis_port = app.config.get('REDIS_PORT')
RC_CLUSTER = redis.StrictRedis(host=redis_data, port=redis_port,decode_responses=True)
page_assets_query = Blueprint('assets_query', __name__)
@page_assets_query.route('/assets_query',methods = ['POST'])
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

@page_assets_query.teardown_request
def db_remove(exception):
    db_idc.DB.session.remove()
    db_op.DB.session.remove()
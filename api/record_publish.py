#-*- coding: utf-8 -*-
import time
from flask import Blueprint,jsonify,request
from Modules import db_op,loging,init
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_
app = Flask(__name__)
app.config.from_pyfile('../conf/sql.conf')
DB = SQLAlchemy(app)
limiter = init.web_limiter()
limiter = limiter.limiter
app.config.from_pyfile('../conf/redis.conf')
logging = loging.Error()
page_record_publish = Blueprint('record_publish',__name__)
@page_record_publish.route('/record_publish',methods = ['POST'])
@limiter.limit("15/minute")
def record_publish():
    try:
        dt = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        db_publish = db_op.publish_records
        db_token = db_op.platform_token
        params = request.json
        if 'access_token' in params:
            token = params['access_token']
            #验证token是否有效
            vals = db_token.query.filter(and_(db_token.token==token,db_token.expire > time.strftime('%Y-%m-%d',time.localtime()))).all()
            if vals:
                # 获取详细参数
                user = params['proposer']
                package_url = params['package_url']
                describe = params['describe']
                project = params['project_name']
                version = params['project_version']
                if user and package_url and describe and project and version:
                    c = db_publish(date=time.strftime('%Y-%m-%d', time.localtime()),
                                   time=time.strftime('%H:%M:%S', time.localtime()),
                                   user=user, project=project, version=version, package_url=package_url,
                                   describe=describe,
                                   package_md5='', package_type='full',
                                   publish_type='batch',
                                   restart='True', check_url='', callback_url='',
                                   token=token,
                                   execute='publish', gray='', channel='api', result='Success',
                                   flow_number='None')
                    db_op.DB.session.add(c)
                    db_op.DB.session.commit()
                else:
                    return jsonify({'status': 'parameter  error!', 'datatime': dt})
            else:
                return jsonify({'status': 'token deny!', 'datatime': dt})
        else:
            return jsonify({'status': 'token not null!', 'datatime': dt})
    except Exception as e:
        logging.error(e)
        return jsonify({'record': str(e), 'datatime': dt})
    else:
        return jsonify({'record': 'ok', 'datatime': dt})
    finally:
        db_op.DB.session.remove()
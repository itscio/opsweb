#-*- coding: utf-8 -*-
from flask import Blueprint,request,render_template,g,flash
from Modules import check,db_op,produce,loging
from sqlalchemy import desc
import redis
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)
app.config.from_pyfile('../conf/sql.conf')
DB = SQLAlchemy(app)
logging = loging.Error()
app.config.from_pyfile('../conf/redis.conf')
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
Redis = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
page_examine = Blueprint('examine', __name__)
@page_examine.route('/publish_record')
@check.login_required(grade=2)
def publish_record():
    db = db_op.publish_records
    vals = []
    try:
        GRAY = {0:'否',1:'是'}
        vals = db.query.with_entities(db.date,db.time,db.user,db.project,db.version,db.package_url,db.describe,
                                     db.package_type,db.publish_type,db.restart,db.execute,db.gray,db.channel,
                                      db.result,db.flow_number).order_by(desc(db.id)).all()
        vals = [list(val) for val in vals]
        for val in vals:
            val[11] = GRAY[val[11]]
        tables = ['日期','时间','操作人','项目','版本号','下载地址','上线描述','包类型','部署方式','服务重启','操作','灰度','来源','执行结果','流水号']
    except Exception as e:
        logging.error(e)
    return render_template('publish_record.html',tables = tables,values = vals)
@page_examine.route('/op_log')
@check.login_required(grade=1)
def op_log():
    db = db_op.op_log
    try:
        val = db.query.with_entities(db.date,db.time,db.ip,db.user,db.access).order_by(desc(db.id)).limit(500).all()
        if val:
            tables = ['日期','时间','IP','用户','访问页面']
            return render_template('op_log.html',tables = tables,values = val)
        else:
            flash('获取数据错误!',"error")
            return render_template('Message.html')
    except Exception as e:
        flash(e,"error")
        return render_template('Message.html')
@page_examine.before_request
@check.login_required(grade=10)
def check_login(error=None):
    produce.Async_log(g.user, request.url)
@page_examine.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
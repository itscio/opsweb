#-*- coding: utf-8 -*-
import os
from flask import Flask,make_response,render_template,session,render_template_string,request,g
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from api import ajax_api,assets_add,publish_code,assets_query,record_publish,deployment_deploy
import index,login,logout
import socket
import time
from views import chart_center,publish,deploy,k8s,k8s_deploy
from views import sch_list,app_service
from views import business_m,Error,report,influxdb_m
from views import Assets,mysql_info,business,approval
from admin import examine,assets_manage,resource_pool
from Modules import init,produce,check
from flask_debugtoolbar import DebugToolbarExtension
class MyFlask(Flask):
    jinja_environment = init.FlaskEchartsEnvironment
app = MyFlask(__name__)
app.config.from_pyfile('conf/main.conf')
app.config.from_pyfile('conf/redis.conf')
app.config.from_pyfile('conf/task.conf')
app.config.from_pyfile('conf/sql.conf')
app.config.get('TRAP_HTTP_EXCEPTIONS')
task_servers = app.config.get('TASK_SERVERS')
DB = SQLAlchemy(app)
app.secret_key = os.urandom(24)
app.debug = False
limiter = init.web_limiter()
limiter = limiter.limiter
moment = Moment(app)
task_run = produce.Scheduler_backgroud()
toolbar = DebugToolbarExtension(app)
HOST = socket.gethostbyname(socket.gethostname())
app.register_blueprint(Assets.page_Assets)
app.register_blueprint(mysql_info.page_mysql_info)
app.register_blueprint(assets_manage.page_assets_manage)
app.register_blueprint(publish.page_publish)
app.register_blueprint(resource_pool.page_resource_pool)
app.register_blueprint(chart_center.page_chart_center)
app.register_blueprint(examine.page_examine)
app.register_blueprint(sch_list.page_sch_list)
app.register_blueprint(ajax_api.page_ajax_api)
app.register_blueprint(business_m.page_business_monitor)
app.register_blueprint(Error.page_error)
app.register_blueprint(business.page_business)
app.register_blueprint(approval.page_approval)
app.register_blueprint(deploy.page_deploy)
app.register_blueprint(assets_add.page_assets_add)
app.register_blueprint(assets_query.page_assets_query)
app.register_blueprint(login.page_login)
app.register_blueprint(logout.page_logout)
app.register_blueprint(index.page_index)
app.register_blueprint(publish_code.page_publish_code)
app.register_blueprint(report.page_report)
app.register_blueprint(influxdb_m.page_influxdb_m)
app.register_blueprint(record_publish.page_record_publish)
app.register_blueprint(app_service.page_app_service)
app.register_blueprint(k8s.page_k8s)
app.register_blueprint(k8s_deploy.page_k8s_deploy)
app.register_blueprint(deployment_deploy.page_deployment_deploy)
if HOST in task_servers:
    produce.scheduler_tasks()
task_run.Run()
@app.route('/')
@limiter.exempt
def main():
    session['Menu'] = {}
    return render_template('main.html')

@app.route('/mobile')
@limiter.exempt
@check.login_required(grade=1)
def mobile():
    produce.Async_log(g.user, request.url)
    return render_template('mobile/m_index.html')

@app.route('/webssh')
@limiter.exempt
@check.login_required(grade=1)
def webssh():
    produce.Async_log(g.user, request.url)
    url = "http://172.16.69.250:8000/"
    return render_template('webssh.html',url=url)

@app.errorhandler(404)
def page_not_found(error):
     resp = make_response(render_template('404.html',ym=time.strftime('%Y',time.localtime())),404)
     return resp

@app.errorhandler(405)
def method_not_allowed(error):
     resp = make_response(render_template_string("Method Not Allowed: 405 The method is not allowed for the requested URL!"),405)
     return resp
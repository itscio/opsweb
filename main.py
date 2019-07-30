#-*- coding: utf-8 -*-
from flask import Flask,make_response,render_template,render_template_string,request,g
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from api import ajax_api,assets_query,k8s_project_update
import index,login,logout
import time
import ssl
from flask_assets import Environment
from flask_mail import Mail
from view import chart_center,publish,deploy,k8s,k8s_deploy
from view import sch_list,app_service,k8s_manage
from view import business_m,report,influxdb_m
from view import Assets,business,approval
from view import work_order
from operation import examine,assets_manage,resource_pool
from module import tools,user_auth,produce
from flask_debugtoolbar import DebugToolbarExtension
import conf
class MyFlask(Flask):
    jinja_environment = conf.FlaskEchartsEnvironment
app = MyFlask(__name__)
DB = SQLAlchemy(app)
mail = Mail(app)
limiter = conf.web_limiter()
limiter = limiter.limiter
moment = Moment(app)
assets = Environment(app)
app.config.from_pyfile('conf/main.conf')
app.config.from_pyfile('conf/sql.conf')
app.config.from_pyfile('conf/redis.conf')
app.config.get('TRAP_HTTP_EXCEPTIONS')
app.secret_key = app.config.get('SECRET_KEY')
app.debug = False
task_run = produce.Scheduler_backgroud()
toolbar = DebugToolbarExtension(app)
ssl._create_default_https_context = ssl._create_unverified_context
app.register_blueprint(Assets.page_Assets)
app.register_blueprint(assets_manage.page_assets_manage)
app.register_blueprint(publish.page_publish)
app.register_blueprint(resource_pool.page_resource_pool)
app.register_blueprint(chart_center.page_chart_center)
app.register_blueprint(examine.page_examine)
app.register_blueprint(sch_list.page_sch_list)
app.register_blueprint(ajax_api.page_ajax_api)
app.register_blueprint(business_m.page_business_monitor)
app.register_blueprint(business.page_business)
app.register_blueprint(approval.page_approval)
app.register_blueprint(deploy.page_deploy)
app.register_blueprint(assets_query.page_assets_query)
app.register_blueprint(index.page_index)
app.register_blueprint(login.page_login)
app.register_blueprint(logout.page_logout)
app.register_blueprint(report.page_report)
app.register_blueprint(influxdb_m.page_influxdb_m)
app.register_blueprint(app_service.page_app_service)
app.register_blueprint(k8s.page_k8s)
app.register_blueprint(work_order.page_work_order)
app.register_blueprint(k8s_manage.page_k8s_manage)
app.register_blueprint(k8s_deploy.page_k8s_deploy)
app.register_blueprint(k8s_project_update.page_k8s_project_update)
produce.scheduler_tasks()
task_run.Run()
assets.register('js_file', conf.js_files())
assets.register('css_file', conf.css_files())
@app.route('/')
@limiter.exempt
def main():
    return render_template('main.html')

@app.route('/webssh')
@limiter.exempt
@user_auth.login_required(grade=1)
def webssh():
    tools.Async_log(g.user, request.url)
    return render_template('webssh.html',url=app.config.get('WEBSSH_URL'))

@app.errorhandler(404)
def page_not_found(error):
     resp = make_response(render_template('404.html',ym=time.strftime('%Y',time.localtime())),404)
     return resp

@app.errorhandler(405)
def method_not_allowed(error):
     resp = make_response(render_template_string("Method Not Allowed: 405 The method is not allowed for the requested URL!"),405)
     return resp

@app.route('/error')
def error():
    return render_template('error.html')

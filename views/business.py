#-*- coding: utf-8 -*-
from flask import Flask,Blueprint,render_template,g,flash,request
from module import user_auth,db_op,tools,db_idc,loging
from sqlalchemy import distinct,and_,func,desc
from pyecharts import Bar,Pie
from collections import defaultdict,OrderedDict
import redis
import datetime
import time
from functools import reduce
from influxdb import InfluxDBClient
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/sql.conf')
logging = loging.Error()
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
Redis = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
influxdb_host = app.config.get('INFLUXDB_HOST')
influxdb_port = app.config.get('INFLUXDB_PORT')
influxdb_user = app.config.get('INFLUXDB_USER')
influxdb_pw = app.config.get('INFLUXDB_PASSWORD')
influxdb_db = app.config.get('INFLUXDB_DB')
Influx_cli = InfluxDBClient(influxdb_host,influxdb_port,influxdb_user,influxdb_pw,'analysis_logs')
page_business = Blueprint('business', __name__)
@page_business.route('/business',methods = ['GET', 'POST'])
@page_business.route('/business/<id>',methods = ['GET', 'POST'])
def business(id=None):
    values = defaultdict()
    db_server = db_idc.idc_servers
    db_idc_id = db_idc.idc_id
    db_project = db_op.project_list
    db_third = db_idc.third_resource
    db_business = db_op.business
    db_project_third = db_op.project_third
    db_project_other = db_op.project_other
    business_info = [('项目','域名','业务','业务描述','联系人','联系方式')]
    bar = None
    busi_tables = ('日期', 'PV访问量', '平均响应时间', '4xx错误占比', '5xx错误占比')
    busi_counts = OrderedDict()
    try:
        if id:
            #获取业务信息
            try:
                key = 'op_business_counts_tmp'
                business_id = db_business.query.with_entities(db_business.id,db_business.business,db_business.describe,db_business.person,db_business.contact).all()
                business_id = {id:[business,describe,person,contact ] for id,business,describe,person,contact in business_id}
                business = business_id[int(id)]
            except Exception as e:
                logging.error(e)
            #获取项目信息
            business_values = db_project.query.with_entities(distinct(db_project.project)).filter(db_project.business_id==int(id)).all()
            other_values = db_project_other.query.with_entities(distinct(db_project_other.project)).filter(db_project_other.business_id == int(id)).all()
            if business_values:
                projects = [project[0] for project in business_values]
                #合并信息
                try:
                    for project in projects:
                        domain = db_project.query.with_entities(distinct(db_project.domain)).filter(db_project.project==project).all()
                        if domain:
                            domain = domain[0][0]
                        else:
                            domain = 'None'
                        project = [project,domain]
                        project.extend(business)
                        business_info.append(project)
                except Exception as e:
                    logging.error(e)
                try:
                    for project in projects:
                        #获取自有项目信息
                        project_val = db_project.query.with_entities(db_project.resource,func.count(db_project.id)).filter(db_project.project == project).group_by(db_project.resource).all()
                        if project_val:
                            for val in project_val:
                                Redis.hincrby(key,val[0],int(val[1]))
                        #获取第三方项目信息
                        project_third = db_project_third.query.with_entities(db_project_third.third_id,func.count(distinct(db_project_third.third_id))).filter(db_project_third.project==project).group_by(db_project_third.third_id).all()
                        if project_third:
                            project_third = [list(val) for val in project_third]
                            for i,val in enumerate(project_third):
                                vals = db_third.query.with_entities(db_third.resource_type).filter(db_third.id == val[0]).all()
                                if vals:
                                    project_third[i][0] = vals[0][0]
                            for vals in project_third:
                                Redis.hincrby(key,str(vals[0]),int(vals[1]))
                except Exception as e:
                    logging.error(e)
                try:
                    apps_vals = Redis.hgetall(key)
                    apps_vals = sorted(apps_vals.items(), key=lambda item: int(item[1]),reverse=True)
                    pie_vals = [val[0] for val in apps_vals]
                    pie_counts = [val[1] for val in apps_vals]
                    pie = Pie(width='100%', height='100%')
                    pie.add("", pie_vals, pie_counts, radius=[35, 75], is_yaxislabel_align=True, legend_orient='vertical',
                            legend_pos='left', is_toolbox_show=False, is_label_show=True, rosetype='area')
                    values['app'] = pie
                    Redis.delete(key)
                    values['app_lists'] = apps_vals
                except Exception as e:
                    logging.error(e)
                #统计机房信息和服务器数量
                try:
                    idcs = db_idc_id.query.with_entities(db_idc_id.id,db_idc_id.aid).all()
                    idcs = {int(val[0]):val[1] for val in idcs}
                    ids = db_project_third.query.with_entities(db_project_third.third_id).filter(db_project_third.project.in_(tuple(projects))).all()
                    third_ids = [id[0] for id in ids]
                    self_ips = db_project.query.with_entities(distinct(db_project.ip)).filter(db_project.project.in_(tuple(projects))).all()
                    self_ips = [ip[0] for ip in self_ips]
                    third_ips = db_third.query.with_entities(distinct(db_third.ip)).filter(db_third.id.in_(tuple(third_ids))).all()
                    third_ips = [ip[0] for ip in third_ips]
                    idc_vals = db_server.query.with_entities(db_server.idc_id,func.count(db_server.idc_id)).filter(db_server.ip.in_(tuple(self_ips+third_ips))).group_by(db_server.idc_id).all()
                    idc_vals = [list(val) for val in idc_vals]
                    for val in idc_vals:
                        val[0] = idcs[int(val[0])]
                    for val in idc_vals:
                        Redis.hincrby(key,val[0],val[1])
                    idc_vals = Redis.hgetall(key)
                    pie_idc = Pie(width='100%', height='100%')
                except Exception as e:
                    logging.error(e)
                if idc_vals:
                    try:
                        idc_vals = sorted(idc_vals.items(), key=lambda item: int(item[1]),reverse=True)
                        total_vals = reduce(lambda x,y:x+y ,[ int(vals[1]) for vals in idc_vals])
                        pie_vals = [val[0] for val in idc_vals]
                        pie_counts = [val[1] for val in idc_vals]
                        pie_idc.add("", pie_vals, pie_counts, radius=[35, 75], is_yaxislabel_align=True, legend_orient='vertical',
                                legend_pos='left', is_toolbox_show=False, is_label_show=True, rosetype='area')
                        Redis.delete(key)
                        idc_vals.append(['总计:',total_vals])
                    except Exception as e:
                        logging.error(e)
                values['idc'] = pie_idc
                values['idc_lists'] = idc_vals
                #获取业务相关性能数据
                try:
                    hosts = []
                    dt = datetime.datetime.now()
                    host_vals = [ infos[1].split(',') for infos in business_info[1:]]
                    for vals in host_vals:
                        for val in vals:
                            hosts.append(val)
                except Exception as e:
                    logging.error(e)
                year = time.strftime('%Y',time.localtime())
                for i in range(2,7):
                    info = []
                    ot = dt - datetime.timedelta(days=i - 1)
                    nt = dt - datetime.timedelta(days=i - 2)
                    ot = ot.strftime('%Y-%m-%dT00:00:00Z')
                    nt = nt.strftime('%Y-%m-%dT00:00:00Z')
                    try:
                        pv_sum = [0,]
                        for host in hosts:
                            cmd = 'select sum(mean_pv) from ' + 'analysis%s' %year + " where time >='%s' and time < '%s' and host = '%s';" % (ot, nt, host)
                            result = Influx_cli.query(cmd)
                            if result:
                                for infos in result.get_points():
                                    infos = infos
                                    if infos:
                                        pv_sum.append(infos['sum']*60)
                        if pv_sum:
                            pv_sum = reduce(lambda x,y:x+y,pv_sum)
                        else:
                            pv_sum = 0.0
                        info.append(int(pv_sum))
                    except Exception as e:
                        logging.error(e)
                    try:
                        avg_resp = [0,]
                        for host in hosts:
                            cmd = 'select mean(mean_avg_resp) from ' + 'analysis%s' %year + " where time >='%s' and time < '%s'and host = '%s';" % (ot, nt, host)
                            result = Influx_cli.query(cmd)
                            if result:
                                for infos in result.get_points():
                                    infos = infos
                                if infos:
                                    avg_resp.append(infos['mean'])
                        if avg_resp:
                            avg_resp = reduce(lambda x,y:x+y,avg_resp)
                        else:
                            avg_resp = 0.0
                        info.append('%.3f' %avg_resp+'s')
                    except Exception as e:
                        logging.error(e)
                    try:
                        s4 = [0,]
                        for host in hosts:
                            cmd = 'select sum(mean_status_4xx) from ' + 'analysis%s' %year + " where time >='%s' and time < '%s' and host = '%s';" % (ot, nt, host)
                            result = Influx_cli.query(cmd)
                            if result:
                                for infos in result.get_points():
                                    infos = infos
                                if infos:
                                    s4.append(infos['sum']*60/pv_sum)
                        if s4:
                            s4 = reduce(lambda x,y:x+y,s4)*100
                        else:
                            s4 = 0.0
                        info.append('%.3f' % s4+'%')
                        s5 = [0,]
                        for host in hosts:
                            cmd = 'select sum(mean_status_5xx) from ' + 'analysis%s' %year + " where time >='%s' and time < '%s' and host = '%s';" % (ot, nt, host)
                            result = Influx_cli.query(cmd)
                            if result:
                                for infos in result.get_points():
                                    infos = infos
                                if infos:
                                    s5.append(infos['sum']*60/pv_sum)
                        if s5:
                            s5 = reduce(lambda x,y:x+y,s5)*100
                        else:
                            s5 = 0.0
                        info.append('%.3f' % s5+'%')
                    except Exception as e:
                        logging.error(e)
                    busi_counts[ot.split('T')[0]] = info
            if other_values:
                for val in other_values:
                    jar_vals = [val[0],'']
                    jar_vals.extend(business)
                    business_info.append(jar_vals)
        else:
            #获取业务列表
            VALS = db_business.query.with_entities(db_business.id,db_business.business,db_business.describe).order_by(db_business.id).all()
            vals = {val[0]:val for val in VALS}
            busi_vals = {val[0]: val[1] for val in VALS}
            #获取各业务使用web应用实例数量
            web_vals = db_project.query.with_entities(db_project.business_id,func.count(db_project.business_id)).filter(and_(db_project.resource.in_(('php','tomcat','python','java')),db_project.business_id != 0)).group_by(db_project.business_id).order_by(desc(func.count(db_project.business_id))).all()
            pro_vals = [val[0] for val in web_vals]
            jar_vals = db_project_other.query.with_entities(db_project_other.business_id).group_by(db_project_other.business_id).all()
            jar_vals = [val[0] for val in jar_vals]
            for val in jar_vals:
                if val not in pro_vals:
                    pro_vals.append(val)
            values['business'] = [vals[val] for val in pro_vals if val in vals ]
            project_vals = [busi_vals[val[0]] for val in web_vals if val[0] in busi_vals ]
            project_counts = [val[1] for val in web_vals]
            bar = Bar(width='110%',height='250px')
            bar.add("线上业务web应用实例数量", project_vals, project_counts,mark_point=["max", "min"],is_yaxislabel_align=True,is_toolbox_show=False,xaxis_interval=0,xaxis_rotate=30)
    except Exception as e:
        flash(e)
        return render_template('Message.html')
    return render_template('business.html',values=values,id=id,business_info = business_info,bar=bar,busi_counts=busi_counts,busi_tables=busi_tables)
@page_business.before_request
@user_auth.login_required(grade=1)
def check_login(exception = None):
    tools.Async_log(g.user, request.url)
@page_business.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
    db_idc.DB.session.remove()
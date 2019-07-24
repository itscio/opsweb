#-*- coding: utf-8 -*-
from flask import Blueprint,render_template,request,g
from module import tools,user_auth,loging,db_op,db_idc
import time
import datetime
import json
import redis
from pyecharts import Bar,Line
from flask_sqlalchemy import SQLAlchemy
from influxdb import InfluxDBClient
from collections import OrderedDict,defaultdict
from sqlalchemy import func
import urllib
from pyecharts import Pie
import conf
app = conf.app
logging = loging.Error()
DB = SQLAlchemy(app)
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
RC = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
redis_data = app.config.get('REDIS_DATA')
RC_CLUSTER = redis.StrictRedis(host=redis_data, port=redis_port,decode_responses=True)
influxdb_host = app.config.get('INFLUXDB_HOST')
influxdb_port = app.config.get('INFLUXDB_PORT')
influxdb_user = app.config.get('INFLUXDB_USER')
influxdb_pw = app.config.get('INFLUXDB_PASSWORD')
influxdb_db = app.config.get('INFLUXDB_DB')
Influx_cli = InfluxDBClient(influxdb_host,influxdb_port,influxdb_user,influxdb_pw,'analysis_logs')
page_influxdb_m=Blueprint('influxdb_m',__name__)
@page_influxdb_m.route('/interface_monitor')
@user_auth.login_required(grade=1)
def interface_monitor():
    try:
        dd = time.strftime('%Y-%m-%d', time.localtime())
        Keys = {'bef': '同比', 'old': '环比',
                'mean_avg_resp': '平均响应时间',
                'mean_status_5xx': '5xx状态码',
                'mean_status_4xx': '4xx状态码',
                'mean_resp_1000': '响应时间大于1s',
                'mean_pv': 'pv访问量'}
        alarm_key = 'interface_alarm_%s' % dd
        alarms = RC.hgetall(alarm_key)
    except Exception as e:
        logging.error(e)
    if alarms:
        alarms = {key: eval(alarms[key]) for key in alarms}
        alarms = sorted(alarms.items(), key=lambda item: item[1]['incr'],reverse=True)
    return render_template('interface_monitor.html',alarms=alarms,Keys=Keys)

@page_influxdb_m.route('/interface_report')
@user_auth.login_required(grade=8)
def interface_report():
    try:
        Bars = []
        searchs = []
        db_project = db_op.project_list
        db_idcs = db_idc.idc_id
        db_servers = db_idc.idc_servers
        db_project_third = db_op.project_third
        db_third = db_idc.third_resource
        Infos = defaultdict()
        values = OrderedDict()
        dt = datetime.datetime.now()
        #获取域名列表
        hosts = RC_CLUSTER.smembers('api_domain_lists_%s' %time.strftime('%Y-%m-%d', time.localtime()))
        hosts = [host for host in hosts]
        if hosts:
            searchs = json.dumps([{"id": str(i), "text": str(host)} for i, host in enumerate(hosts)])
        #获取域名和接口信息
        if  'business_bigdata_select_host' in request.cookies and 'business_bigdata_select_uri' in request.cookies:
            host = request.cookies['business_bigdata_select_host']
            uri = urllib.parse.unquote(request.cookies['business_bigdata_select_uri'])
            #获取接口相关的资产信息
            projects = db_project.query.with_entities(db_project.ip,db_project.ssh_port,db_project.resource).filter(db_project.domain.like('%{0},%'.format(host))).all()
            if projects:
                idc_lists = db_idcs.query.with_entities(db_idcs.id,db_idcs.aid).all()
                idc_lists = {idcs[0]:idcs[-1] for idcs in idc_lists}
                third_lists = db_third.query.with_entities(db_third.id,db_third.resource_type).all()
                third_lists = {third[0]: third[-1] for third in third_lists}
                ips = [val[0] for val in projects]
                resource = projects[0][-1]
                idc_ids = db_servers.query.with_entities(db_servers.idc_id,func.count(db_servers.idc_id)).filter(db_servers.ip.in_(tuple(ips))).group_by(db_servers.idc_id).all()
                if idc_ids:
                    idc_ids = [list(ids) for ids in idc_ids]
                    for ids in idc_ids:
                        ids[0] = idc_lists[ids[0]]
                    RC.delete('idc_incrs')
                    for ids in idc_ids:
                        RC.hincrby('idc_incrs',ids[0],ids[1])
                    idc_ids = RC.hgetall('idc_incrs')
                    idc_attr = [ids for ids in idc_ids]
                    idc_vals = [int(idc_ids[ids]) for ids in idc_ids]
                    pie = Pie("%s台%s服务器机房分布" %(len(set(projects)),resource), width='100%', height='270px', title_pos='center',title_text_size=14)
                    pie.add("", idc_attr, idc_vals, is_label_show=True, is_toolbox_show=False,is_legend_show=False,
                                   legend_orient='vertical', legend_pos='left', radius=[0, 65], is_random=True)
                    Infos['pie'] = pie
            project = db_project.query.with_entities(db_project.project).filter(db_project.domain.like('%{0},%'.format(host))).all()
            #获取接口相关的应用服务资源
            if project:
                project = project[0][0]
                third_vals = db_project_third.query.with_entities(db_project_third.third_id,func.count(db_project_third.third_id)).filter(db_project_third.project==project).group_by(db_project_third.third_id).all()
                if third_vals:
                    third_vals = [list(val) for val in third_vals]
                    for val in third_vals:
                        val[0] = third_lists[val[0]]
                    RC.delete('third_incrs')
                    for val in third_vals:
                        RC.hincrby('third_incrs', val[0], val[1])
                    third_vals = RC.hgetall('third_incrs')
                    third_vals[resource] = len(projects)
                    third_attr = [val for val in third_vals]
                    third_counts = [int(third_vals[val]) for val in third_vals]
                    pie_third = Pie("应用服务资源分布", width='100%', height='270px', title_pos='center',
                              title_text_size=14)
                    pie_third.add("", third_attr, third_counts, is_label_show=True, is_toolbox_show=False,
                            legend_orient='vertical', legend_pos='right', radius=[55, 65], is_random=True,is_legend_show=False,)
                    Infos['pie_third'] = pie_third
            #接口性能数据获取
            year = time.strftime('%Y',time.localtime())
            for i in range(2,9):
                ot = dt - datetime.timedelta(days=i-1)
                nt = dt - datetime.timedelta(days=i-2)
                ot = ot.strftime('%Y-%m-%dT00:00:00Z')
                nt = nt.strftime('%Y-%m-%dT00:00:00Z')
                try:
                    pv_sum = 0.0
                    cmd = 'select sum(mean_pv) from '+ 'analysis%s' %year + " where time >='%s' and time < '%s' and host='%s' and uri = '%s';" %(ot,nt,host,uri)
                    result = Influx_cli.query(cmd)
                    if result:
                        for infos in result.get_points():
                            infos = infos
                        if infos:
                            pv_sum = infos['sum']
                except Exception as e:
                    logging.error(e)
                try:
                    values['avg_resp'] = 0.0
                    cmd = 'select mean(mean_avg_resp) from ' + 'analysis%s' %year + " where time >='%s' and time < '%s'and host='%s' and uri = '%s';" %(ot,nt,host,uri)
                    result = Influx_cli.query(cmd)
                    if result:
                        for infos in result.get_points():
                            infos = infos
                        if infos:
                            values['avg_resp:%s' %ot.split('T')[0]] = '%.2f'%infos['mean']
                except Exception as e:
                    logging.error(e)
                try:
                    s4 = 0.0
                    cmd = 'select sum(mean_status_4xx) from ' + 'analysis%s' %year + " where time >='%s' and time < '%s' and host='%s' and uri = '%s';" %(ot,nt,host,uri)
                    result = Influx_cli.query(cmd)
                    if result:
                        for infos in result.get_points():
                            infos = infos
                        if infos:
                            s4 = infos['sum']
                    s5 = 0.0
                    cmd = 'select sum(mean_status_5xx) from ' + 'analysis%s' %year + " where time >='%s' and time < '%s' and host='%s' and uri = '%s';" %(ot,nt,host,uri)
                    result = Influx_cli.query(cmd)
                    if result:
                        for infos in result.get_points():
                            infos = infos
                        if infos:
                            s5 = infos['sum']
                    if pv_sum >0:
                        values['status_sum:%s' % ot.split('T')[0]] = float('%.2f' % (float(s4 + s5) / pv_sum * 100))
                except Exception as e:
                    logging.error(e)
                values['pv_sum:%s'%ot.split('T')[0]] = int(pv_sum)*60
            #接口性能展示
            if values:
                #pv总数
                bar_pv = Bar("PV访问量", width='105%', height='270px', title_pos='center',
                              title_text_size=14)
                vals = [(val.split(':')[-1],values[val]) for val in values if 'pv_sum:' in val]
                if vals:
                    bar_vals = [val[0] for val in vals]
                    bar_counts = [val[-1] for val in vals]
                    bar_pv.add('', bar_vals, bar_counts, is_label_show=True, is_toolbox_show=False,legend_orient='vertical', legend_pos='right', xaxis_interval=0,is_random=True)
                    Bars.append(bar_pv)
                #平均响应时间
                line_resp = Line("平均响应时间", width='105%', height='270px', title_pos='center',title_text_size=14)
                vals = [(val.split(':')[-1], values[val]) for val in values if 'avg_resp:' in val]
                if vals:
                    line_vals = [val[0] for val in vals]
                    line_counts = [val[-1] for val in vals]
                    line_resp.add('', line_vals, line_counts, is_label_show=True, is_toolbox_show=False, legend_orient='vertical',
                               legend_pos='right', xaxis_interval=0, yaxis_formatter='s',is_random=True,is_smooth=False,mark_point=["min","max"])
                    Bars.append(line_resp)
                #错误状态码占比
                line_status = Line("错误码占比", width='105%', height='270px', title_pos='center',
                               title_text_size=14)
                vals = [(val.split(':')[-1], values[val]) for val in values if 'status_sum:' in val]
                if vals:
                    line_vals = [val[0] for val in vals]
                    line_counts = [val[-1] for val in vals]
                    line_status.add('', line_vals, line_counts,is_fill=True,is_label_show=True,is_smooth=False,is_toolbox_show=False, legend_orient='vertical',
                                 legend_pos='right', xaxis_interval=0, yaxis_formatter='%', is_random=True,mark_line=["max", "min"])
                    Bars.append(line_status)
    except Exception as e:
        logging.error(e)
    return render_template('interface_report.html',Bars=Bars,Infos=Infos,searchs=searchs)

@page_influxdb_m.before_request
@user_auth.login_required(grade=10)
def check_login(exception = None):
    tools.Async_log(g.user, request.url)

@page_influxdb_m.teardown_request
def db_remove(error=None):
    db_idc.DB.session.remove()
    db_op.DB.session.remove()
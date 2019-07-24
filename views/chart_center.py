#-*- coding: utf-8 -*-
from flask import Blueprint,render_template,flash,g,request,make_response
from module import user_auth,loging,tools,db_idc,db_op,MyForm
import redis
import urllib
import json
from functools import reduce
from influxdb import InfluxDBClient
import importlib
from sqlalchemy import func,desc,distinct
import time,datetime
from elasticsearch import Elasticsearch
from pyecharts import Bar,Pie,Line
from flask_sqlalchemy import SQLAlchemy
from collections import defaultdict,OrderedDict
import conf
app = conf.app
DB = SQLAlchemy(app)
logging = loging.Error()
es_hosts = app.config.get('ES_HOSTS')
es = Elasticsearch(hosts=es_hosts)
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
RC = Redis = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
redis_data = app.config.get('REDIS_DATA')
RC_CLUSTER = redis.StrictRedis(host=redis_data, port=redis_port,decode_responses=True)
influxdb_host = app.config.get('INFLUXDB_HOST')
influxdb_port = app.config.get('INFLUXDB_PORT')
influxdb_user = app.config.get('INFLUXDB_USER')
influxdb_pw = app.config.get('INFLUXDB_PASSWORD')
influxdb_db = 'analysis_logs'
Influx_cli = InfluxDBClient(influxdb_host,influxdb_port,influxdb_user,influxdb_pw,influxdb_db)
page_chart_center = Blueprint('chart_center', __name__)
@page_chart_center.route('/chart_error_status',methods = ['GET', 'POST'])
@user_auth.login_required(grade=1)
def chart_center_status():
    try:
        td = time.strftime("%Y-%m-%d", time.localtime())
        form = MyForm.MyForm_input()
        tm = datetime.datetime.now() - datetime.timedelta(minutes=1)
        tm = tm.strftime('%H:%M')
        tm = '%s_%s'%(time.strftime('%Y-%m-%d',time.localtime()),tm)
        if form.submit.data:
            if form.input.data:
                td,tm = form.input.data.strip().split()
        # 获取4xx,5xx状态码数据
        err_4xx = 'error_4xx_%s' % td
        err_5xx = 'error_5xx_%s' % td
        err_4xx_data = [eval(v) for v in RC.lrange(err_4xx, 0, -1)]
        err_5xx_data = [eval(v) for v in RC.lrange(err_5xx, 0, -1)]
        # 获取并发pv
        INTERNET_DATA = [eval(v) for v in RC.lrange('internet_access_%s' % td, 0, -1)]
        INTERNET_DATA = {DATA[0]: DATA[1] for DATA in INTERNET_DATA}
        attr_4_p = []
        vals_4_p = []
        for i, key in enumerate([DATA[0] for DATA in err_4xx_data]):
            if key in INTERNET_DATA.keys():
                v = float('%.3f' % ((float([DATA[1] for DATA in err_4xx_data][i]) / float(INTERNET_DATA[key])) * 100))
                attr_4_p.append(key)
                vals_4_p.append(v)
        attr_5_p = []
        vals_5_p = []
        for i, key in enumerate([DATA[0] for DATA in err_5xx_data]):
            if key in INTERNET_DATA.keys():
                v = float('%.3f' % ((float([DATA[1] for DATA in err_5xx_data][i]) / float(INTERNET_DATA[key])) * 100))
                attr_5_p.append(key)
                vals_5_p.append(v)
        Lines = Line('线上服务错误状态码(pv占比)', width='110%', height='250px', title_pos='center', title_text_size=14)
        Lines.add('4xx', attr_4_p, vals_4_p, is_toolbox_show=False, is_smooth=True, mark_point=["max", "min"],
                     mark_point_symbolsize=60, yaxis_formatter='%', is_random=True, is_datazoom_show=True,
                     datazoom_range=[v for v in range(100, 10)], datazoom_type='both',legend_pos='80%')
        Lines.add('5xx', attr_5_p, vals_5_p, is_toolbox_show=False, is_smooth=True, mark_point=["max", "min"],
                     mark_point_symbolsize=60, yaxis_formatter='%', is_random=True, is_datazoom_show=True,
                     datazoom_range=[v for v in range(100, 10)], datazoom_type='both',legend_pos='80%')
        infos = []
        # 错误状态码
        code_key = 'error_logs_status_%s' %tm
        if RC.exists(code_key):
            vals = RC.hgetall(code_key)
            vals = sorted(vals.items(), key=lambda item: int(item[1]), reverse=True)
            bar = Bar("%s线上错误状态码统计" %tm,width='100%', height='100%',title_pos='center',title_text_size=14)
            bar_vals = [val[0] for val in vals]
            bar_counts = [int(val[1]) for val in vals]
            bar.add("", bar_vals, bar_counts, is_label_show=True, is_toolbox_show=False, legend_orient='vertical',legend_pos='right',xaxis_interval=0,is_random=True)
            infos.append(bar)
            code = bar_vals[0]
            #最高错误状态域名
            host_key = 'error_logs_domain_%s_%s' % (code, tm)
            if RC.exists(host_key):
                vals = RC.hgetall(host_key)
                vals = sorted(vals.items(), key=lambda item: int(item[1]), reverse=True)
                pie_domain = Pie("%s状态码域名分布" % code, width='100%', height='100%',title_pos='center',title_text_size=14)
                end=8
                if len(vals) <=8:
                    end = len(vals)
                pie_vals = [val[0] for val in vals[:end]]
                pie_counts = [int(val[1]) for val in vals[:end]]
                pie_domain.add("", pie_vals, pie_counts, is_label_show=True, is_toolbox_show=False, legend_orient='vertical',legend_pos='right', radius=[5, 65],is_random=True)
                infos.append(pie_domain)
                #最高域名的接口
                end = 4
                if len(vals) <=4:
                    end = len(vals)
                for domain in pie_vals[:end]:
                    uri_key = 'error_logs_domain_%s_%s_%s' % (code,domain, tm)
                    if RC.exists(uri_key):
                        vals = RC.hgetall(uri_key)
                        vals = sorted(vals.items(), key=lambda item: int(item[1]), reverse=True)
                        pie_uri = Pie("%s域名接口分布" % domain, width='100%', height='100%',title_pos='center',title_text_size=14)
                        end = 5
                        if len(vals) <= 5:
                            end = len(vals)
                        pie_val = [val[0] for val in vals[:end]]
                        pie_count = [int(val[1]) for val in vals[:end]]
                        pie_uri.add("", pie_val, pie_count, is_label_show=True, is_toolbox_show=False, legend_orient='vertical',legend_pos='right', radius=[5, 65],is_random=True)
                        infos.append(pie_uri)
        return render_template('chart_error_status.html', infos=infos,Lines = Lines,form=form)
    except Exception as e:
        flash('暂时没有相关数据.')
        logging.error(e)
        return render_template('Message.html')

@page_chart_center.route('/chart_time_detail',methods = ['GET', 'POST'])
@user_auth.login_required(grade=1)
def chart_time_detail():
    try:
        td = time.strftime("%Y-%m-%d", time.localtime())
        form = MyForm.MyForm_input()
        tm = datetime.datetime.now() - datetime.timedelta(minutes=1)
        tm = tm.strftime('%H:%M')
        tm = '%s_%s'%(time.strftime('%Y-%m-%d',time.localtime()),tm)
        if form.submit.data:
            if form.input.data:
                td,tm = form.input.data.strip().split()
        now_time = time.strftime("%H%M", time.localtime())
        NOW_DATA = [eval(v) for v in RC.lrange('internet_access_%s' % td, 0, -1)]
        NOW_DATA = {val[0]: val[1] for val in NOW_DATA if int(val[0].replace(':', '')) <= int(now_time)}
        Lines = []
        line = Line('线上服务响应时间段占比', width='110%', height='250px', title_pos='center', title_text_size=14)
        for k in ['0-100','100-200', '200-500', '500-1000', '1000-3000', '3000+']:
            Key = 'es_get_time_%s_%s' % (k, td)
            vals = RC.hgetall(Key)
            vals = sorted(vals.items(), key=lambda item: int(item[0].split('_')[-1].replace(':', '')))
            line_attrs = [val[0].split('_')[-1] for val in vals]
            line_vals = [eval(val[1])[0] for val in vals]
            line_attrs_p = [key for key in line_attrs if key in NOW_DATA.keys()]
            line_vals_p = [float('%.2f' % ((float(line_vals[i]) / NOW_DATA[key]) * 100)) for i, key in
                           enumerate(line_attrs) if
                           key in NOW_DATA.keys()]
            for i, val in enumerate(line_vals_p):
                if val > 100:
                    line_vals_p[i] = 100
            line.add('%sms' % k, line_attrs_p, line_vals_p, is_toolbox_show=False, is_smooth=True,
                        mark_point=["max", "min"], mark_point_symbolsize=80,legend_pos='55%', legend_top='top', is_datazoom_show=True,
                        datazoom_range=[v for v in range(100, 10)], datazoom_type='both', yaxis_formatter='%')
        Lines.append(line)
        infos = []
        host_vals_1 = None
        host_vals_3 = None
        total_key = 'total_access_%s' % tm
        total_counts = RC.get(total_key)
        #响应时间段详细统计
        try:
            counts = defaultdict()
            host_key = 'response_time_domain_%s_%s' % ('1000-3000', tm)
            if RC.exists(host_key):
                bar_host = Bar("%s线上服务响应时间域名占比" % tm, width='100%', height='100%', title_pos='center',
                               title_text_size=14)
                vals = RC.hgetall(host_key)
                vals = sorted(vals.items(),key=lambda item:int(item[1]),reverse = True)
                end=8
                if len(vals) <=8:
                    end = len(vals)
                host_vals_1 = [val[0] for val in vals[:end]]
                counts['1000-3000']= vals[0][1]
                host_counts = [float('%.3f' % ((float(val[1]) / float(total_counts)) * 100)) for val in vals[:end]]
                bar_host.add('1000-3000', host_vals_1, host_counts, is_label_show=True, is_toolbox_show=False, legend_orient='vertical',legend_pos='right',xaxis_interval=0,is_random=True,xaxis_rotate=15,yaxis_formatter='%')
                infos.append(bar_host)
            host_key = 'response_time_domain_%s_%s' % ('3000+', tm)
            if RC.exists(host_key):
                bar_host_3 = Bar("%s线上服务响应时间域名占比" % tm, width='100%', height='100%', title_pos='center',
                                 title_text_size=14)
                vals = RC.hgetall(host_key)
                vals = sorted(vals.items(),key=lambda item:int(item[1]),reverse = True)
                end=8
                if len(vals) <=8:
                    end = len(vals)
                host_vals_3 = [val[0] for val in vals[:end]]
                counts['3000+']= vals[0][1]
                host_counts = [float('%.3f' % ((float(val[1]) / float(total_counts)) * 100)) for val in vals[:end]]
                bar_host_3.add('3000+', host_vals_3, host_counts, is_label_show=True, is_toolbox_show=False, legend_orient='vertical',legend_pos='right',xaxis_interval=0,is_random=True,xaxis_rotate=15,yaxis_formatter='%')
                infos.append(bar_host_3)
        except Exception as e:
            logging.error(e)
        else:
            try:
                if host_vals_1 and host_vals_3:
                    end = 4
                    if len(host_vals_1) <= 4:
                        end = len(host_vals_1)
                    for domain in host_vals_1[:end]:
                        uri_key = 'response_time_domain_%s_%s_%s' % (domain, '1000-3000', tm)
                        if RC.exists(uri_key):
                            bar_uri = Bar("%s域名接口响应时间占比" % domain, width='100%', height='100%', title_pos='center',
                                          title_text_size=14)
                            vals = RC.hgetall(uri_key)
                            vals = sorted(vals.items(),key=lambda item:int(item[1]),reverse = True)
                            if len(vals) <=4:
                                end = len(vals)
                            uri_vals = [val[0] for val in vals[:end]]
                            uri_counts = [float('%.3f' % ((float(val[1]) / float(counts['1000-3000'])) * 100)) for val in vals[:end]]
                            bar_uri.add('1000-3000', uri_vals, uri_counts, is_label_show=True, is_toolbox_show=False, legend_orient='vertical',legend_pos='right',xaxis_interval=0,is_random=True,xaxis_rotate=15,yaxis_formatter='%')
                            infos.append(bar_uri)
                    if len(host_vals_3) <= 4:
                            end = len(host_vals_3)
                    for domain in host_vals_1[:end]:
                        uri_key = 'response_time_domain_%s_%s_%s' % (domain, '3000+', tm)
                        if RC.exists(uri_key):
                            bar_uri_3 = Bar("%s域名接口响应时间占比" % domain, width='100%', height='100%', title_pos='center',
                                            title_text_size=14)
                            vals = RC.hgetall(uri_key)
                            vals = sorted(vals.items(),key=lambda item:int(item[1]),reverse = True)
                            if len(vals) <=4:
                                end = len(vals)
                            uri_vals = [val[0] for val in vals[:end]]
                            uri_counts = [float('%.3f' % ((float(val[1]) / float(counts['3000+'])) * 100)) for val in vals[:end]]
                            bar_uri_3.add('3000+', uri_vals, uri_counts, is_label_show=True, is_toolbox_show=False, legend_orient='vertical',legend_pos='right',xaxis_interval=0,is_random=True,xaxis_rotate=15,yaxis_formatter='%')
                            infos.append(bar_uri_3)
            except Exception as e:
                logging.error(e)
        return render_template('chart_time_detail.html',infos=infos,Lines=Lines,form=form)
    except Exception as e:
        logging.error(e)
        return render_template('Message.html')

@page_chart_center.route('/chart_third_resource')
@user_auth.login_required(grade=1)
def chart_third_resource():
    idc_ids= {}
    idc_vals = {}
    db_idc_id = db_idc.idc_id
    db_project = db_op.project_list
    db_third = db_idc.third_resource
    db_servers = db_idc.idc_servers
    th = time.strftime('%H',time.localtime())
    try:
        Key = 'chart_third_resource_bar_%s' %th
        if Redis.exists(Key):
            bar_values = eval(Redis.hget(Key,'bar_values'))
            bar_counts = eval(Redis.hget(Key,'bar_counts'))
            values = eval(Redis.hget(Key,'values'))
        else:
            #获取机房信息
            IDS_val = db_idc_id.query.with_entities(distinct(db_idc_id.aid)).group_by(db_idc_id.aid).all()
            for aid in IDS_val:
                #获取机房机柜ID
                cid = db_idc_id.query.with_entities(db_idc_id.id).filter(db_idc_id.aid == aid[0]).all()
                cid = [val[0] for val in cid]
                idc_ids[aid[0]] = cid
            #统计应用服务实例数量
            project_values = db_project.query.with_entities(db_project.resource,
                                                        func.count(db_project.resource)).group_by(
                db_project.resource).order_by(desc(func.count(db_project.resource))).all()
            third_values = db_third.query.with_entities(db_third.resource_type,func.count(db_third.resource_type)).group_by(db_third.resource_type).order_by(desc(func.count(db_third.resource_type))).all()
            values = project_values+third_values
            bar_values = [str(value[0]) for value in values]
            bar_counts = [int(value[-1]) for value in values]
            Redis.hset(Key,'values',values)
            Redis.hset(Key,'bar_values',bar_values)
            Redis.hset(Key, 'bar_counts', bar_counts)
            Redis.expire(Key, 7200)
        bar = Bar("线上应用服务实例汇总",title_pos='center',width='110%',height='300px')
        bar.add("",bar_values,bar_counts, mark_point=["max", "min"], is_yaxislabel_align=True,is_toolbox_show=False, xaxis_interval=0,legend_pos='100%',xaxis_rotate=30)
        #取前8个最多的实例
        for value in values[:8]:
            app = str(value[0])
            Key = 'chart_third_resource_%s_%s' %(th,app)
            if Redis.exists(Key):
                pie_counts = eval(Redis.hget(Key,'pie_counts'))
                pie_vals = eval(Redis.hget(Key,'pie_vals'))
            else:
                pie_counts=[]
                pie_vals= []
                if app in ['php','tomcat','python','java']:
                    vals  = db_project.query.with_entities(db_project.ip).filter(db_project.resource==app).all()
                else:
                    vals = db_third.query.with_entities(db_third.ip).filter(db_third.resource_type == app).all()
                ips = [str(ip[0]) for ip in vals]
                #获取服务实例对应的机房机柜ID
                vals = db_servers.query.with_entities(db_servers.idc_id,func.count(db_servers.idc_id)).filter(db_servers.ip.in_(tuple(ips))).group_by(db_servers.idc_id).all()
                for key in idc_ids:
                    RC.delete('op_chart_%s_%s' % (key, g.secret_key))
                for idc_id,counts in vals:
                    for key in idc_ids:
                        if idc_id in idc_ids[key]:
                            RC.incrby('op_chart_%s_%s' %(key,g.secret_key),int(counts))
                for key in idc_ids:
                    vals = RC.get('op_chart_%s_%s' %(key,g.secret_key))
                    if vals:
                        pie_counts.append(int(vals))
                        pie_vals.append(key)
                Redis.hset(Key,'pie_counts',pie_counts)
                Redis.hset(Key,'pie_vals', pie_vals)
                Redis.expire(Key,7200)
            pie = Pie(width='100%',height='100%')
            pie.add("", pie_vals, pie_counts,is_label_show=True,is_toolbox_show=False,legend_orient='vertical',legend_pos='right',radius=[0, 55])
            idc_vals[app] = pie
        return render_template('chart_third_resource.html',bar=bar,idc_vals=idc_vals)
    except Exception as e:
        logging.error(e,"error")
        flash('获取数据错误!',"error")
        return render_template('Message.html')

@page_chart_center.route('/chart_domain_status',methods = ['GET', 'POST'])
@user_auth.login_required(grade=1)
def chart_center_hosts():
    try:
        bar_upstreams = []
        form = MyForm.MyForm_input()
        tm = datetime.datetime.now() - datetime.timedelta(minutes=1)
        tm = tm.strftime('%H:%M')
        tm = '%s_%s'%(time.strftime('%Y-%m-%d',time.localtime()),tm)
        if form.submit.data:
            if form.input.data:
                tm = form.input.data.strip().split()[-1]
        domain_key = 'domain_counts_%s' %tm
        if RC.exists(domain_key):
            try:
                vals = RC.hgetall(domain_key)
                if vals:
                    vals = sorted(vals.items(), key=lambda item: int(item[1]), reverse=True)
                    bar_vals_1 = [val[0] for val in vals if '1000-3000' in val[0].split(':')]
                    bar_vals_3 = [val[0] for val in vals if '3000+' in val[0].split(':')]
                    if bar_vals_1:
                        thost = bar_vals_1[0]
                        counts_key = 'counts_%s_%s' % (thost, tm)
                        if RC.exists(counts_key):
                            bar_hosts = Bar("%s应用服务实例分布" % tm, width='100%', height='100%', title_pos='center',
                                            title_text_size=14)
                            vals = RC.hgetall(counts_key)
                            if vals:
                                vals = sorted(vals.items(), key=lambda item: int(item[1]), reverse=True)
                                total_counts = float(reduce(lambda x, y: x + y, [int(val[1]) for val in vals]))
                                end = 15
                                if len(vals) <15:
                                    end = len(vals)
                                bar_attr = [val[0].split(',')[-1] for val in vals[:end]]
                                bar_count = [float('%.2f'%((int(val[1])/total_counts)*100)) for val in vals[:end]]
                                bar_hosts.add('%sms'%thost, bar_attr, bar_count, is_label_show=True, is_toolbox_show=False,
                                        legend_orient='vertical', legend_pos='right', xaxis_interval=0, is_random=True,yaxis_formatter='%',xaxis_rotate=15)
                                bar_upstreams.append(bar_hosts)
                        thost = bar_vals_1[1]
                        counts_key = 'counts_%s_%s' % (thost, tm)
                        if RC.exists(counts_key):
                            bar_hosts_1 = Bar("%s应用服务实例分布" % tm, width='100%', height='100%', title_pos='center',
                                              title_text_size=14)
                            vals = RC.hgetall(counts_key)
                            if vals:
                                vals = sorted(vals.items(), key=lambda item: int(item[1]), reverse=True)
                                total_counts = float(reduce(lambda x, y: x + y, [int(val[1]) for val in vals]))
                                end = 15
                                if len(vals) < 15:
                                    end = len(vals)
                                bar_attr = [val[0].split(',')[-1] for val in vals[:end]]
                                bar_count = [float('%.2f' % ((int(val[1]) / total_counts) * 100)) for val in vals[:end]]
                                bar_hosts_1.add('%sms' % thost, bar_attr, bar_count, is_label_show=True,
                                              is_toolbox_show=False,
                                              legend_orient='vertical', legend_pos='right', xaxis_interval=0,
                                              is_random=True, yaxis_formatter='%', xaxis_rotate=15)
                                bar_upstreams.append(bar_hosts_1)
                    if bar_vals_3:
                        thost = bar_vals_3[0]
                        counts_key = 'counts_%s_%s' % (thost, tm)
                        if RC.exists(counts_key):
                            bar_hosts_3 = Bar("%s应用服务实例分布" % tm, width='100%', height='100%', title_pos='center',
                                              title_text_size=14)
                            vals = RC.hgetall(counts_key)
                            if vals:
                                vals = sorted(vals.items(), key=lambda item: int(item[1]), reverse=True)
                                total_counts = float(reduce(lambda x, y: x + y, [int(val[1]) for val in vals]))
                                end = 15
                                if len(vals) < 15:
                                    end = len(vals)
                                bar_attr = [val[0].split(',')[-1] for val in vals[:end]]
                                bar_count = [float('%.2f'%((int(val[1])/total_counts)*100)) for val in vals[:end]]
                                bar_hosts_3.add('%sms'%thost, bar_attr, bar_count, is_label_show=True, is_toolbox_show=False,
                                                legend_orient='vertical', legend_pos='right', xaxis_interval=0,
                                                    is_random=True,yaxis_formatter='%',xaxis_rotate=15)
                                bar_upstreams.append(bar_hosts_3)
                        thost = bar_vals_3[1]
                        counts_key = 'counts_%s_%s' % (thost, tm)
                        if RC.exists(counts_key):
                            bar_hosts_4 = Bar("%s内应用服务实例分布" % tm, width='100%', height='100%', title_pos='center',
                                              title_text_size=14)
                            vals = RC.hgetall(counts_key)
                            if vals:
                                vals = sorted(vals.items(), key=lambda item: int(item[1]), reverse=True)
                                total_counts = float(reduce(lambda x, y: x + y, [int(val[1]) for val in vals]))
                                end = 15
                                if len(vals) < 15:
                                    end = len(vals)
                                bar_attr = [val[0].split(',')[-1] for val in vals[:end]]
                                bar_count = [float('%.2f'%((int(val[1])/total_counts)*100)) for val in vals[:end]]
                                bar_hosts_4.add('%sms'%thost, bar_attr, bar_count, is_label_show=True, is_toolbox_show=False,
                                                legend_orient='vertical', legend_pos='right', xaxis_interval=0,
                                                    is_random=True,yaxis_formatter='%',xaxis_rotate=15)
                                bar_upstreams.append(bar_hosts_4)
            except Exception as e:
                logging.error(e)
            domain_status_key = 'domain_counts_status_%s' %tm
            if RC.exists(domain_status_key):
                try:
                    vals = RC.hgetall(domain_status_key)
                    vals = sorted(vals.items(), key=lambda item: int(item[1]), reverse=True)
                    bar_attrs = [val[0] for val in vals]
                    host = bar_attrs[0]
                    if host:
                        counts_status_key = 'counts_%s_%s' % (host, tm)
                        if RC.exists(counts_status_key):
                            bar_status_hosts = Bar("%s应用服务实例分布" % tm, width='100%', height='100%', title_pos='center',
                                                   title_text_size=14)
                            vals = RC.hgetall(counts_status_key)
                            vals = sorted(vals.items(), key=lambda item: int(item[1]), reverse=True)
                            total_counts = float(reduce(lambda x, y: x + y, [int(val[1]) for val in vals]))
                            end = 15
                            if len(vals) < 15:
                                end = len(vals)
                            bar_attr = [val[0].split(',')[-1] for val in vals[:end]]
                            bar_counts = [float('%.2f'%((int(val[1])/total_counts)*100)) for val in vals[:end]]
                            bar_status_hosts.add('%s状态码' %host, bar_attr, bar_counts, is_label_show=True, is_toolbox_show=False,
                                            legend_orient='vertical', legend_pos='right', xaxis_interval=0, is_random=True,yaxis_formatter='%',xaxis_rotate=15)
                            bar_upstreams.append(bar_status_hosts)
                    host = bar_attrs[1]
                    if host:
                        counts_status_key = 'counts_%s_%s' % (host, tm)
                        if RC.exists(counts_status_key):
                            bar_status_hosts_1 = Bar("%s应用服务实例分布" % tm, width='100%', height='100%',
                                                     title_pos='center', title_text_size=14)
                            vals = RC.hgetall(counts_status_key)
                            vals = sorted(vals.items(), key=lambda item: int(item[1]), reverse=True)
                            total_counts = float(reduce(lambda x, y: x + y, [int(val[1]) for val in vals]))
                            end = 15
                            if len(vals) < 15:
                                end = len(vals)
                            bar_attr = [val[0].split(',')[-1] for val in vals[:end]]
                            bar_counts = [float('%.2f' % ((int(val[1]) / total_counts) * 100)) for val in
                                          vals[:end]]
                            bar_status_hosts_1.add('%s状态码' %host, bar_attr, bar_counts, is_label_show=True,
                                                 is_toolbox_show=False,
                                                 legend_orient='vertical', legend_pos='right', xaxis_interval=0,
                                                 is_random=True, yaxis_formatter='%', xaxis_rotate=15)
                            bar_upstreams.append(bar_status_hosts_1)
                    host = bar_attrs[2]
                    if host:
                        counts_status_key = 'counts_%s_%s' % (host, tm)
                        if RC.exists(counts_status_key):
                            bar_status_hosts_2 = Bar("%s应用服务实例分布" % tm, width='100%', height='100%',
                                                     title_pos='center', title_text_size=14)
                            vals = RC.hgetall(counts_status_key)
                            vals = sorted(vals.items(), key=lambda item: int(item[1]), reverse=True)
                            total_counts = float(reduce(lambda x, y: x + y, [int(val[1]) for val in vals]))
                            end = 15
                            if len(vals) < 15:
                                end = len(vals)
                            bar_attr = [val[0].split(',')[-1] for val in vals[:end]]
                            bar_counts = [float('%.2f' % ((int(val[1]) / total_counts) * 100)) for val in
                                          vals[:end]]
                            bar_status_hosts_2.add('%s状态码' %host, bar_attr, bar_counts, is_label_show=True,
                                                 is_toolbox_show=False,
                                                 legend_orient='vertical', legend_pos='right', xaxis_interval=0,
                                                 is_random=True, yaxis_formatter='%', xaxis_rotate=15)
                            bar_upstreams.append(bar_status_hosts_2)
                    host = bar_attrs[3]
                    if host:
                        counts_status_key = 'counts_%s_%s' % (host, tm)
                        if RC.exists(counts_status_key):
                            bar_status_hosts_3 = Bar("%s应用服务实例分布" % tm, width='100%', height='100%',
                                                     title_pos='center', title_text_size=14)
                            vals = RC.hgetall(counts_status_key)
                            vals = sorted(vals.items(), key=lambda item: int(item[1]), reverse=True)
                            total_counts = float(reduce(lambda x, y: x + y, [int(val[1]) for val in vals]))
                            end = 15
                            if len(vals) < 15:
                                end = len(vals)
                            bar_attr = [val[0].split(',')[-1] for val in vals[:end]]
                            bar_counts = [float('%.2f' % ((int(val[1]) / total_counts) * 100)) for val in
                                          vals[:end]]
                            bar_status_hosts_3.add('%s状态码' %host, bar_attr, bar_counts, is_label_show=True,
                                                 is_toolbox_show=False,
                                                 legend_orient='vertical', legend_pos='right', xaxis_interval=0,
                                                 is_random=True, yaxis_formatter='%', xaxis_rotate=15)
                            bar_upstreams.append(bar_status_hosts_3)

                except Exception as e:
                    logging.error(e)
        return render_template('chart_domain_status.html',bar_upstreams=bar_upstreams,form=form)
    except Exception as e:
        flash('暂时没有相关数据.')
        logging.error(e)
        return render_template('Message.html')

@page_chart_center.route('/chart_business_bigdata',methods = ['GET', 'POST'])
@user_auth.login_required(grade=8)
def chart_business_bigdata():
    try:
        try:
            importlib.reload(MyForm)
            form = MyForm.Form_business_bigdata()
            tm = datetime.datetime.now() - datetime.timedelta(minutes=1)
            tm = tm.strftime('%H:%M')
            dt = time.strftime('%Y-%m-%d', time.localtime())
            tm_vals = []
            Lines = []
            host = ''
            uri = ''
            searchs = []
            hosts = RC_CLUSTER.smembers('api_domain_lists_%s' % dt)
            hosts = [host for host in hosts]
            if hosts:
                searchs = json.dumps([{"id": str(i), "text": str(host)} for i, host in enumerate(hosts)])
                host = hosts[0]
            if 'business_bigdata_select_host' in request.cookies:
                host = request.cookies['business_bigdata_select_host']
            uris = RC_CLUSTER.smembers('api_uri_lists_%s_%s' %(host, dt))
            uris = [u for u in uris]
            if 'business_bigdata_select_uri' in request.cookies:
                URI = urllib.parse.unquote(request.cookies['business_bigdata_select_uri'])
                if URI in uris:
                    uri = URI
        except Exception as e:
            logging.error(e)
        #获取域名接口详情
        if host:
            try:
                #生成时间表
                if 'business_bigdata_select_date' in request.cookies:
                    dt = request.cookies['business_bigdata_select_date']
                for d in range(0, 24):
                    for t in range(0, 60):
                        if int(d) < 10:
                            d = '0{0}'.format(d)
                        if int(t) < 10:
                            t = '0{0}'.format(t)
                        if dt == time.strftime('%Y-%m-%d', time.localtime()):
                            if int(tm.replace(':', '')) > int('{0}{1}'.format(d, t)):
                                tm_vals.append('%s:%s' % (d, t))
                        else:
                            tm_vals.append('%s:%s' % (d, t))
            except Exception as e:
                logging.error(e)
            #域名接口访问量统计
            try:
                pv_vals = OrderedDict()
                for tm in tm_vals:
                    Key = 'domain_api_pv_%s_%s_%s' % (host, dt, tm)
                    if uri:
                        Key = 'domain_api_pv_%s_%s_%s_%s' %(host,uri,dt,tm)
                    if RC_CLUSTER.exists(Key):
                        pv_vals[tm] = int(RC_CLUSTER.get(Key))
                if pv_vals:
                    line_attrs = [val for val in pv_vals]
                    line_vals = [pv_vals[val] for val in pv_vals]
                    title = '%s http://%s域名访问量(分钟)' % (dt,host)
                    if uri:
                        title = '%s http://%s%s接口访问量(分钟)' % (dt, host, uri)
                    line = Line(title, width='110%', height='250px', title_pos='25%',
                                       title_text_size=14)
                    line.add('', line_attrs, line_vals, is_toolbox_show=False, is_smooth=True,
                                    mark_point=["max", "min"], mark_point_symbolsize=80, legend_pos='65%', legend_top='top', is_datazoom_show=True,
                                    datazoom_range=[v for v in range(100, 1)], datazoom_type='both')
                    Lines.append(line)
            except Exception as e:
                logging.error(e)
            #详细数据获取
            try:
                vals4xx = OrderedDict()
                vals5xx = OrderedDict()
                vals100 = OrderedDict()
                vals200 = OrderedDict()
                vals500 = OrderedDict()
                vals1000 = OrderedDict()
                avg_resp = OrderedDict()
                VALS = {'status_4xx': vals4xx, 'status_5xx': vals5xx, 'resp_100': vals100, 'resp_200': vals200, 'resp_500': vals500, 'resp_1000': vals1000,'avg_resp':avg_resp}
                for tm in tm_vals:
                    Key = 'domain_api_infos_%s_%s_%s' % (host, dt, tm)
                    if uri:
                        Key = 'domain_api_infos_%s_%s_%s_%s' % (host, uri, dt, tm)
                    if RC_CLUSTER.exists(Key):
                        for k in VALS:
                            v = RC_CLUSTER.hget(Key, k)
                            if v:
                                if tm in pv_vals:
                                    if k == 'avg_resp':
                                        v = float('%.2f' %float(v))
                                        if v >0:
                                            VALS[k][tm] = v
                                    else:
                                        fv = float('%.2f' %(float(v)/float(pv_vals[tm])*100))
                                        if fv >100:
                                            fv = 100
                                        if fv >=0.001:
                                            VALS[k][tm] = fv
            except Exception as e:
                logging.error(e)
            #异常状态码统计
            title = '%s http://%s域名异常状态码(占比)' % (dt,host)
            if uri:
                title = '%s http://%s%s接口异常状态码(占比)' % (dt, host, uri)
            line_status = Line(title, width='110%', height='250px',
                               title_pos='25%', title_text_size=14)
            if len(vals4xx)>1:
                line4_attrs = [val for val in vals4xx]
                line4_vals = [float('%.2f' %(vals4xx[val]/100)) for val in vals4xx]
                if uri:
                    line4_vals = [vals4xx[val] for val in vals4xx]
                line_status.add('4xx', line4_attrs, line4_vals, is_toolbox_show=False, is_smooth=True,
                                mark_point=["max", "min"], mark_point_symbolsize=80, legend_pos='65%',legend_top='top', is_datazoom_show=True,
                                datazoom_range=[v for v in range(100, 1)], datazoom_type='both',
                                yaxis_formatter='%')
            if len(vals5xx)>1:
                line5_attrs = [val for val in vals5xx]
                line5_vals = [float('%.2f' %(vals5xx[val]/100)) for val in vals5xx]
                if uri:
                    line5_vals = [vals5xx[val] for val in vals5xx]
                line_status.add('5xx', line5_attrs, line5_vals, is_toolbox_show=False, is_smooth=True,
                         mark_point=["max", "min"], mark_point_symbolsize=80, legend_pos='65%',legend_top='top', is_datazoom_show=True,
                         datazoom_range=[v for v in range(100, 1)], datazoom_type='both', yaxis_formatter='%')
            if len(vals4xx)>1 or len(vals5xx)>1:
                Lines.append(line_status)
            #响应时间统计
            title = '%s http://%s域名响应时间(占比)' % (dt,host)
            if uri:
                title = '%s http://%s%s接口响应时间(占比)' % (dt, host, uri)
            line_time = Line(title, width='110%', height='250px',
                                 title_pos='25%', title_text_size=14)
            if len(vals100) >1:
                line100_attrs = [val for val in vals100]
                line100_vals = [float('%.2f' %(vals100[val]/100)) for val in vals100]
                if uri:
                    line100_vals = [vals100[val] for val in vals100]
                line_time.add('100ms以上', line100_attrs, line100_vals, is_toolbox_show=False, is_smooth=True,
                              mark_point=["max", "min"], mark_point_symbolsize=80, legend_pos='65%',legend_top='top', is_datazoom_show=True,
                              datazoom_range=[v for v in range(100, 1)], datazoom_type='both', yaxis_formatter='%')
            if len(vals200) >1:
                line200_attrs = [val for val in vals200]
                line200_vals = [float('%.2f' %(vals200[val]/100)) for val in vals200]
                if uri:
                    line200_vals = [vals200[val] for val in vals200]
                line_time.add('200ms以上', line200_attrs, line200_vals, is_toolbox_show=False, is_smooth=True,
                              mark_point=["max", "min"], mark_point_symbolsize=80, legend_pos='65%',legend_top='top', is_datazoom_show=True,
                              datazoom_range=[v for v in range(100, 1)], datazoom_type='both', yaxis_formatter='%')
            if len(vals500) >1:
                line500_attrs = [val for val in vals500]
                line500_vals = [float('%.2f' %(vals500[val]/100)) for val in vals500]
                if uri:
                    line500_vals = [vals500[val] for val in vals500]
                line_time.add('500ms以上', line500_attrs, line500_vals, is_toolbox_show=False, is_smooth=True,
                           mark_point=["max", "min"], mark_point_symbolsize=80, legend_pos='65%',legend_top='top', is_datazoom_show=True,
                           datazoom_range=[v for v in range(100, 1)], datazoom_type='both', yaxis_formatter='%')
            if len(vals1000) >1:
                line1000_attrs = [val for val in vals1000]
                line1000_vals = [float('%.2f' %(vals1000[val]/100)) for val in vals1000]
                if uri:
                    line1000_vals = [vals1000[val] for val in vals1000]
                line_time.add('1000ms以上', line1000_attrs, line1000_vals, is_toolbox_show=False, is_smooth=True,
                     mark_point=["max", "min"], mark_point_symbolsize=80, legend_pos='65%',legend_top='top', is_datazoom_show=True,
                     datazoom_range=[v for v in range(100, 1)], datazoom_type='both', yaxis_formatter='%')
            if len(vals100) >1 or len(vals200) >1 or len(vals500) >1 or len(vals1000) >1:
                Lines.append(line_time)
            # 响应时间统计
            title = '%s http://%s域名平均响应时间' % (dt, host)
            if uri:
                title = '%s http://%s%s接口平均响应时间' % (dt, host, uri)
            line_avg_resp = Line(title, width='110%', height='250px',
                             title_pos='20%', title_text_size=14)
            avg_resp_attrs = [val for val in avg_resp]
            avg_resp_vals = [float('%.2f' % (avg_resp[val] / 100)) for val in avg_resp]
            if uri:
                avg_resp_vals = [avg_resp[val] for val in avg_resp]
            line_avg_resp.add('单位:秒', avg_resp_attrs, avg_resp_vals, is_toolbox_show=False, is_smooth=True,
                            mark_point=["max", "min"], mark_point_symbolsize=80, legend_pos='65%',legend_top='top', is_datazoom_show=True,
                            datazoom_range=[v for v in range(100, 1)], datazoom_type='both')
            if avg_resp:
                Lines.append(line_avg_resp)
        try:
            resp = make_response(render_template('chart_business_bigdata.html',form=form,Lines=Lines,searchs=searchs,dt=dt))
            resp.set_cookie('business_bigdata_select_host',host,path='/')
            resp.set_cookie('business_bigdata_select_date',dt, path='/')
        except Exception as e:
            logging.error(e)
        return resp
    except Exception as e:
        flash('暂时没有相关数据.','error')
        logging.error(e)
        return render_template('Message.html')

@page_chart_center.route('/chart_business_collect',methods = ['GET', 'POST'])
@user_auth.login_required(grade=8)
def chart_business_collect():
    try:
        try:
            tm = datetime.datetime.now() - datetime.timedelta(days=30)
            tm = tm.strftime('%Y-%m-%dT%H:%M:%SZ')
            dt = time.strftime('%Y-%m-%d', time.localtime())
            Lines = []
            host = ''
            uri = ''
            searchs = []
            hosts = RC_CLUSTER.smembers('api_domain_lists_%s' % dt)
            hosts = [host for host in hosts]
            if hosts:
                searchs = json.dumps([{"id": str(i), "text": str(host)} for i, host in enumerate(hosts)])
                host = hosts[0]
            if 'business_bigdata_select_host' in request.cookies:
                host = request.cookies['business_bigdata_select_host']
            uris = RC_CLUSTER.smembers('api_uri_lists_%s_%s' %(host, dt))
            uris = [uri for uri in uris]
            if uris:
                uri = uris[0]
            if 'business_bigdata_select_uri' in request.cookies:
                URI = urllib.parse.unquote(request.cookies['business_bigdata_select_uri'])
                if URI in uris:
                    uri = URI
        except Exception as e:
            logging.error(e)
        #获取域名接口详情
        if host and uri:
            if 'select_datatime' in request.cookies:
                tm = urllib.parse.unquote(request.cookies['select_datatime'])
                tm = tm.replace('.000','')
            #详细数据获取
            try:
                vals4xx = OrderedDict()
                vals5xx = OrderedDict()
                vals100 = OrderedDict()
                vals200 = OrderedDict()
                vals500 = OrderedDict()
                vals1000 = OrderedDict()
                avg_resp = OrderedDict()
                pv_vals = OrderedDict()
                VALS = {'status_4xx': vals4xx, 'status_5xx': vals5xx, 'resp_100': vals100, 'resp_200': vals200, 'resp_500': vals500, 'resp_1000': vals1000,'avg_resp':avg_resp,'pv':pv_vals}
                cmd = "select * from " + ' "analysis%s" ' %time.strftime('%Y',time.localtime()) + "WHERE time >= '%s' and host='%s' and uri='%s'" % (tm, host, uri)
                result = Influx_cli.query(cmd)
                infos = [infos for infos in result.get_points()]
                for key in VALS:
                    for info in infos:
                        if info['mean_%s' %key]:
                            if key in ('avg_resp','pv'):
                                v = info['mean_%s' %key]
                            else:
                                if info['mean_pv']:
                                    v = info['mean_%s' %key]/info['mean_pv']*100
                                else:
                                    v = 0.0
                        else:
                            v = 0.0
                        VALS[key][info['time'].replace('T',' ').replace('Z','')] = float('%.3f'%v)
            except Exception as e:
                logging.error(e)
            # 并发访问量统计
            if pv_vals:
                line_attrs = [val for val in pv_vals]
                line_vals = [int(pv_vals[val])*60 for val in pv_vals]
                line = Line('%s -> %s http://%s%s接口访问量(小时)' % (tm.split('T')[0],dt, host, uri), width='105%', height='250px',
                            title_pos='20%',
                            title_text_size=14)
                line.add('', line_attrs, line_vals, is_toolbox_show=False, is_smooth=True,
                         mark_point=["max", "min"], mark_point_symbolsize=80, legend_pos='65%', legend_top='top',
                         is_datazoom_show=True,
                         datazoom_range=[v for v in range(100, 1)], datazoom_type='both',xaxis_rotate=5)
                Lines.append(line)
            #异常状态码统计
            line_status = Line('%s -> %s http://%s%s接口异常状态码(占比)' % (tm.split('T')[0],dt,host, uri), width='105%', height='250px',
                               title_pos='20%', title_text_size=14)
            if len(vals4xx)>1:
                line4_attrs = [val for val in vals4xx]
                line4_vals = [vals4xx[val] for val in vals4xx]
                line_status.add('4xx', line4_attrs, line4_vals, is_toolbox_show=False, is_smooth=True,
                                mark_point=["max", "min"], mark_point_symbolsize=80, legend_pos='65%',legend_top='top', is_datazoom_show=True,
                                datazoom_range=[v for v in range(100, 1)], datazoom_type='both',
                                yaxis_formatter='%',xaxis_rotate=5)
            if len(vals5xx)>1:
                line5_attrs = [val for val in vals5xx]
                line5_vals = [vals5xx[val] for val in vals5xx]
                line_status.add('5xx', line5_attrs, line5_vals, is_toolbox_show=False, is_smooth=True,
                         mark_point=["max", "min"], mark_point_symbolsize=80, legend_pos='65%',legend_top='top', is_datazoom_show=True,
                         datazoom_range=[v for v in range(100, 1)], datazoom_type='both', yaxis_formatter='%',xaxis_rotate=5)
            if len(vals4xx)>1 or len(vals5xx)>1:
                Lines.append(line_status)
            #响应时间统计
            line_time = Line('%s -> %s http://%s%s接口响应时间(占比)' % (tm.split('T')[0],dt,host, uri), width='105%', height='250px',
                                 title_pos='20%', title_text_size=14)
            if len(vals100) >1:
                line100_attrs = [val for val in vals100]
                line100_vals = [vals100[val] for val in vals100]
                line_time.add('100ms以上', line100_attrs, line100_vals, is_toolbox_show=False, is_smooth=True,
                              mark_point=["max", "min"], mark_point_symbolsize=80, legend_pos='65%',legend_top='top', is_datazoom_show=True,
                              datazoom_range=[v for v in range(100, 1)], datazoom_type='both', yaxis_formatter='%',xaxis_rotate=5)
            if len(vals200) >1:
                line200_attrs = [val for val in vals200]
                line200_vals = [vals200[val] for val in vals200]
                line_time.add('200ms以上', line200_attrs, line200_vals, is_toolbox_show=False, is_smooth=True,
                              mark_point=["max", "min"], mark_point_symbolsize=80, legend_pos='65%',legend_top='top', is_datazoom_show=True,
                              datazoom_range=[v for v in range(100, 1)], datazoom_type='both', yaxis_formatter='%',xaxis_rotate=5)
            if len(vals500) >1:
                line500_attrs = [val for val in vals500]
                line500_vals = [vals500[val] for val in vals500]
                line_time.add('500ms以上', line500_attrs, line500_vals, is_toolbox_show=False, is_smooth=True,
                           mark_point=["max", "min"], mark_point_symbolsize=80, legend_pos='65%',legend_top='top', is_datazoom_show=True,
                           datazoom_range=[v for v in range(100, 1)], datazoom_type='both', yaxis_formatter='%',xaxis_rotate=5)
            if len(vals1000) >1:
                line1000_attrs = [val for val in vals1000]
                line1000_vals = [vals1000[val] for val in vals1000]
                line_time.add('1000ms以上', line1000_attrs, line1000_vals, is_toolbox_show=False, is_smooth=True,
                     mark_point=["max", "min"], mark_point_symbolsize=80, legend_pos='65%',legend_top='top', is_datazoom_show=True,
                     datazoom_range=[v for v in range(100, 1)], datazoom_type='both', yaxis_formatter='%',xaxis_rotate=5)
            if len(vals100) >1 or len(vals200) >1 or len(vals500) >1 or len(vals1000) >1:
                Lines.append(line_time)
            # 响应时间统计
            line_avg_resp = Line('%s -> %s http://%s%s接口平均响应时间' % (tm.split('T')[0],dt, host, uri), width='105%', height='250px',
                             title_pos='20%', title_text_size=14)
            avg_resp_attrs = [val for val in avg_resp]
            avg_resp_vals = [avg_resp[val] for val in avg_resp]
            line_avg_resp.add('单位:秒', avg_resp_attrs, avg_resp_vals, is_toolbox_show=False, is_smooth=True,
                            mark_point=["max", "min"], mark_point_symbolsize=80, legend_pos='65%',legend_top='top', is_datazoom_show=True,
                            datazoom_range=[v for v in range(100, 1)], datazoom_type='both',xaxis_rotate=5)
            if avg_resp:
                Lines.append(line_avg_resp)
        try:
            resp = make_response(render_template('chart_business_collect.html',Lines=Lines,searchs=searchs))
            resp.set_cookie('business_bigdata_select_host',host,path='/')
            resp.set_cookie('select_datatime',tm, path='/')
        except Exception as e:
            logging.error(e)
        return resp
    except Exception as e:
        flash('暂时没有相关数据.','error')
        logging.error(e)
        return render_template('Message.html')

@page_chart_center.route('/chart_k8s_status')
@page_chart_center.route('/chart_k8s_status/<domain>')
@user_auth.login_required(grade=1)
def chart_k8s_status(domain=None):
    try:
        td = time.strftime("%Y-%m-%d", time.localtime())
        charts = []
        vals = OrderedDict()
        now_date = datetime.datetime.now()
        db_project = db_op.project_list
        all_domains = db_project.query.with_entities(distinct(db_project.domain)).all()
        all_domains = [domains[0].split(',') for domains in all_domains if domains[0]]
        all_domains = set([domain for domains in all_domains for domain in domains])
        k8s_domains_key = 'op_k8s_domains_%s' % td
        domains_menu = RC.smembers(k8s_domains_key)
        domains_menu = [domain for domain in domains_menu if domain in all_domains]
        if not domain:
            domain = domains_menu[0]
        for i in range(10):
            tt = now_date - datetime.timedelta(days=i)
            tt = tt.strftime('%Y-%m-%d')
            k8s_pv_key = 'op_k8s_pv_%s' % tt
            if RC.exists(k8s_pv_key):
                vals[tt] = int(RC.get(k8s_pv_key))
        bar = Bar("容器平台每日PV统计", width='105%', height=250, title_pos='5%', title_text_size=12)
        if vals:
            vals = sorted(vals.items(), key=lambda item:item[0])
            bar_vals = [val[0] for val in vals]
            bar_counts = [float('%.2f'%(float(val[1])/10000)) for val in vals]
            bar.add("", bar_vals, bar_counts, is_label_show=True, is_toolbox_show=False, legend_orient='vertical',
                    legend_pos='right', xaxis_interval=0,yaxis_formatter='万')
            charts.append(bar)
        Key = 'op_k8s_ingress_log'
        if RC.exists('%s_%s' % (Key,td)):
            try:
                line = Line("容器平台业务QPS统计", width='105%', height=250, title_pos='5%', title_text_size=12)
                vals = RC.hgetall('%s_%s' % (Key, td))
                vals = sorted(vals.items(), key=lambda item: item[0])
                attrs = [val[0] for val in vals[::10]]
                vals = [int(int(val[1]) / 60) for val in vals[::10]]
                line.add('', attrs, vals, is_label_show=True, is_toolbox_show=False, legend_pos='70%',xaxis_interval=0, is_datazoom_show=True,
                 datazoom_range=[v for v in range(100, 10)],datazoom_type='both', is_smooth=True)
                charts.append(line)
            except Exception as e:
                logging.error(e)
        stat_key = 'op_k8s_ingress_stat'
        rt_key = 'op_k8s_ingress_rt'
        line = Line("域名%s访问量统计" % domain, width='105%', height=250, title_pos='5%', title_text_size=12)
        vals = RC.hgetall('%s_%s_%s' % (Key, domain, td))
        vals = sorted(vals.items(), key=lambda item: item[0])
        line_vals = [val[0] for val in vals]
        line_counts = [int(int(val[1]) / 60) for val in vals]
        line.add('RPS', line_vals, line_counts, is_label_show=True, is_toolbox_show=False, is_smooth=True,
                 mark_point=["max", "min"],
                 mark_point_symbolsize=80, is_datazoom_show=True,
                 datazoom_range=[v for v in range(100, 10)],
                 datazoom_type='both', legend_pos='70%')
        charts.append(line)
        line = Line("域名%s状态码统计" %domain, width='105%', height=250, title_pos='5%', title_text_size=12)
        vals = RC.hgetall('%s_%s_%s' % (stat_key, domain, td))
        if vals:
            vals = sorted(vals.items(), key=lambda item: item[0])
            line_vals = [val[0] for val in vals]
            line_key = set([key for val in vals for key in eval(val[1])])
            for key in line_key:
                line_counts = []
                for val in vals:
                    if key in eval(val[1]):
                        line_counts.append(float('%.2f'%(float(eval(val[1])[key])/reduce(lambda x,y:x+y,eval(val[1]).values())*100)))
                    else:
                        line_counts.append(0.0)
                line.add('%s'%key, line_vals, line_counts,is_label_show=True, is_toolbox_show=False, is_smooth=True, mark_point=["max", "min"],
                         mark_point_symbolsize=80, is_datazoom_show=True,
                         datazoom_range=[v for v in range(100, 10)],
                         datazoom_type='both', legend_pos='70%',yaxis_formatter='%')
            charts.append(line)
            line = Line("域名%s响应时间" % domain, width='105%', height=250, title_pos='5%', title_text_size=12)
            vals = RC.hgetall('%s_%s_%s' % (rt_key, domain, td))
            vals = sorted(vals.items(), key=lambda item: item[0])
            line_vals = [val[0] for val in vals]
            line_counts = [float(val[1])*1000 for val in vals]
            line.add('响应时间', line_vals, line_counts,is_label_show=True, is_toolbox_show=False, is_smooth=True, mark_point=["max", "min"],
                         mark_point_symbolsize=80, is_datazoom_show=True,
                         datazoom_range=[v for v in range(100, 10)],
                         datazoom_type='both', legend_pos='70%', yaxis_formatter='ms')
            charts.append(line)
    except Exception as e:
        logging.error(e)
    return render_template('chart_k8s_status.html', charts=charts,domains_menu=domains_menu,domain=domain)
@page_chart_center.before_request
@user_auth.login_required(grade=10)
def check_login(exception = None):
    tools.Async_log(g.user, request.url)
@page_chart_center.teardown_request
def db_remove(error=None):
    db_idc.DB.session.remove()
    db_op.DB.session.remove()
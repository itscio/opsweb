#-*- coding: utf-8 -*-
from flask import Blueprint,render_template,render_template_string,flash,g,request
from Modules import check,loging,MyForm,produce
import redis
from rediscluster import RedisCluster
import json
import __init__
app = __init__.app
host = app.config.get('REDIS_HOST')
port = app.config.get('REDIS_PORT')
Redis = redis.StrictRedis(host=host,port=port,db=0,socket_timeout=1)
nodes = app.config.get('NODES')
RC = RedisCluster(startup_nodes=nodes,decode_responses=True)
page_chart_center = Blueprint('chart_center', __name__)
@page_chart_center.route('/chart_center_internet',methods = ['GET', 'POST'])
def chart_center_internet():
    try:
        reload(MyForm)
        form = MyForm.MyForm_chart_center()
        DOMAIN_DATA = None
        RT_DATA = None
        PV = RC.get('baihe_pv') or 'None'
        UV = len(RC.smembers('baihe_uv')) or 'None'
        if form.submit.data:
            Domain = form.select_internet.data
            Key = 'internet_access_%s' %Domain
            web_rt_key = 'internet_rt_%s' % Domain
            if RC.exists(Key):
                #获取响应时间
                DATA = [eval(v) for v in RC.lrange(web_rt_key, 0, -1)]
                DATA = [DATA[i] for i in xrange(0, len(DATA), 3)]
                RT_DATA = [{'data': DATA, 'name': str(Domain)}]
                #获取并发量
                DATA = [eval(v) for v in RC.lrange(Key, 0, -1)]
                DATA = [DATA[i] for i in xrange(0, len(DATA), 3)]
                DOMAIN_DATA = [{'data': DATA, 'name': str(Domain)}]
            else:
                 flash('暂时还没%s的相关数据!' %Domain)
        DATA = [eval(v) for v in Redis.lrange('lvs_internet', 0, -1)]
        LVS_DATA = [{'data': DATA, 'name': 'INTERNET_LVS'}]
        return render_template('chart_center_internet.html',form = form,LVS_DATA=LVS_DATA,DOMAIN_DATA=DOMAIN_DATA,RT_DATA=RT_DATA,PV=PV,UV=UV)
    except Exception as e:
        loging.write(e)
        return render_template_string('获取数据错误!')

@page_chart_center.route('/chart_center_intranet',methods = ['GET', 'POST'])
def chart_center_intranet():
    try:
        reload(MyForm)
        form = MyForm.MyForm_chart_center()
        DOMAIN_DATA = None
        RT_DATA = None
        if form.submit.data:
            Domain = form.select_intranet.data
            Key = 'intranet_access_%s' % Domain
            web_rt_key = 'intranet_rt_%s' % Domain
            if RC.exists(Key):
                # 获取响应时间
                DATA = [eval(v) for v in RC.lrange(web_rt_key, 0, -1)]
                DATA = [DATA[i] for i in xrange(0, len(DATA), 3)]
                # 获取并发量
                RT_DATA = [{'data': DATA, 'name': str(Domain)}]
                DATA = [eval(v) for v in RC.lrange(Key, 0, -1)]
                DATA = [DATA[i] for i in xrange(0, len(DATA), 3)]
                DOMAIN_DATA = [{'data': DATA, 'name': str(Domain)}]
            else:
                 flash('暂时还没%s的相关数据!' %Domain)
        DATA = [eval(v) for v in Redis.lrange('lvs_intranet', 0, -1)]
        LVS_DATA=[{'data': DATA, 'name': 'INTRANET_LVS'}]
        return render_template('chart_center_intranet.html',form = form,LVS_DATA=LVS_DATA,DOMAIN_DATA=DOMAIN_DATA,RT_DATA=RT_DATA)
    except Exception as e:
        loging.write(e)
        return render_template_string('获取数据错误!')

@page_chart_center.route('/chart_center_domain')
def chart_center_domain():
    try:
        INTERNET_DOMAIN = {}
        INTRANET_DOMAIN = {}
        for domain in RC.smembers('haproxy_topic'):
            Count = int(RC.get('haproxy_logs_%s' %domain))
            if Count == 0:
                continue
            INTERNET_DOMAIN[str(domain)] = Count
        for domain in RC.smembers('haproxy2_topic'):
            Count = int(RC.get('haproxy2_logs_%s' %domain))
            if Count == 0:
                continue
            INTRANET_DOMAIN[str(domain)] = Count
        return render_template('chart_center_domain.html',INTERNET_DOMAIN=INTERNET_DOMAIN,INTRANET_DOMAIN=INTRANET_DOMAIN)
    except Exception as e:
        loging.write(e)
        return render_template_string('获取数据错误!')

@page_chart_center.route('/chart_center_area')
def chart_center_area():
    try:
        AREA_DATA = {}
        area_key = 'Area_Keys'
        for area in RC.smembers(area_key):
            Count = int(RC.get(area))
            if Count == 0:
                continue
            AREA_DATA[str(area.split('_')[2])] = Count
        AREA_DATA = json.dumps(AREA_DATA, encoding='utf-8',indent=4)
        return render_template('chart_center_area.html',AREA_DATA=AREA_DATA)
    except Exception as e:
        loging.write(e)
        return render_template_string('获取数据错误!')

@page_chart_center.route('/chart_center_traffic',methods = ['GET', 'POST'])
def chart_center_traffic():
    try:
        reload(MyForm)
        form = MyForm.MyForm_chart_center()
        Traffic_ser_DATA = Traffic_cli_DATA = None
        if form.submit.data:
            Domain = form.select_internet.data
            Cli_Key = 'Topic.traffic.client_%s' % Domain
            Ser_Key = 'Topic.traffic.server_%s' % Domain
            if RC.exists(Cli_Key):
                # 获取请求流量
                DATA = [eval(v) for v in RC.lrange(Cli_Key, 0, -1)]
                DATA = [DATA[i] for i in xrange(0, len(DATA), 10)]
                Traffic_cli_DATA = [{'data': DATA, 'name': str(Domain)}]
            if RC.exists(Ser_Key):
                # 获取响应流量
                DATA = [eval(v) for v in RC.lrange(Ser_Key, 0, -1)]
                DATA = [DATA[i] for i in xrange(0, len(DATA), 10)]
                Traffic_ser_DATA = [{'data': DATA, 'name': str(Domain)}]
            if not Traffic_ser_DATA and not Traffic_cli_DATA:
                 flash('暂时还没%s的相关数据!' %Domain)
        return render_template('chart_center_traffic.html',form = form,Traffic_cli_DATA = Traffic_cli_DATA,Traffic_ser_DATA=Traffic_ser_DATA)
    except Exception as e:
        loging.write(e)
        return render_template_string('获取数据错误!')

@page_chart_center.before_request
@check.login_required(grade=2)
def check_login(error=None):
    produce.Async_log(g.user, request.url)
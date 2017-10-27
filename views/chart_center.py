#-*- coding: utf-8 -*-
from imp import reload
from flask import Blueprint,render_template,flash,g,request
from Modules import check,loging,MyForm,produce,ip_area,db_idc,main_info
import redis
from sqlalchemy import and_
from rediscluster import RedisCluster
import time
import datetime
import collections
import __init__
app = __init__.app
logging = loging.Error()
host = app.config.get('REDIS_HOST')
port = app.config.get('REDIS_PORT')
Redis = redis.StrictRedis(host=host,port=port,db=0,socket_timeout=1)
nodes = app.config.get('NODES_PRODUCE')
RC = RedisCluster(startup_nodes=nodes,decode_responses=True)
page_chart_center = Blueprint('chart_center', __name__)
@page_chart_center.route('/chart_center_internet',methods = ['GET', 'POST'])
@main_info.main_info
def chart_center_internet():
    try:
        reload(MyForm)
        form = MyForm.MyForm_chart_center()
        DOMAIN_DATA = None
        RT_DATA = None
        tt = int(time.strftime('%Y%m%d', time.localtime()))
        PV = RC.get('baihe_pv_%s'%tt) or 'None'
        UV = len(RC.smembers('baihe_uv_%s'%tt)) or 'None'
        if form.submit.data:
            Domain = form.select_internet.data
            Key = 'internet_access_%s_%s'%(tt,Domain)
            web_rt_key = 'internet_rt_%s_%s'%(tt,Domain)
            if RC.exists(Key):
                #获取响应时间
                DATA = [eval(v) for v in RC.lrange(web_rt_key, 0, -1)]
                DATA = [DATA[i] for i in range(0, len(DATA), 3)]
                RT_DATA = [{'data': DATA, 'name': str(Domain)}]
                #获取并发量
                DATA = [eval(v) for v in RC.lrange(Key, 0, -1)]
                DATA = [DATA[i] for i in range(0, len(DATA), 3)]
                DOMAIN_DATA = [{'data': DATA, 'name': str(Domain)}]
            else:
                 flash('%s的相关数据为空!' %Domain.strip())
        DATA = [eval(v) for v in Redis.lrange('lvs_internet', 0, -1)]
        LVS_DATA = [{'data': DATA, 'name': 'INTERNET_LVS'}]
        return render_template('chart_center_internet.html',Main_Infos=g.main_infos,form = form,LVS_DATA=LVS_DATA,DOMAIN_DATA=DOMAIN_DATA,RT_DATA=RT_DATA,PV=PV,UV=UV)
    except Exception as e:
        logging.error(e)
        flash('获取数据错误!')
        return render_template('Message_static.html', Main_Infos=g.main_infos)

@page_chart_center.route('/chart_center_intranet',methods = ['GET', 'POST'])
@main_info.main_info
def chart_center_intranet():
    try:
        reload(MyForm)
        tt = int(time.strftime('%Y%m%d', time.localtime()))
        form = MyForm.MyForm_chart_center()
        DOMAIN_DATA = None
        RT_DATA = None
        if form.submit.data:
            Domain = form.select_intranet.data
            Key = 'intranet_access_%s_%s'%(tt,Domain)
            web_rt_key = 'intranet_rt_%s_%s'%(tt,Domain)
            if RC.exists(Key):
                # 获取响应时间
                DATA = [eval(v) for v in RC.lrange(web_rt_key, 0, -1)]
                DATA = [DATA[i] for i in range(0, len(DATA), 3)]
                # 获取并发量
                RT_DATA = [{'data': DATA, 'name': str(Domain)}]
                DATA = [eval(v) for v in RC.lrange(Key, 0, -1)]
                DATA = [DATA[i] for i in range(0, len(DATA), 3)]
                DOMAIN_DATA = [{'data': DATA, 'name': str(Domain)}]
            else:
                 flash('%s的相关数据为空!' %Domain.strip())
        DATA = [eval(v) for v in Redis.lrange('lvs_intranet', 0, -1)]
        LVS_DATA=[{'data': DATA, 'name': 'INTRANET_LVS'}]
        return render_template('chart_center_intranet.html',Main_Infos=g.main_infos,form = form,LVS_DATA=LVS_DATA,DOMAIN_DATA=DOMAIN_DATA,RT_DATA=RT_DATA)
    except Exception as e:
        logging.error(e)
        flash('获取数据错误!')
        return render_template('Message_static.html', Main_Infos=g.main_infos)

@page_chart_center.route('/chart_center_domain')
@main_info.main_info
def chart_center_domain():
    tt = int(time.strftime('%Y%m%d', time.localtime()))
    try:
        INTERNET_DOMAIN = {}
        INTRANET_DOMAIN = {}
        for domain in RC.smembers('haproxy_topic_%s' %tt):
            Count = int(RC.get('haproxy_logs_%s_%s'%(tt,domain)))
            if Count == 0:
                continue
            INTERNET_DOMAIN[str(domain)] = Count
        for domain in RC.smembers('haproxy2_topic_%s' %tt):
            Count = int(RC.get('haproxy2_logs_%s_%s'%(tt,domain)))
            if Count == 0:
                continue
            INTRANET_DOMAIN[str(domain)] = Count
        return render_template('chart_center_domain.html',Main_Infos=g.main_infos,INTERNET_DOMAIN=INTERNET_DOMAIN,INTRANET_DOMAIN=INTRANET_DOMAIN)
    except Exception as e:
        logging.error(e)
        flash('获取数据错误!')
        return render_template('Message_static.html', Main_Infos=g.main_infos)

@page_chart_center.route('/chart_center_traffic')
@main_info.main_info
def chart_center_traffic():
    try:
        Tra_cli_url_minute_datas = collections.OrderedDict()
        Tra_ser_url_minute_datas = collections.OrderedDict()
        for i in range(1,5):
            Tm = datetime.datetime.now() - datetime.timedelta(minutes=i)
            Tm = Tm.strftime('%H:%M')
            Tra_cli_url_minute_Key = 'traffic.cli.url_%s' % Tm
            Tra_ser_url_minute_Key = 'traffic.ser.url_%s' % Tm
            Tra_cli_url_minute_datas[Tm] = [[str(url), int(RC.zscore(Tra_cli_url_minute_Key, url)) * 8 / 1024 / 1024] for url in RC.zrevrange(Tra_cli_url_minute_Key, 0,4)]
            Tra_ser_url_minute_datas[Tm] = [[str(url), int(RC.zscore(Tra_ser_url_minute_Key,url)) * 8 / 1024 / 1024] for url in RC.zrevrange(Tra_ser_url_minute_Key, 0,4) ]
        return render_template('chart_center_traffic.html',Main_Infos=g.main_infos,Tra_cli_url_minute_datas=Tra_cli_url_minute_datas,Tra_ser_url_minute_datas=Tra_ser_url_minute_datas)
    except Exception as e:
        logging.error(e)
        flash('获取数据错误!')
        return render_template('Message_static.html', Main_Infos=g.main_infos)

@page_chart_center.route('/gateway_traffic')
@main_info.main_info
def gateway_traffic():
    try:
        values = collections.OrderedDict()
        for k in range(1,13):
            tt = datetime.datetime.now()-datetime.timedelta(minutes=k)
            tt = tt.strftime("%H:%M")
            value = []
            tables = ('入口IP','入口流量','出口IP','出口流量')
            for i in range(1, 11):
                if RC.exists('Traffic_gateway_%s' %tt):
                    value.append(eval(RC.hget('Traffic_gateway_%s' %tt, str(i))))
            values[tt] = value
        return render_template('gateway_traffic.html',Main_Infos=g.main_infos,tables = tables,values=values)
    except Exception as e:
        logging.error(e)
        flash('获取数据错误!')
        return render_template('Message_static.html', Main_Infos=g.main_infos)

@page_chart_center.route('/gateway_domain')
@main_info.main_info
def gateway_domain():
    try:
        DATA = [eval(v) for v in RC.lrange('top_url_%s'%time.strftime('%Y-%m-%d',time.localtime()), 0, -1)]
        TOP_URL_DATA = [{'data': DATA, 'name': 'conn'}]
        values = collections.OrderedDict()
        for k in range(1,7):
            td = datetime.datetime.now()-datetime.timedelta(minutes=k)
            tt = td.strftime("%H:%M")
            tm = td.strftime('%Y%m%d%H%M')
            tables = ('外部域名','分钟并发')
            httpry_Key = 'httpry_domain.%s' % tm
            values[tt] = [[url,int(RC.zscore(httpry_Key, url))] for url in RC.zrevrange(httpry_Key, 0, 10)]
        return render_template('gateway_domain.html',Main_Infos=g.main_infos,tables = tables,values=values,TOP_URL_DATA=TOP_URL_DATA)
    except Exception as e:
        logging.error(e)
        flash('获取数据错误!')
        return render_template('Message_static.html', Main_Infos=g.main_infos)

@page_chart_center.route('/chart_center_ip')
@page_chart_center.route('/chart_center_ip/<ip>')
@main_info.main_info
def chart_center_ip(ip=None):
    tt = time.strftime('%Y%m%d', time.localtime())
    th = time.strftime('%Y%m%d%H', time.localtime())
    tm = time.strftime('%M', time.localtime())
    try:
        if ip:
            ip_domain_key = 'top_%s_domain_%s' %(ip,tt)
            ip_domain_hour_key = 'top_%s_domain_%s' % (ip,th)
            DOMAIN_DATA = [[str(domain), int(RC.zscore(ip_domain_key,domain))] for domain in RC.zrevrange(ip_domain_key, 0, 20)]
            DOMAIN_DATA_HOUR = [[str(domain), int(RC.zscore(ip_domain_hour_key,domain))] for domain in RC.zrevrange(ip_domain_hour_key, 0, 20)]
            return render_template('chart_center_ip.html',Main_Infos=g.main_infos,DOMAIN_DATA=DOMAIN_DATA, DOMAIN_DATA_HOUR=DOMAIN_DATA_HOUR,ip=ip,tm=tm,domain=True)
        else:
            ip_key = 'top_ip_%s' % tt
            ip_key_hour = 'top_ip_%s' % th
            IP_AREA = [[str(ip),ip_area.Search(ip)] for ip in RC.zrevrange(ip_key, 0, 20)]
            IP_AREA_HOUR = [[str(ip), ip_area.Search(ip)] for ip in RC.zrevrange(ip_key_hour, 0, 20)]
            return render_template('chart_center_ip.html',Main_Infos=g.main_infos,IP_AREA=IP_AREA,IP_AREA_HOUR=IP_AREA_HOUR,tm=tm,domain=False)
    except Exception as e:
        logging.error(e)
        flash('获取数据错误!')
        return render_template('Message_static.html', Main_Infos=g.main_infos)

@page_chart_center.route('/chart_center_url')
@main_info.main_info
def chart_center_url():
    tm = datetime.datetime.now() - datetime.timedelta(minutes=1)
    tm = tm.strftime('%Y%m%d%H%M')
    top_url_minute = 'top_url_%s' % tm
    th = time.strftime('%Y%m%d%H', time.localtime())
    top_url_hour = 'top_url_%s' % th
    top2_url_hour = 'top2_url_hour_%s' % th
    top2_url_minute = 'top2_url_minute_%s' % tm
    MM = time.strftime('%M', time.localtime())
    try:
        URL_DATA_HOUR = [[str(url), int(RC.zscore(top_url_hour, url))] for url in RC.zrevrange(top_url_hour, 0, 15)]
        URL_DATA_MINUTE = [[str(url), int(RC.zscore(top_url_minute,url))] for url in RC.zrevrange(top_url_minute, 0, 15)]
        URL_DATA_HOUR2 = [[str(url), int(RC.zscore(top2_url_hour, url))] for url in RC.zrevrange(top2_url_hour, 0, 15)]
        URL_DATA_MINUTE2 = [[str(url), int(RC.zscore(top2_url_minute, url))] for url in RC.zrevrange(top2_url_minute, 0,15)]
        return render_template('chart_center_url.html',Main_Infos=g.main_infos, URL_DATA_MINUTE=URL_DATA_MINUTE,URL_DATA_HOUR=URL_DATA_HOUR,URL_DATA_MINUTE2=URL_DATA_MINUTE2,URL_DATA_HOUR2=URL_DATA_HOUR2,MM=MM)
    except Exception as e:
        logging.error(e)
        flash('获取数据错误!')
        return render_template('Message_static.html', Main_Infos=g.main_infos)
@page_chart_center.before_request
@check.login_required(grade=10)
def check_login(error=None):
    produce.Async_log(g.user, request.url)

@page_chart_center.route('/chart_system')
@main_info.main_info
def chart_system():
    try:
        disk_data = network_data = disk_data_time = network_data_time = None
        Key = 'check_hosts_disk'
        values = RC.hgetall(Key)
        if values:
            disk_data = {host:eval(values[host]) for host in values}
            disk_data_time = RC.get('%s_time'%Key)
        Key = 'check_hosts_net'
        values = RC.hgetall(Key)
        if values:
            network_data = {host:eval(values[host]) for host in values}
            network_data_time = RC.get('%s_time' % Key)
        return render_template('chart_system.html',Main_Infos=g.main_infos, disk_data = disk_data,network_data = network_data,disk_data_time=disk_data_time,network_data_time=network_data_time)
    except Exception as e:
        logging.error(e)
        flash('获取数据错误!')
        return render_template('Message_static.html', Main_Infos=g.main_infos)
@page_chart_center.before_request
@check.login_required(grade=10)
def check_login(error=None):
    produce.Async_log(g.user, request.url)

@page_chart_center.route('/chart_redis_cluster_info')
@page_chart_center.route('/chart_redis_cluster_info/<redis_host>')
@main_info.main_info
def chart_redis_cluster_info(redis_host=None):
    try:
        Redis_Key = 'redis_cluster_java_info'
        Infos = RC.hgetall(Redis_Key)
        Infos = {str(host):eval(Infos[host]) for host in Infos}
        charts_data = {}
        if redis_host:
            db = db_idc.idc_redis_cluster_info
            dt = time.strftime('%Y-%m-%d',time.localtime())
            #keys
            add_keys = db.query.with_entities(db.gettime,db.add_keys).filter(and_(db.getdate == dt,db.master == redis_host)).order_by(db.gettime).all()
            add_keys = [{'data':[[str('%s %s'%(dt,values[0])),int(values[1])] for values in add_keys],'name':'add_keys'}]
            charts_data['add_keys'] = add_keys
            #连接数
            connected_clients = db.query.with_entities(db.gettime,db.connected_clients).filter(and_(db.getdate == dt,db.master == redis_host)).order_by(db.gettime).all()
            connected_clients = [{'data':[[str('%s %s'%(dt,values[0])),int(values[1])] for values in connected_clients],'name':'connected_clients'}]
            charts_data['connected_clients'] = connected_clients
            #命中率
            HitRate = db.query.with_entities(db.gettime,db.HitRate).filter(and_(db.getdate == dt,db.master == redis_host)).order_by(db.gettime).all()
            HitRate = [{'data':[[str('%s %s'%(dt,values[0])),int(values[1])] for values in HitRate],'name':'HitRate'}]
            charts_data['HitRate'] = HitRate
            #执行指令
            commands = db.query.with_entities(db.gettime,db.commands).filter(and_(db.getdate == dt,db.master == redis_host)).order_by(db.gettime).all()
            commands = [{'data':[[str('%s %s'%(dt,values[0])),int(values[1])] for values in commands],'name':'commands'}]
            charts_data['commands'] = commands
            #入口流量
            net_input = db.query.with_entities(db.gettime,db.net_input).filter(and_(db.getdate == dt,db.master == redis_host)).order_by(db.gettime).all()
            net_input = [{'data':[[str('%s %s'%(dt,values[0])),int(values[1])] for values in net_input],'name':'net_input(MB)'}]
            charts_data['net_input'] = net_input
            #出口流量
            net_output = db.query.with_entities(db.gettime,db.net_output).filter(and_(db.getdate == dt,db.master == redis_host)).order_by(db.gettime).all()
            net_output = [{'data':[[str('%s %s'%(dt,values[0])),int(values[1])] for values in net_output],'name':'net_output(MB)'}]
            charts_data['net_output'] = net_output
        return render_template('chart_redis_cluster_info.html',Main_Infos=g.main_infos,Infos=Infos,charts_data=charts_data,redis_host=redis_host)
    except Exception as e:
        logging.error(e)
        flash('获取数据错误!')
        return render_template('Message_static.html', Main_Infos=g.main_infos)
    finally:
        db_idc.DB.session.remove()
@page_chart_center.before_request
@check.login_required(grade=10)
def check_login(error=None):
    produce.Async_log(g.user, request.url)
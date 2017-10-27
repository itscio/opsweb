#-*- coding: utf-8 -*-
import time
import datetime
from flask import Blueprint,render_template,g,request,make_response,flash
from Modules import loging,check ,produce,db_op,main_info
import string
from rediscluster import RedisCluster
import __init__
app = __init__.app
logging = loging.Error()
nodes = app.config.get('NODES_PRODUCE')
RC = RedisCluster(startup_nodes=nodes,decode_responses=True,)
page_index=Blueprint('index',__name__)
@page_index.route('/index')
@main_info.main_info
def index():
    try:
        tm = datetime.datetime.now() - datetime.timedelta(minutes=1)
        tm = tm.strftime('%Y%m%d%H%M')
        td = time.strftime("%Y-%m-%d", time.localtime())
        Tra_ser_minute_Key = 'traffic.ser.%s' % tm
        Tra_cli_minute_Key = 'traffic.cli.%s' % tm
        tt = time.strftime('%Y%m%d', time.localtime())
        th = time.strftime('%Y%m%d%H', time.localtime())
        TM = time.strftime('%M', time.localtime())
        ip_key = 'top_ip_%s' % tt
        ip_key_hour = 'top_ip_%s' % th
        IP_DATA = [[str(ip), int(RC.zscore(ip_key, ip))] for ip in RC.zrevrange(ip_key, 0, 20)]
        IP_DATA_HOUR = [[str(ip), int(RC.zscore(ip_key_hour, ip))] for ip in RC.zrevrange(ip_key_hour, 0, 20)]
        val_cli = [[str(url), int(RC.zscore(Tra_cli_minute_Key,url))*8/1024/1024] for url in RC.zrevrange(Tra_cli_minute_Key, 0,10) if int(RC.zscore(Tra_cli_minute_Key,url))*8/1024/1024 > 1]
        val_ser = [[str(url), int(RC.zscore(Tra_ser_minute_Key,url))*8/1024/1024] for url in RC.zrevrange(Tra_ser_minute_Key, 0,10) if int(RC.zscore(Tra_ser_minute_Key,url))*8/1024/1024 > 1]
        INTERNET_DATA = [eval(v) for v in RC.lrange('internet_access_%s' %td, 0, -1)]
        INTERNET_DATA = [INTERNET_DATA[i] for i in range(0,len(INTERNET_DATA),2)]
        INTRANET_DATA = [eval(v) for v in RC.lrange('intranet_access_%s' %td, 0, -1)]
        INTRANET_DATA = [INTRANET_DATA[i] for i in range(0,len(INTRANET_DATA),2)]
        WEB_ACCESS = [{'data':INTERNET_DATA, 'name': 'internet'},{'data': INTRANET_DATA, 'name': 'intranet'}]
        app_resp = make_response(render_template('index.html',Main_Infos = g.main_infos,val_cli=val_cli,val_ser=val_ser,WEB_ACCESS=WEB_ACCESS,IP_DATA=IP_DATA,IP_DATA_HOUR=IP_DATA_HOUR,tm=TM))
        app_resp.set_cookie('secret_key',produce.Produce(length=6,chars=string.digits))
        return app_resp
    except Exception as e:
        logging.error(e)
        flash('获取数据错误!')
        return render_template('Message_static.html', Main_Infos=g.main_infos)
@page_index.before_request
@check.login_required(grade=10)
def check_login(error=None):
    produce.Async_log(g.user, request.url)
@page_index.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
#-*- coding: utf-8 -*-
from flask import Blueprint,render_template,render_template_string
from Modules import check,loging
from rediscluster import RedisCluster
import time
import __init__
app = __init__.app
nodes = app.config.get('NODES_PRODUCE')
RC = RedisCluster(startup_nodes=nodes,decode_responses=True,)
page_chart = Blueprint('chart', __name__)
@page_chart.route('/chart')
@check.login_required(grade=10)
def charts():
    try:
        val_cli = {}
        val_ser = {}
        tt = int(time.strftime('%Y%m%d', time.localtime()))
        traffic_key = 'traffic_Keys_%s' %tt
        for key in RC.smembers(traffic_key):
            key = '{0}_old'.format(key)
            if RC.exists(key):
                data = eval(str(RC.get(key)))
                if data and isinstance(data,list):
                    va = int(reduce(lambda x, y: int(x) + int(y), data))
                    v = va * 8 / 1024 / 1024
                    key = key.split('_')
                    domain = str(key[-2])
                    if v > 1:
                        if 'traffic.client' in str(key[0]):
                            val_cli[domain] = v
                        if 'traffic.server' in str(key[0]):
                            val_ser[domain] = v
        DATA = [eval(v) for v in RC.lrange('internet_access', 0, -1)]
        DATA = [DATA[i] for i in xrange(0,len(DATA),3)]
        INTERNET_ACCESS = [{'data':DATA, 'name': 'WEB_ACCESS'}]
        return render_template('chart.html',val_cli=val_cli,val_ser=val_ser,INTERNET_ACCESS=INTERNET_ACCESS)
    except Exception as e:
        loging.write(e)
        return render_template_string('获取数据错误!')


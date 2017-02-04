#-*- coding: utf-8 -*-
from flask import Blueprint,json,jsonify,request
from Modules import loging
import urllib2
import __init__
app = __init__.app
limiter = __init__.limiter
page_zabbix_api = Blueprint('zabbix_api', __name__)
@page_zabbix_api.route('/zabbix_api')
@limiter.exempt
def zabbix_api():
    try:
        def API_get(method, DATAS):
            # 调用zabbix的API接口
            url = "http://"
            header = {"Content-Type": "application/json"}
            data = json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": method,
                    "params": DATAS,
                    "id": 0,
                    "auth": ""
                })
            request = urllib2.Request(url, data)
            for key in header:
                request.add_header(key, header[key])
            try:
                result = urllib2.urlopen(request)
            except Exception as e:
                loging.write(e)
            else:
                response = json.loads(result.read())
                result.close()
            return response['result']

        def GET_value(host,method):
            # 构造zabbix需要的json数据
            DATAS = {"output": "extend","filter": {"host": [host]}}
            value = API_get(method, DATAS)
            loging.write(value[0])
            return value[0]

        def Get_arg(arg):
            # 解析请求参数
            loging.write(request.args)
            if arg in request.args:
                return request.args[arg].encode('utf-8')
            else:
                return None
        host = Get_arg('host')
        method = Get_arg('method')
    except Exception as e:
        return jsonify({'Error':str(e)})
    else:
        if host and method:
            return jsonify({'results':str(GET_value(host, method))})
        else:
            return jsonify({'Error':'parameter error'})
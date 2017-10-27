import loging
import urllib2
import json
import __init__
app = __init__.app
logging = loging.Error()
def GET_value(host, key, method, history):
    def API_get(method, DATAS):
        zabbix_auth = app.config.get('ZABBIX_AUTH')
        zabbix_auth["method"] = method
        zabbix_auth["params"] = DATAS
        url = app.config.get('ZABBIX_URL')
        header = {"Content-Type": "application/json"}
        data = json.dumps(zabbix_auth)
        request = urllib2.Request(url, data)
        for key in header:
            request.add_header(key, header[key])
        try:
            result = urllib2.urlopen(request)
        except Exception as e:
            logging.error(e)
        else:
            response = json.loads(result.read())
            result.close()
            return response['result']
    DATAS = {"output": ["itemids", "key_"], "host": host, "search": {"key_": key}}
    API_value = API_get('item.get', DATAS)
    if API_value:
        itemids = str(API_get('item.get', DATAS)[0]['itemid'])
        DATAS = {"output": "extend", "history": history, "itemids": itemids, "sortfield": "clock",
                 "sortorder": "DESC",
                 "limit": 1}
        value = API_get(method, DATAS)
        print(value)
        if value:
            value = str(value[0]['value'])
            return value
        else:
            return None
    else:
        return None
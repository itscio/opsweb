#-*- coding: utf-8 -*-
from flask import Flask
import requests
import time
import datetime
import pytz
from Modules import loging,db_idc
import dns.resolver
from random import choice
import string
import json
from pyzabbix import ZabbixAPI
from kubernetes import config
app = Flask(__name__)
logging = loging.Error()
app.config.from_pyfile('../conf/zabbix.conf')
app.config.from_pyfile('../conf/jump.conf')
zabbix_url = app.config.get('ZABBIX_URL')
zabbix_user = app.config.get('ZABBIX_USER')
zabbix_pw = app.config.get('ZABBIX_PW')
tokenUrl = app.config.get('TOKENURL')
assetsUrl = app.config.get('ASSETSURL')
username = app.config.get('USERNAME')
password = app.config.get('PASSWORD')
def Produce(length=8,chars=string.ascii_letters+string.digits):
    return ''.join([choice(chars) for i in range(length)])

def dingding_msg(text,alart_token=None):
    '''
    :param text:list
    '''
    th = time.strftime("%H", time.localtime())
    #6点以后报警
    if int(th) > 6:
        try:
            td = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            headers = {'Content-Type': 'application/json'}
            urls = ["https://oapi.dingtalk.com/robot/send?access_token=2c5d2dd93f4866b4d25ba60d25d4fdf9031d7b2edf63f5f7e307d5315948f013"]
            if alart_token:
               urls.append(alart_token)
            if isinstance(text, list):
                text.append("*%s*" % td)
                data = {
                    "msgtype": "markdown",
                    "markdown": {"title": "[关注] 新报警信息!",
                                 "text": ' \n\n'.join([ str(line) for line in text])},
                    "at": {
                        "atMobiles": [
                        ],
                        "isAtAll": False
                    }
                }
                for url in set(urls):
                    try:
                        requests.post(url, data=json.dumps(data), headers=headers)
                    except Exception as e:
                        logging.error(e)
                        continue
        except Exception as e:
            logging.error(e)

def dig(domain):
    '''
    :param domain:str
    '''
    addr = []
    try:
        A = dns.resolver.query(domain,'A')
        for i in A.response.answer:
            for j in i.items:
                try:
                     if j.rdtype == 1:
                         addr.append(j.address)
                except Exception as e:
                    logging.error(e)
                    continue
        return addr
    except Exception as e:
        logging.error(e)

def time_format(iso8601):
    try:
        if 'T' in iso8601:
            iso8601 = iso8601.split('T')
            y, m, d = iso8601[0].split('-')
            if '-' in iso8601[1]:
                H, M, S = iso8601[1].split('-')[0].split(':')
                tz = 0 - int(iso8601[1].split('-')[1].split(':')[0])
            if '+' in iso8601[1]:
                H, M, S = iso8601[1].split('+')[0].split(':')
                tz = int(iso8601[1].split('+')[1].split(':')[0])
            dd = datetime.datetime(int(y), int(m), int(d), int(H), int(M), int(S), tzinfo=pytz.timezone('Asia/Shanghai'))
            dd = dd + datetime.timedelta(hours= 8-tz)
            return dd.strftime('%Y-%m-%d %H:%M:%S').split()
    except Exception as e:
        logging.error(e)

def format_day_date(date):
    try:
        date = date.split('-')
        if len(date) ==3:
            if int(date[1]) <10:
                date[1] = '0%s' %int(date[1])
            if int(date[2]) <10:
                date[2] = '0%s' %int(date[2])
            date = '-'.join(date)
        return date
    except Exception as e:
        logging.error(e)

def k8s_conf():
    config_file="%s/../conf/k8s.conf" % app.root_path
    contexts, active_context = config.list_kube_config_contexts(config_file)
    contexts = [context['name'] for context in contexts]
    config.load_kube_config(config_file, context=active_context['name'])
    return(config,contexts,config_file)

class zabbix_api(object):
    def __init__(self):
        self.zapi = ZabbixAPI(zabbix_url)
        self.zapi.session.auth = (zabbix_user, zabbix_pw)
        self.zapi.session.verify = False
        self.zapi.timeout = 5
        self.zapi.login(zabbix_user, zabbix_pw)
        self.val = 0.0
    def zabbix_history(self,host, key):
        try:
            results = self.zapi.host.get(filter={"host": host})
            if results:
                hostid = results[0]['hostid']
                results = self.zapi.item.get(hostids=hostid, output=["itemids", 'key_'], search={"key_": key})
                if results:
                    itemid = results[0]['itemid']
                    for history in (0, 1, 2, 3, 4):
                        vals = self.zapi.history.get(history=history, itemids=itemid, limit=1, sortfield='clock',
                                                sortorder="DESC")
                        if vals:
                            if (int(time.time()) - int(vals[0]['clock'])) < 2000:
                                self.val = float('%.2f' % float(vals[0]['value'].strip()))
                                return self.val
        except Exception as e:
            logging.error(e)
        finally:
            return self.val
    def zabbix_logout(self):
        self.zapi.user.logout()

def get_server_list():
    hosts = []
    try:
        res = requests.post(tokenUrl, data={
            "username": username,
            "password": password
        })
        res = res.json()
        headers = {
            "Authorization": "%s %s" % ("Bearer ", res["token"])
        }
        res  = requests.get(assetsUrl, headers=headers,timeout=30)
        idcs = requests.get("https://xxx.xxx.com/api/assets/v1/labels", headers=headers, timeout=30)
        idcs = {info['id']:info['value'] for info in idcs.json()}
        for info in res.json():
            idc = idcs[info['labels'][0]]
            if idc != 'lan':
                hosts.append((info['ip'],info['port'],info['hostname'],idc))
    except Exception as e:
        logging.error(e)
    finally:
        return list(set(hosts))

def http_args(request,arg):
    #解析请求参数
    args = request.args.to_dict()
    if arg in args:
        return args[arg]
    else:
        return None

def real_ip(ip):
    try:
        db_servers = db_idc.idc_servers
        val = db_servers.query.filter(db_servers.ip == ip).all()
        if not val:
            val = db_servers.query.with_entities(db_servers.ip).filter(db_servers.s_ip.like('%{0};%'.format(ip))).all()
            if val:
                ip = val[0][0]
    except Exception as e:
        logging.error(e)
    finally:
        db_idc.DB.session.remove()
        return ip

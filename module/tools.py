#-*- coding: utf-8 -*-
from flask import Flask,request,render_template_string,session
import requests
from functools import wraps
import time
import re
import datetime
import pytz
from module import loging,db_idc
import dns.resolver
from random import choice
import string
import json
import redis
import socket
from flask_sqlalchemy import SQLAlchemy
from pyzabbix import ZabbixAPI
from kubernetes import config
app = Flask(__name__)
logging = loging.Error()
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/tokens.conf')
app.config.from_pyfile('../conf/zabbix.conf')
app.config.from_pyfile('../conf/jump.conf')
app.config.from_pyfile('../conf/security.conf')
zabbix_url = app.config.get('ZABBIX_URL')
zabbix_user = app.config.get('ZABBIX_USER')
zabbix_pw = app.config.get('ZABBIX_PW')
tokenUrl = app.config.get('TOKENURL')
assetsUrl = app.config.get('ASSETSURL')
username = app.config.get('USERNAME')
password = app.config.get('PASSWORD')
alarm_token = app.config.get('ALARM_TOKEN')
white_list = app.config.get('WHITE_LIST')
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
Redis = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
HOST = socket.gethostbyname(socket.gethostname())
def Async_log(user,url):
    try:
        url = url.replace('op_servers', 'op.moji.com')
        if 'op.moji.com' in url and not url.endswith('/index'):
            ip = session['remote_ip']
            Key = 'op_http_log_%s' %time.strftime('%Y-%m-%d',time.localtime())
            Redis.hset(Key,time.strftime('%H:%M:%S',time.localtime()),[ip,user,url])
            Redis.expire(Key,864000)
    except Exception as e:
        logging.error(e)

def timestamp(i):
    '''
    i is 0 days ago
    '''
    if i>=1:
        t = (datetime.datetime.now() + datetime.timedelta(days=1))
    else:
        t = (datetime.datetime.now() - datetime.timedelta(days=1))
    tp = int(time.mktime(t.timetuple()))
    return tp

def Produce(length=8,chars=string.ascii_letters+string.digits):
    return ''.join([choice(chars) for i in range(length)])

def dingding_msg(text,token=None):
    '''
    :param text:list
    '''
    try:
        td = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        headers = {'Content-Type': 'application/json'}
        urls = []
        if not token:
            urls.append(alarm_token)
        if token:
           urls.append(token)
        if isinstance(text, list):
            text.append("*%s*" % td)
            data = {
                "msgtype": "markdown",
                "markdown": {"title": "[关注消息]",
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
        idcs = requests.get(app.config.get('JPSURL'), headers=headers, timeout=30)
        idcs = {info['id']:info['value'] for info in idcs.json()}
        for info in res.json():
            idc = idcs[info['labels'][0]]
            if idc not in ('lan','j'):
                hosts.append((info['ip'],info['port'],info['hostname'],idc))
    except Exception as e:
        logging.error(e)
    finally:
        return list(set(hosts))

def modify_jumpserver_comment(hostname,comment):
    try:
        status_code = None
        res = requests.post(tokenUrl, data={
            "username": username,
            "password": password
        })
        res = res.json()
        headers = {
            "Authorization": "%s %s" % ("Bearer ", res["token"]),
            'dataType': 'json',
            'contentType': 'application/json;charset=UTF-8'
        }
        res = requests.get("%s?hostname=%s" %(assetsUrl,hostname), headers=headers).json()
        res = res[0]
        res['comment'] = comment
        res = requests.put("%s%s/"%(assetsUrl,res['id']),data=res,headers=headers)
        status_code = res.status_code
    except Exception as e:
        logging.error(e)
    finally:
        return status_code

def http_args(request,arg):
    #解析请求参数
    args = request.args.to_dict()
    if arg in args:
        return args[arg]
    else:
        return None

def real_ip(ip):
    try:
        #缓存查询加速
        Key = 'op_real_ip_list'
        val = Redis.hget(Key,ip)
        if val:
            ip = val
        else:
            db_servers = db_idc.idc_servers
            val = db_servers.query.filter(db_servers.ip == ip).all()
            if val:
                Redis.hset(Key, ip,ip)
            else:
                val = db_servers.query.with_entities(db_servers.ip).filter(db_servers.s_ip.like('%{0};%'.format(ip))).all()
                if val:
                    ip = val[0][0]
                    Redis.hset(Key,ip,val[0][0])
    except Exception as e:
        logging.error(e)
    finally:
        db_idc.DB.session.remove()
        return ip

def check_chinese(char):
    char = char.decode('utf8')
    if re.search(u"[\u4e00-\u9fa5]+",char):
        return True
    else:
        return False

#任务执行锁
def proce_lock(func):
    @wraps(func)
    def LOCK(*args, **kwargs):
        try:
            time.sleep(choice([i for i in range(1,10)]))
            if Redis.exists('task_%s'%func.__name__):
                raise AssertionError
            Redis.set('task_%s' %func.__name__, HOST)
            Redis.expire('task_%s' % func.__name__,15)
            return func(*args, **kwargs)
        except:
            pass
    return LOCK

#访问ip限制
def acl_ip(func):
    @wraps(func)
    def check_ip(*args, **kwargs):
        ip_check = []
        try:
            if request.headers['X-Forwarded-For']:
                src_ip = request.headers['X-Forwarded-For']
            else:
                src_ip = request.remote_addr
        except:
            src_ip = request.remote_addr
        if ',' in src_ip:
            src_ip = src_ip.split(',')[0]
        for ip in white_list:
            if '/' in ip:
                mask = ip.split('/')[1]
                if mask == '32':
                    ip = ip.split('.')
                if mask == '24':
                    ip = ip.split('.')[:3]
                if mask == '16':
                    ip = ip.split('.')[:2]
                if mask == '8':
                    ip = ip.split('.')[:1]
                if src_ip.startswith('.'.join(ip)):
                    ip_check.append(True)
            else:
                if ip == src_ip:
                    ip_check.append(True)
        if not ip_check:
            return render_template_string('%s 该IP地址未被授权访问!' % src_ip)
        return func(*args, **kwargs)
    return check_ip
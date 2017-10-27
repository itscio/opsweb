#-*- coding: utf-8 -*-
import Mysql
import loging
import memcache
import kestrel
import datetime
import os
import redis
import json
import socket
import check
import zabbix_api
import SSH
import Md5
import time
from Modules import db_idc
from rediscluster import RedisCluster
from sqlalchemy import and_
from confluent_kafka import Consumer, KafkaError
from multiprocessing.dummy import Pool as ThreadPool
import __init__
app = __init__.app
logging = loging.Error()
kafka_hosts = app.config.get('KAFKA_HOSTS_HAPROXY')
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
Redis = redis.Redis(redis_host, redis_port)
nodes = app.config.get('NODES_PRODUCE')
cluster_java_nodes = app.config.get('NODES_CLUSTER_JAVA')
RC = RedisCluster(startup_nodes=nodes,decode_responses=True)
USER = app.config.get('MYSQL_USER')
PASSWORD = app.config.get('MYSQL_PASSWORD')
HOST = app.config.get('MYSQL_HOST')
PORT = app.config.get('MYSQL_PORT')
BACKUP_SERVERS = app.config.get('BACKUP_SERVERS')
NOT_BACKUP_MYSQL = app.config.get('NOT_BACKUP_MYSQL')
TWEMPROXY_HOSTS = app.config.get('TWEMPROXY_HOSTS')
HA_SERVERS = app.config.get('HA_SERVERS')
DB = 'idc'
dt = time.strftime('%m%d',time.localtime())
def analytics_internet_logs():
    consumer = Consumer({'bootstrap.servers': kafka_hosts, 'group.id': 'Internet_logs_%s' %dt,'default.topic.config': {'auto.offset.reset': 'latest','auto.commit.enable':'true'}})
    consumer.subscribe(['haproxy_logs'])
    try:
        while True:
            msg = consumer.poll()
            if not msg.error():
                Msg = msg.value().decode('utf-8').strip()
                try:
                    tt = time.strftime('%Y%m%d', time.localtime())
                    th = time.strftime('%Y%m%d%H', time.localtime())
                    pv_key = 'baihe_pv_%s' % tt
                    if Msg:
                        Msg = Msg.split()
                        RC.incr(pv_key)
                        if len(Msg) >= 17:
                            Topic = str(Msg[14]).split('|')[0].replace('{', '').strip()
                            IP = str(Msg[5])
                            H_key = 'haproxy_topic_%s' % tt
                            top_ip = 'top_ip_%s' % tt
                            top_ip_hour = 'top_ip_%s' % th
                            top_url_hour = 'top_url_%s' % th
                            PATH = str(Msg[16]).split('?')[0]
                            URL = 'http://%s%s' % (Topic,PATH)
                            Ha_Key = 'haproxy_logs_%s_%s' % (tt, Topic)
                            top_ip_domain = 'top_%s_domain_%s' % (IP, tt)
                            top_ip_domain_hour = 'top_%s_domain_%s' % (IP, th)
                            for KEY in (H_key, pv_key, top_ip, top_url_hour, top_ip_hour,Ha_Key, top_ip_domain, top_ip_domain_hour):
                                RC.expire(KEY,3600)
                            RC.sadd(H_key, Topic)
                            RC.incr(Ha_Key)
                            # ip
                            RC.zincrby(top_ip, IP, 1)
                            RC.zincrby(top_ip_hour, IP, 1)
                            # IP_接口
                            RC.zincrby(top_ip_domain, URL, 1)
                            RC.zincrby(top_ip_domain_hour, URL, 1)
                            # 接口
                            RC.zincrby(top_url_hour, URL, 1)
                except:
                    continue
            elif msg.error().code() != KafkaError._PARTITION_EOF:
                logging.error(msg.error())
                continue
    except Exception as e:
        logging.error(e)
    finally:
        consumer.close()
def analytics_internet2_logs():
    consumer = Consumer({'bootstrap.servers': kafka_hosts, 'group.id': 'Internet2_logs_%s' %dt,'default.topic.config': {'auto.offset.reset': 'latest','auto.commit.enable':'true'}})
    consumer.subscribe(['haproxy_logs'])
    try:
        while True:
            msg = consumer.poll()
            if not msg.error():
                Msg = msg.value().decode('utf-8').strip()
                try:
                    tt = time.strftime('%Y%m%d', time.localtime())
                    tm = time.strftime('%Y%m%d%H%M', time.localtime())
                    Tm = time.strftime('%H:%M', time.localtime())
                    Tra_ser_minute_Key = 'traffic.ser.%s' % tm
                    Tra_cli_minute_Key = 'traffic.cli.%s' % tm
                    if Msg:
                        Msg = Msg.split()
                        if len(Msg) >= 17:
                            traffic_cli = Msg[10]
                            traffic_ser = Msg[11]
                            Topic = str(Msg[14]).split('|')[0].replace('{', '').strip()
                            IP = str(Msg[5])
                            Rtime = Msg[8].split('/')[-1]
                            if Rtime.isdigit():
                                Rtime = int(Rtime)
                            else:
                                Rtime = 0
                            uv_key = 'baihe_uv_%s' % tt
                            Rt_Key = 'Rtime_%s_%s' % (tt, Topic)
                            PATH = str(Msg[16]).split('?')[0]
                            URL = 'http://%s%s' % (Topic,PATH)
                            Tra_ser_url_minute_Key = 'traffic.ser.url_%s' % Tm
                            Tra_cli_url_minute_Key = 'traffic.cli.url_%s' % Tm
                            for KEY in (uv_key,Rt_Key,Tra_ser_url_minute_Key,Tra_cli_url_minute_Key):
                                RC.expire(KEY,3600)
                            # 流量
                            if traffic_ser.isdigit() and traffic_cli.isdigit():
                                RC.zincrby(Tra_cli_url_minute_Key, URL, int(traffic_cli))
                                RC.zincrby(Tra_ser_url_minute_Key,URL, int(traffic_ser))
                                # 实时流量
                                RC.zincrby(Tra_cli_minute_Key, Topic, int(traffic_cli))
                                RC.expire(Tra_cli_minute_Key, 300)
                                RC.zincrby(Tra_ser_minute_Key, Topic, int(traffic_ser))
                                RC.expire(Tra_ser_minute_Key, 300)
                            #
                            if Rtime:
                                RC.lpush(Rt_Key, Rtime)
                                RC.sadd(uv_key, IP)
                except Exception as e:
                    logging.error(e)
                    continue
            elif msg.error().code() != KafkaError._PARTITION_EOF:
                logging.error(msg.error())
                continue
    except Exception as e:
        logging.error(e)
    finally:
        consumer.close()
def analytics_internet3_logs():
    consumer = Consumer({'bootstrap.servers': kafka_hosts, 'group.id': 'Internet3_logs_%s' %dt,
                         'default.topic.config': {'auto.offset.reset': 'latest', 'auto.commit.enable': 'true'}})
    consumer.subscribe(['haproxy_logs'])
    try:
        while True:
            msg = consumer.poll()
            if not msg.error():
                Msg = msg.value().decode('utf-8').strip()
                try:
                    tm = time.strftime('%Y%m%d%H%M', time.localtime())
                    if Msg:
                        Msg = Msg.split()
                        if len(Msg) >= 17:
                            internet_access_minute = 'internet_access_minute_%s' % tm
                            RC.incr(internet_access_minute)
                            RC.expire(internet_access_minute,3600)
                except Exception as e:
                    logging.error(e)
                    continue
            elif msg.error().code() != KafkaError._PARTITION_EOF:
                logging.error(msg.error())
                continue
    except Exception as e:
        logging.error(e)
    finally:
        consumer.close()
def analytics_intranet_logs():
    consumer = Consumer({'bootstrap.servers': kafka_hosts, 'group.id': 'Intranet_logs_%s' %dt,'default.topic.config': {'auto.offset.reset': 'latest','auto.commit.enable':'true'}})
    consumer.subscribe(['haproxy2_logs'])
    try:
        while True:
            msg = consumer.poll()
            if not msg.error():
                Msg = msg.value().decode('utf-8').strip()
                try:
                    tt = time.strftime('%Y%m%d', time.localtime())
                    th = time.strftime('%Y%m%d%H', time.localtime())
                    tm = time.strftime('%Y%m%d%H%M', time.localtime())
                    H_key = 'haproxy2_topic_%s' % tt
                    top2_url_hour = 'top2_url_hour_%s' % th
                    top2_url_minute = 'top2_url_minute_%s' % tm
                    if len(Msg.split()) >= 17:
                        val = Msg.split('{')
                        if len(val) >= 2:
                            Topic = val[1].split('}')[0]
                            Rtime = val[0].split()[8]
                            Rtime = int(Rtime.split('/')[4])
                            if ':' in Topic:
                                Topic = str(Topic.split(':')[0])
                            if '|' in Topic:
                                Topic = str(Topic.split('|')[0])
                            if '.baihe.com' in Topic:
                                Key = 'haproxy2_logs_%s_%s' % (tt, Topic)
                                Rt_Key = 'Rtime2_%s_%s' % (tt, Topic)
                                # 接口
                                PATH = str(Msg.split()[17]).split('?')[0]
                                URL = 'http://%s%s' % (Topic,PATH)
                                RC.zincrby(top2_url_hour, URL, 1)
                                RC.zincrby(top2_url_minute, URL, 1)
                                for KEY in (H_key, Key, Rt_Key,top2_url_hour,top2_url_minute):
                                    RC.expire(KEY,3600)
                                RC.sadd(H_key, Topic)
                                RC.incr(Key)
                                if Rtime:
                                    RC.lpush(Rt_Key, Rtime)
                except Exception as e:
                    logging.error(e)
                    continue
            elif msg.error().code() != KafkaError._PARTITION_EOF:
                logging.error(msg.error())
                continue
    except Exception as e:
        logging.error(e)
    finally:
        consumer.close()
def analytics_intranet2_logs():
    consumer = Consumer({'bootstrap.servers': kafka_hosts, 'group.id': 'Intranet2_logs_%s' %dt,'default.topic.config': {'auto.offset.reset': 'latest','auto.commit.enable':'true'}})
    consumer.subscribe(['haproxy2_logs'])
    try:
        while True:
            msg = consumer.poll()
            if not msg.error():
                Msg = msg.value().decode('utf-8').strip()
                try:
                    tm = time.strftime('%Y%m%d%H%M', time.localtime())
                    intranet_access_minute = 'intranet_access_minute_%s' %tm
                    if len(Msg.split()) >= 17:
                        RC.incr(intranet_access_minute)
                        RC.expire(intranet_access_minute,3600)
                except Exception as e:
                    logging.error(e)
                    continue
            elif msg.error().code() != KafkaError._PARTITION_EOF:
                logging.error(msg.error())
                continue
    except Exception as e:
        logging.error(e)
    finally:
        consumer.close()
def WAF_logs():
    consumer = Consumer({'bootstrap.servers': kafka_hosts, 'group.id': 'Waf_logs_%s' %dt,'default.topic.config': {'auto.offset.reset': 'latest','auto.commit.enable':'true'}})
    consumer.subscribe(['haproxy_logs'])
    try:
        while True:
            msg = consumer.poll()
            if not msg.error():
                Msg = msg.value().decode('utf-8').strip()
                try:
                    tm = time.strftime('%Y%m%d%H%M',time.localtime())
                    if Msg:
                        Msg = Msg.split()
                        if len(Msg) >= 17:
                            url_code = Msg[9]
                            Topic =str(Msg[14]).split('|')[0].replace('{','').strip()
                            IP = str(Msg[5])
                            if url_code in ('200', '206', '301', '302', '304', '404'):
                                top_ip_minute = 'top_ip_%s' % tm
                                top_url_minute = 'top_url_%s' % tm
                                PATH = str(Msg[16]).split('?')[0]
                                URL = 'http://%s%s' % (Topic,PATH)
                                top_ip_domain_minute = 'top_%s_domain_%s' % (IP, tm)
                                top_url_ip_minute = 'top_%s_ip_%s' % (URL, tm)
                                # ip
                                RC.zincrby(top_ip_minute, IP, 1)
                                RC.expire(top_ip_minute, 300)
                                # IP_接口
                                RC.zincrby(top_ip_domain_minute, URL, 1)
                                RC.expire(top_ip_domain_minute, 300)
                                # 接口
                                RC.zincrby(top_url_minute, URL, 1)
                                RC.expire(top_url_minute, 300)
                                # 接口_ip
                                RC.zincrby(top_url_ip_minute, IP, 1)
                                RC.expire(top_url_ip_minute, 300)
                except Exception as e:
                    logging.error(e)
                    continue
            elif msg.error().code() != KafkaError._PARTITION_EOF:
                logging.error(msg.error())
                continue
    except Exception as e:
        logging.error(e)
    finally:
        consumer.close()
def httpry_logs():
    consumer = Consumer({'bootstrap.servers': kafka_hosts, 'group.id': 'Httpry_logs_%s' %dt,'default.topic.config': {'auto.offset.reset': 'latest','auto.commit.enable':'true'}})
    consumer.subscribe(['httpry_logs'])
    try:
        while True:
            msg = consumer.poll()
            if msg:
                if not msg.error():
                    Msg = msg.value().decode('utf-8').strip()
                    try:
                        tm = time.strftime('%Y%m%d%H%M', time.localtime())
                        httpry_Key = 'httpry_domain.%s' % tm
                        if Msg:
                            msg = Msg.split()
                            if len(msg) == 11:
                                if msg[6] != '-':
                                    RC.zincrby(httpry_Key,msg[6], 1)
                                    RC.expire(httpry_Key,600)
                    except Exception as e:
                        logging.error(e)
                        continue
                elif msg.error().code() != KafkaError._PARTITION_EOF:
                    logging.error(msg.error())
                    continue
    except Exception as e:
        logging.error(e)
    finally:
        consumer.close()
@check.proce_lock
def kafka_internet():
    tt = time.strftime('%Y%m%d', time.localtime())
    H_key = 'haproxy_topic_%s' % tt
    for Topic in RC.smembers(H_key):
        try:
            Key = 'haproxy_logs_%s_%s' % (tt, Topic)
            web_key = 'internet_access_%s_%s' % (tt, Topic)
            Rt_Key = 'Rtime_%s_%s' % (tt, Topic)
            web_rt_key = 'internet_rt_%s_%s' % (tt, Topic)
            for KEY in (web_key, Key, Rt_Key, web_rt_key):
                RC.expire(KEY,3600)
            va = int(RC.getset(Key, 0))
            Rt_va = RC.lrange(Rt_Key, 0, -1)
            if len(Rt_va) > 2:
                Rt_va = reduce(lambda x, y: int(x) + int(y), Rt_va) / len(Rt_va)
                RC.delete(Rt_Key)
                TT = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                Rt_data = [TT, Rt_va]
                RC.rpush(web_rt_key, Rt_data)
                data = [TT, va]
                RC.rpush(web_key, data)
                tt = time.strftime('%Y%m%d', time.localtime())
                H_key = 'haproxy_topic_%s' % tt
        except Exception as e:
            logging.error(e)
            continue
@check.proce_lock
def kafka_intranet():
    tt = time.strftime('%Y%m%d', time.localtime())
    H_key = 'haproxy2_topic_%s' % tt
    for Topic in RC.smembers(H_key):
        try:
            Key = 'haproxy2_logs_%s_%s' % (tt, Topic)
            web_key = 'intranet_access_%s_%s' % (tt, Topic)
            Rt_Key = 'Rtime2_%s_%s' % (tt, Topic)
            web_rt_key = 'intranet_rt_%s_%s' % (tt, Topic)
            for KEY in (web_key, Key, Rt_Key, web_rt_key):
                RC.expire(KEY,3600)
            va = int(RC.getset(Key, 0))
            Rt_va = RC.lrange(Rt_Key, 0, -1)
            if len(Rt_va) > 2:
                Rt_va = reduce(lambda x, y: int(x) + int(y), Rt_va) / len(Rt_va)
                RC.delete(Rt_Key)
                TT = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                Rt_data = [TT, Rt_va]
                RC.rpush(web_rt_key, Rt_data)
                data = [TT, va]
                RC.rpush(web_key, data)
                tt = time.strftime('%Y%m%d', time.localtime())
                H_key = 'haproxy2_topic_%s' % tt
        except Exception as e:
            logging.error(e)
            continue
@check.proce_lock
def task_tables_info():
    MYSQL_IDC = Mysql.MYSQL(USER,PASSWORD,HOST,PORT,DB)
    Table = 'tableinfo'
    cmds = ("TRUNCATE TABLE %s;" %Table,"select ip,port,db from mysqldb;")
    results = map(MYSQL_IDC.Run,cmds)
    for host,port,dbs in results[1]:
        try:
            if '172.16.9.' not in host:
                MYSQL = Mysql.MYSQL(USER,PASSWORD,host,port,'mysql')
                cmd = "show variables like 'version';"
                version = MYSQL.Run(cmd)
                version = version[0][1]  or 'None'
                for db in dbs.split('|'):
                    cmd = "show table status from %s;"  %db
                    results = MYSQL.Run(cmd)
                    if results:
                        for table_info in results:
                            try:
                                Table_Name = table_info[0]
                                Engine = table_info[1] or 'None'
                                Rows = table_info[4]  or 0
                                Charset = table_info[14]  or 'None'
                                cmd = ("insert into %s (ip,port,database_name,table_name,Engine_name,Rows,Charset,version)  VALUES ('%s',%i,'%s','%s','%s',%i,'%s','%s');" %(Table,host,int(port),db,Table_Name,Engine,Rows,Charset,version))
                                MYSQL_IDC.Run(cmd)
                            except Exception as e:
                                logging.error(e)
                                continue
                MYSQL.Close()
        except Exception as e:
            logging.error(e)
            continue
    MYSQL_IDC.Close()
@check.proce_lock
def clear_kestrel():
    MYSQL = Mysql.MYSQL(USER, PASSWORD, HOST, PORT, DB)
    cmd = "select kestrel_ip,kestrel_port,kestrel_key from kestrel where kestrel_num ='0';"
    results = MYSQL.Run(cmd)
    if results:
        MYSQL.Close()
        for ip,port,key in results:
            try:
                Kestrel = memcache.Client(['%s:%s'%(ip,port)],debug=0,socket_timeout=1)
                Kestrel.delete(str(key))
            except Exception as e:
                logging.error(e)
                continue
@check.proce_lock
def check_publish():
    try:
        DB = 'op'
        td  = time.strftime('%Y-%m-%d',time.localtime())
        tt = (datetime.datetime.now()-datetime.timedelta(hours=4)).strftime('%H:%M:%S')
        MYSQL = Mysql.MYSQL(USER, PASSWORD, HOST, PORT, DB)
        cmd = "SELECT DISTINCT(project) FROM op_operation WHERE TYPE = '灰度' AND DATE  = '{0}' AND TIME <= '{1}';".format(td,tt)
        result  = MYSQL.Run(cmd)
        if result:
            for Project in result:
                os.system("/bin/tomail pd.list@baihe.com 灰度发布警告 {0} 项目已经保持灰度状态超过4个时间,请相关开发人员尽快处理!".format(Project[0]))
        MYSQL.Close()
    except Exception as e:
        logging.error(e)
@check.proce_lock
def get_twemproxy_redis():
    MYSQL = Mysql.MYSQL(USER, PASSWORD, HOST, PORT, DB)
    redis_info = {}
    for twemproxy_ip in TWEMPROXY_HOSTS:
            for port in (22222,22220):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect((twemproxy_ip,port))
                    INFOS = json.loads(sock.recv(86400))
                    for key in INFOS:
                        if 'redis_' in key:
                            IP_list = []
                            for ip_key in INFOS[key]:
                                if '172.16.' in ip_key:
                                    IP_list.append(ip_key.split(':')[0])
                            redis_info[key] = IP_list
                except Exception as e:
                    logging.error(e)
                    continue
    cmd = "TRUNCATE TABLE twemproxyInfo;"
    MYSQL.Run(cmd)
    for key in redis_info:
        for ip in redis_info[key]:
            try:
                Redis = redis.StrictRedis(host=ip,port=6379,db=0,socket_timeout=1)
                Keys = Redis.info()['db0']['keys']
                cmd = "insert into twemproxyInfo (serviceGroup,clientIP,clientKeyItems) VALUES('%s','%s','%s');"%(key,ip,Keys)
                MYSQL.Run(cmd)
            except Exception as e:
                logging.error(e)
                continue
    MYSQL.Close()
@check.proce_lock
def zabbix_api_lvs():
    try:
        t = time.strftime('%H',time.localtime())
        tm = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime())
        Key = 'lvs_internet'
        Key1 = 'lvs_intranet'
        if t == '00':
            Redis.delete(Key)
            Redis.delete(Key1)
        key='lvs[80]'
        history = 3
        method = 'history.get'
        host = '172.16.16.8'
        v8 = zabbix_api.GET_value(host,key,method,history)
        host = '172.16.16.4'
        v4 = zabbix_api.GET_value(host,key,method,history)
        host = '172.16.16.5'
        v5 = zabbix_api.GET_value(host,key,method,history)
        if v4 and v8:
            lvs_conn = int(v4)+int(v8)
            Redis.lpush(Key,[tm,lvs_conn])
        if v5:
            Redis.lpush(Key1,[tm,int(v5)])
    except Exception as e:
        logging.error(e)
@check.proce_lock
def zabbix_api_host():
    def Get_values(hosts,Redis_Key,keys,history,preset,operation):
        RC.delete(Redis_Key)
        hosts = [str(host[0]) for host in hosts]
        method = 'history.get'
        RC.set('%s_time' % Redis_Key, time.strftime('%Y-%m-%d %H:%M',time.localtime()))
        def Run(host):
            try:
                values = {}
                for key in keys:
                    value = zabbix_api.GET_value(host, keys[key], method, history)
                    if value != None:
                        if '.' in value:
                            value = float(value)
                        if operation == 'lt':
                            if int(value) < preset:
                                values[key] = value
                                RC.hset(Redis_Key, host, values)
                        if operation == 'gt':
                            if int(value) > preset:
                                values[key] = value
                                RC.hset(Redis_Key, host, values)
            except Exception as e:
                logging.error(e)
        pool = ThreadPool(4)
        pool.map_async(Run,hosts)
        pool.close()
        pool.join()
    try:
        db = db_idc.idc_servers
        hosts = db.query.with_entities(db.ip).filter(and_(db.department == '线上业务中心',db.status == '使用中',db.system.like('CentOS%'))).all()
        if hosts:
            history = 0
            preset = 20
            operation = 'lt'
            Redis_Key = 'check_hosts_disk'
            keys = {'/home': 'vfs.fs.size[/home,pfree]', '/': 'vfs.fs.size[/,pfree]'}
            Get_values(hosts, Redis_Key, keys, history, preset,operation)
            history = 3
            preset = 5000
            operation = 'gt'
            Redis_Key = 'check_hosts_net'
            keys = {'ESTAB': 'netstat[ESTAB]', 'TIME_WAIT': 'netstat[WAIT]'}
            Get_values(hosts, Redis_Key, keys, history, preset,operation)
    except Exception as e:
        logging.error(e)
@check.proce_lock
def kestel_info():
    MYSQL = Mysql.MYSQL(USER, PASSWORD, HOST, PORT, DB)
    cmd = "truncate table kestrel;"
    MYSQL.Run(cmd)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('172.16.16.50', 22222))
    INFOS = json.loads(sock.recv(86400))
    for key in INFOS:
        try:
            if 'kestrel_' in key:
                for ip_key in INFOS[key]:
                    if '172.16.' in ip_key:
                        ip = ip_key.split(':')[0]
                        ks = kestrel.Client(['%s:22133' % ip.strip()])
                        st = ks.stats()[1]['queues']
                        for k in st:
                            v = st[k]
                            data = (ip,'22133', str(k.replace("'", "")), str(v['items']))
                            cmd = "insert into kestrel (kestrel_ip,kestrel_port,kestrel_key,kestrel_num) values('%s',%s,'%s',%s);" % data
                            MYSQL.Run(cmd)
        except:
            continue
@check.proce_lock
def haproxy_blacklist():
    DB = 'op'
    MYSQL = Mysql.MYSQL(USER, PASSWORD, HOST, PORT, DB)
    file_path = '/tmp/blacklist'
    def write_ip():
        cmd = "SELECT ip FROM haproxy_blacklist;"
        hosts = [str(host[0]) for host in MYSQL.Run(cmd)]
        with open(file_path, 'w') as f:
            for host in hosts:
                f.write('%s\n' % host)
        for ip in HA_SERVERS:
            ssh = SSH.ssh('work',ip)
            ssh.Scp(file_path,file_path)
    tm = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    cmd = "SELECT ip FROM haproxy_blacklist where expire <= '%s' and expire !='0000-00-00 00:00:00';" % tm
    if MYSQL.Run(cmd):
        cmd = "delete from haproxy_blacklist where expire <= '%s' and expire !='0000-00-00 00:00:00';" % tm
        MYSQL.Run(cmd)
        write_ip()
    cmd = "SELECT ip FROM haproxy_blacklist where stats = '1';"
    if MYSQL.Run(cmd):
        cmd = "update haproxy_blacklist set stats = '0';"
        MYSQL.Run(cmd)
        write_ip()
    cmd = "SELECT ip FROM haproxy_blacklist where stats = '2';"
    if MYSQL.Run(cmd):
        cmd = "delete from haproxy_blacklist where stats = '2';"
        MYSQL.Run(cmd)
        write_ip()
    MYSQL.Close()
@check.proce_lock
def vpn_conf():
    def create_file(Type):
        try:
            crypto = Md5.crypto('1qazxsw23edcvfr4')
            file_path = '/tmp/chap-secrets'
            ips = {'intranet':('172.16.9.2', '172.16.9.31'),'internet':('172.16.16.150','172.16.16.151','172.16.16.164','172.16.16.165')}
            cmd = "SELECT user,password FROM vpn_users where vpn_type = '%s';" %Type
            User_list = MYSQL.Run(cmd)
            if User_list:
                with open(file_path,'w') as f:
                    f.write('####### system-config-network will overwrite this part!!! (begin) ##########\r\n')
                    for user,pw in User_list:
                        f.write('%s       *       %s       *\n' %(user,crypto.decrypt(pw)))
                for ip in ips[Type]:
                    ssh = SSH.ssh('work', ip)
                    ssh.Scp(file_path, file_path)
        except Exception as e:
            logging.error(e)
    DB = 'op'
    MYSQL = Mysql.MYSQL(USER, PASSWORD, HOST, PORT, DB)
    for Type in ('intranet','internet'):
        cmd = "SELECT user,password FROM vpn_users where status = 2 and vpn_type = '%s';" %Type
        if MYSQL.Run(cmd):
            cmd = "delete FROM vpn_users where status = 2 and vpn_type = '%s';" %Type
            MYSQL.Run(cmd)
            create_file(Type)
        cmd = "SELECT user,password FROM vpn_users where status = 1 and vpn_type = '%s';" %Type
        if MYSQL.Run(cmd):
            cmd = "update vpn_users set status = 0 where status = 1 and vpn_type = '%s';" %Type
            MYSQL.Run(cmd)
            create_file(Type)
    MYSQL.Close()
@check.proce_lock
def WAF():
    DB = 'op'
    black_list = {}
    white_list = app.config.get('WHITE_LIST')
    tm = datetime.datetime.now() - datetime.timedelta(minutes=1)
    tm = tm.strftime('%Y%m%d%H%M')
    tt = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    th = time.strftime('%Y%m%d%H', time.localtime())
    dm = datetime.datetime.now() + datetime.timedelta(minutes=5)
    expire_time = dm.strftime('%Y-%m-%d %H:%M:%S')
    top_ip_minute = 'top_ip_%s' %tm
    top_url_minute = 'top_url_%s' % tm
    black_ip_minute = 'black_ip_%s' %tm
    black_ip_hour = 'black_ip_%s' % th
    try:
        MYSQL = Mysql.MYSQL(USER, PASSWORD, HOST, PORT, DB)
        ip_list = MYSQL.Run("select ip from haproxy_blacklist;")
        ip_list = [str(ip[0]) for ip in ip_list]
        url_data = MYSQL.Run("select url,counts from url_blacklist where stats='1';")
        if url_data:
            for url,counts in url_data:
                black_list[str(url)] = counts
            # 基于ip统计接口
            IP_DATAS = [str(ip) for ip in RC.zrevrange(top_ip_minute, 0,20) if ip not in white_list if ip not in ip_list]
            if IP_DATAS:
                for ip in IP_DATAS:
                    try:
                        top_ip_domain_minute = 'top_%s_domain_%s' % (ip,tm)
                        URL_DATAS = [[str(url), int(RC.zscore(top_ip_domain_minute,url))] for url in RC.zrevrange(top_ip_domain_minute, 0,-1)]
                        if URL_DATAS:
                            for URL,URL_COUNT in URL_DATAS:
                                try:
                                    # 拦截
                                    if URL in black_list.keys():
                                        if URL_COUNT > int(black_list[URL]):
                                            #pass
                                            RC.lpush(black_ip_minute,ip)
                                            RC.lpush(black_ip_hour,ip)
                                            MYSQL.Run("insert into haproxy_blacklist (addtime,ip,stats,expire,rule) VALUES ('%s','%s','1','%s','%s');" %(tt,ip,expire_time,URL))
                                    #学习
                                    urls = [str(url[0]) for url in MYSQL.Run("select url from url_blacklist;")]
                                    if URL not in urls and URL_COUNT > 60:
                                        MYSQL.Run("insert into url_blacklist (url,counts,stats) VALUES ('%s',%i,'0');" %(URL,URL_COUNT))
                                except Exception as e:
                                    logging.error(e)
                                    continue
                    except Exception as e:
                        logging.error(e)
                        continue
                RC.expire(black_ip_minute,300)
                RC.expire(black_ip_hour, 3600)
            #基于接口统计ip
            URLS = [str(url) for url in RC.zrevrange(top_url_minute, 0,-1)]
            if URLS:
                for url in URLS:
                    if url in black_list.keys():
                        top_url_ip_minute = 'top_%s_ip_%s' % (url, tm)
                        IP_DATAS = [ str(ip) for ip in RC.zrevrange(top_url_ip_minute, 0,-1) if int(RC.zscore(top_url_ip_minute,ip)) > int(black_list[url]) if ip not in white_list if ip not in ip_list]
                        if IP_DATAS:
                            for ip in IP_DATAS:
                                try:
                                    #分钟拦截
                                    RC.lpush(black_ip_minute,ip)
                                    RC.lpush(black_ip_hour,ip)
                                    MYSQL.Run("insert into haproxy_blacklist (addtime,ip,stats,expire,rule) VALUES ('%s','%s','1','%s','%s');" % (tt,ip,expire_time,url))
                                except Exception as e:
                                    logging.error(e)
                                    continue
                RC.expire(black_ip_minute, 300)
                RC.expire(black_ip_hour,3600)
        MYSQL.Close()
    except Exception as e:
        logging.error(e)
@check.proce_lock
def WAF2():
    DB = 'op'
    tt = time.strftime('%Y%m%d',time.localtime())
    th = time.strftime('%Y%m%d%H', time.localtime())
    tm = datetime.datetime.now() - datetime.timedelta(minutes=2)
    tm = tm.strftime('%Y%m%d%H%M')
    dm = datetime.datetime.now() + datetime.timedelta(hours=1)
    expire_time = dm.strftime('%Y-%m-%d %H:%M:%S')
    black_ip_minute = 'black_ip_%s' % tm
    black_ip_hour = 'black_ip_%s' % th
    black_ip_day = 'black_ip_%s' % tt
    try:
        MYSQL = Mysql.MYSQL(USER, PASSWORD, HOST, PORT, DB)
        IP_LIST = RC.lrange(black_ip_minute,0,-1)
        IP_LIST_HOUR = RC.lrange(black_ip_hour,0,-1)
        if IP_LIST and IP_LIST_HOUR:
            for ip in set(IP_LIST):
                if ip in set(IP_LIST_HOUR):
                    try:
                        #小时拦截
                        RC.lpush(black_ip_day,ip)
                        MYSQL.Run("update haproxy_blacklist set expire = '%s' where ip = '%s';" % (expire_time,ip))
                    except Exception as e:
                        logging.error(e)
                        continue
            RC.expire(black_ip_day,86400)
            MYSQL.Close()
    except Exception as e:
        logging.error(e)
@check.proce_lock
def WAF3():
    DB = 'op'
    tt = time.strftime('%Y%m%d',time.localtime())
    tm = datetime.datetime.now() - datetime.timedelta(minutes=2)
    tm = tm.strftime('%Y%m%d%H%M')
    dm = datetime.datetime.now() + datetime.timedelta(days=1)
    expire_time = dm.strftime('%Y-%m-%d %H:%M:%S')
    black_ip_day = 'black_ip_%s' %tt
    black_ip_minute = 'black_ip_%s' % tm
    try:
        MYSQL = Mysql.MYSQL(USER, PASSWORD, HOST, PORT, DB)
        IP_LIST = RC.lrange(black_ip_minute,0,-1)
        IP_LIST_DAY = RC.lrange(black_ip_day,0,-1)
        if IP_LIST and IP_LIST_DAY:
            for ip in set(IP_LIST):
                if ip in set(IP_LIST_DAY):
                    try:
                        #全天拦截
                        MYSQL.Run("update haproxy_blacklist set expire = '%s' where ip = '%s';" % (expire_time,ip))
                    except Exception as e:
                        logging.error(e)
                        continue
            MYSQL.Close()
    except Exception as e:
        logging.error(e)
@check.proce_lock
def mysql_backup():
    MYSQL = Mysql.MYSQL(USER,PASSWORD,HOST,PORT,DB)
    cmds = "select ip,port from mysqldb where master='是';"
    results = MYSQL.Run(cmds)
    key = 'mysql_backup'
    Redis.delete('finish_backup')
    if results:
        try:
            for host in BACKUP_SERVERS:
                Redis.delete('%s_%s'%(key,host))
            i = len(BACKUP_SERVERS)
            for info in results:
                info = [str(m) for m in info]
                # 设置binlog过期时间
                MHOST,MPORT = info
                MDB = 'mysql'
                MYSQL_SET = Mysql.MYSQL(USER, PASSWORD, MHOST, MPORT, MDB)
                cmds = 'set global expire_logs_days=15;'
                MYSQL_SET.Run(cmds)
                if info[0] not in NOT_BACKUP_MYSQL:
                    i = i-1
                    Redis.lpush('%s_%s'%(key,BACKUP_SERVERS[i]),info)
                    if i == 0:
                        i = len(BACKUP_SERVERS)
            MYSQL_SET.Close()
        except Exception as e:
            loging.write(e)
    MYSQL.Close()
@check.proce_lock
def del_zabbix_events():
    try:
        HOST = '172.16.4.93'
        PORT = 3306
        DB = 'zabbix'
        MYSQL = Mysql.MYSQL(USER,PASSWORD,HOST,PORT,DB)
        cmd = "select eventid from events order by eventid  limit 10000;"
        results = MYSQL.Run(cmd)
        MYSQL.Close()
        def Delete(eventid):
            MySql = Mysql.MYSQL(USER,PASSWORD,HOST,PORT,DB)
            cmd = "delete from events where eventid=%i" % int(eventid[0])
            MySql.Run(cmd)
            MySql.Close()
        pool = ThreadPool(8)
        pool.map(Delete, results)
        pool.close()
        pool.join()
        loging.write('del_last_eventid:%s' %results[-1][0])
    except Exception as e:
        loging.write(e)
@check.proce_lock
def redis_cluster_info():
    try:
        dt = time.strftime('%Y-%m-%d',time.localtime())
        tt = time.strftime('%H:%M:%S',time.localtime())
        ot = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
        RC_JAVA = RedisCluster(startup_nodes=cluster_java_nodes, decode_responses=True)
        results = RC_JAVA.info()
        Redis_Key = 'redis_cluster_java_info'
        for host in results:
            try:
                if results[host]['role'] == 'master':
                    key_commands = '%s_redis_commands' % host
                    key_offset = '%s_redis_offset' % host
                    key_net_input = '%s_redis_net_input' % host
                    key_net_output = '%s_redis_net_output' % host
                    key_keys = '%s_redis_keys' % host
                    Master_Info = {}
                    Master_Info['maxmemory_policy'] = results[host]['maxmemory_policy']
                    Master_Info['used_memory_human'] = results[host]['used_memory_human']
                    Master_Info['slave_host'] = '%s:%s'%(results[host]['slave0']['ip'],results[host]['slave0']['port'])
                    Master_Info['slave_state'] = results[host]['slave0']['state']
                    Master_Info['rejected_connections'] = results[host]['rejected_connections']
                    Master_Info['redis_version'] = results[host]['redis_version']
                    Master_Info['redis_mode'] = results[host]['redis_mode']
                    Master_Info['uptime_in_days'] = results[host]['uptime_in_days']
                    Master_Info['space_keys'] = results[host]['db0']['keys']
                    old_offset = new_offset = int(results[host]['slave0']['offset'])
                    if RC.exists(key_offset):
                        old_offset = int(RC.get(key_offset))
                    RC.set(key_offset,new_offset)
                    Master_Info['slave_offset'] = new_offset - old_offset
                    #连接数
                    connected_clients = results[host]['connected_clients']
                    #增量keys
                    old_keys = new_keys = int(results[host]['db0']['keys'])
                    if RC.exists(key_keys):
                        old_keys = int(RC.get(key_keys))
                    RC.set(key_keys,int(new_keys))
                    add_keys = new_keys - old_keys
                    #命中率
                    HitRate = int(float(results[host]['keyspace_hits']) / (float(results[host]['keyspace_hits']) + float(results[host]['keyspace_misses'])) * 100)
                    # 执行指令
                    old_commands = new_commands = int(results[host]['total_commands_processed'])
                    if RC.exists(key_commands):
                        old_commands = int(RC.get(key_commands))
                    RC.set(key_commands,int(new_commands))
                    commands = (new_commands - old_commands)/60
                    #入口流量
                    old_net_input = new_net_input = int(results[host]['total_net_input_bytes'])
                    if RC.exists(key_net_input):
                        old_net_input = int(RC.get(key_net_input))
                    RC.set(key_net_input,int(new_net_input))
                    net_input = (new_net_input - old_net_input)/1024/1024
                    # 出口流量
                    old_net_output = new_net_output = int(results[host]['total_net_output_bytes'])
                    if RC.exists(key_net_output):
                        old_net_output = int(RC.get(key_net_output))
                    RC.set(key_net_output,int(new_net_output))
                    net_output = (new_net_output - old_net_output)/1024/1024
                    c = db_idc.idc_redis_cluster_info(getdate =dt,gettime =tt,master=host,add_keys=add_keys, connected_clients=connected_clients, HitRate=HitRate,commands=commands,net_input=net_input,net_output=net_output)
                    db_idc.DB.session.add(c)
                    db_idc.DB.session.commit()
                    db = db_idc.idc_redis_cluster_info
                    v = db.query.filter(db.getdate <= ot).all()
                    if v:
                        for c in v:
                            db_idc.DB.session.delete(c)
                            db_idc.DB.session.commit()
                    RC.hset(Redis_Key,host,Master_Info)
            except Exception as e:
                loging.write(e)
                continue
    except Exception as e:
        loging.write(e)
    finally:
        db_idc.DB.session.remove()
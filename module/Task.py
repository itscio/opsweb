#-*- coding: utf-8 -*-
from elasticsearch import Elasticsearch
from elasticsearch import helpers
import oss2
from tcpping import tcpping
import redis
import time
import datetime
import requests
from influxdb import InfluxDBClient
from multiprocessing.dummy import Pool as ThreadPool
from module import loging,db_op,db_idc,SSH,ip_adress,Mysql,tools,Md5
from sqlalchemy import distinct,and_
from collections import defaultdict
from functools import reduce
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/sql.conf')
app.config.from_pyfile('../conf/cas.conf')
app.config.from_pyfile('../conf/es.conf')
app.config.from_pyfile('../conf/oss.conf')
app.config.from_pyfile('../conf/assets.conf')
app.config.from_pyfile('../conf/jump.conf')
logging = loging.Error()
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
RC = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
redis_data = app.config.get('REDIS_DATA')
RC_CLUSTER = redis.StrictRedis(host=redis_data, port=redis_port,decode_responses=True)
es_hosts = app.config.get('ES_HOSTS')
es = Elasticsearch(hosts=es_hosts,timeout=60)
influxdb_host = app.config.get('INFLUXDB_HOST')
influxdb_port = app.config.get('INFLUXDB_PORT')
influxdb_user = app.config.get('INFLUXDB_USER')
influxdb_pw = app.config.get('INFLUXDB_PASSWORD')
influxdb_db = app.config.get('INFLUXDB_DB')
Influx_cli = InfluxDBClient(influxdb_host,influxdb_port,influxdb_user,influxdb_pw,influxdb_db)
PHYSICAL_TYPES = app.config.get('PHYSICAL_TYPES')
dt = time.strftime('%m%d',time.localtime())
oss_id = app.config.get('OSS_ID')
oss_key = app.config.get('OSS_KEY')
oss_url = app.config.get('OSS_URL')
def counts_logs(vals):
    try:
        def share_counts(host_key,uri_key):
            try:
                # 统计域名
                RC.hincrby(host_key, host, 1)
                # 统计uri
                RC.hincrby(uri_key, uri, 1)
            except Exception as e:
                logging.error(e)
        remote_addr,status,host,uri,upstream_addr,response_time,time_t = vals
        tm = ':'.join(time_t.split(':')[:-1])
        tm = '%s_%s'%(time.strftime('%Y-%m-%d',time.localtime()),tm)
        code_key = 'error_logs_status_%s' % tm
        host_key = 'error_logs_domain_%s_%s' % (status, tm)
        uri_key = 'error_logs_domain_%s_%s_%s' % (status, host, tm)
        total_key = 'total_access_%s' % tm
        domain_key = 'domain_counts_%s' % tm
        domain_status_key = 'domain_counts_status_%s' % tm
        counts_status_key = 'counts_%s:%s_%s' % (host, status, tm)
        RC.incr(total_key, 1)
        if int(status) < 400:
            try:
                if int(response_time) >= 1:
                    if int(response_time) >= 1 and int(response_time) <= 3:
                        r_time = '1000-3000'
                    else:
                        r_time = '3000+'
                    host_key = 'response_time_domain_%s_%s' % (r_time, tm)
                    uri_key = 'response_time_domain_%s_%s_%s' % (host, r_time, tm)
                    # 域名下后端tomcat响应时间统计
                    counts_key = 'counts_%s:%s_%s' % (host, r_time, tm)
                    RC.hincrby(domain_key, '%s:%s' % (host, r_time), 1)
                    try:
                        int(upstream_addr.split(':')[-1])
                    except:
                        pass
                    else:
                        if int(upstream_addr.split(':')[-1]) >1024:
                            RC.hincrby(counts_key, upstream_addr, 1)
                    share_counts(host_key, uri_key)
                    RC.expire(counts_key, 86400)
            except Exception as e:
                logging.error(e)

        else:
            try:
                share_counts(host_key, uri_key)
                # 统计错误状态码
                RC.hincrby(code_key, status, 1)
                # 域名下后端tomcat状态码统计
                RC.hincrby(domain_status_key, '%s:%s' % (host, status), 1)
                try:
                    int(upstream_addr.split(':')[-1])
                except:
                    pass
                else:
                    if int(upstream_addr.split(':')[-1]) > 1024:
                        RC.hincrby(counts_status_key, upstream_addr, 1)
                for KEY in (code_key, domain_status_key, counts_status_key):
                    RC.expire(KEY, 86400)
            except Exception as e:
                logging.error(e)
        for KEY in (host_key, uri_key, total_key, domain_key):
            RC.expire(KEY, 86400)
    except Exception as e:
        logging.error(e)

def count_es_logs():
    try:
        dt = time.strftime('%Y-%m-%d',time.localtime())
        now_date = datetime.datetime.now()
        lte_date = now_date.strftime('%Y-%m-%dT%H:%M:%S+08:00')
        gd = now_date - datetime.timedelta(minutes=1)
        tm = gd.strftime('%Y-%m-%d_%H:%M')
        gte_date = gd.strftime('%Y-%m-%dT%H:%M:%S+08:00')
        gd = gd.strftime('%Y-%m-%dT%H:%M:%SZ')
        index = 'logstash-nginx-log-*'
        Key = 'api_domain_lists_%s' % dt
        web_domain_key = 'web_domain_lists_%s' %dt
        domain_list_key = 'domain_lists_%s' %tm
        try:
            # 获取域名
            body = {'size': 0,
                    "query": {"bool": {"must": [{"range": {"time_iso8601": {"gte": gte_date, "lte": lte_date}}}]}},
                    "aggs": {"counts": {"terms": {"field": "host.keyword", "size": 100}}}}
            res = es.search(index=index, body=body)
        except Exception as e:
            logging.error(e)
        # 获取指定域名列表
        hosts = RC_CLUSTER.smembers(Key)
        for val in res['aggregations']['counts']['buckets']:
            host = val['key']
            if host in hosts:
                RC_CLUSTER.sadd(web_domain_key,host)
                RC_CLUSTER.sadd(domain_list_key,host)
        RC_CLUSTER.expire(web_domain_key,864000)
        RC_CLUSTER.expire(domain_list_key,3600)
        for i in range(len(RC_CLUSTER.smembers(domain_list_key))):
            try:
                host = RC_CLUSTER.spop(domain_list_key)
                if host:
                    # 获取指定域名接口列表
                    Key = 'api_uri_lists_%s_%s' % (host, dt)
                    uris = RC_CLUSTER.smembers(Key)
                    # 获取域名下接口
                    try:
                        body = {'size': 0, "query": {"bool": {"must": [{"range": {"time_iso8601": {"gte": gte_date, "lte": lte_date}}},
                                                                       {"match_phrase": {"host": {"query": host}}}]}},
                                "aggs": {"counts": {"terms": {"field": "uri.keyword","size":20}}}}
                        res = es.search(index=index, body=body)
                    except Exception as e:
                        logging.error(e)
                    for val in res['aggregations']['counts']['buckets']:
                        try:
                            uri = val['key']
                            influx_fields = defaultdict()
                            if uri in uris:
                                #域名接口列表
                                RC_CLUSTER.sadd('domain_api_lists_%s_%s' %(host,dt),uri)
                                RC_CLUSTER.expire('domain_api_lists_%s_%s' %(host,dt),864000)
                                #域名接口pv
                                RC_CLUSTER.set('domain_api_pv_%s_%s_%s' %(host,uri,tm),val['doc_count'])
                                RC_CLUSTER.expire('domain_api_pv_%s_%s_%s' % (host, uri, tm), 864000)
                                #域名总pv
                                RC_CLUSTER.incr('domain_api_pv_%s_%s' % (host, tm), int(val['doc_count']))
                                RC_CLUSTER.expire('domain_api_pv_%s_%s' % (host, tm), 864000)
                                #记录到influxdb
                                influx_fields['pv'] = float('%.2f' % float(val['doc_count']))
                                # 获取域名下接口状态码统计
                                upstream = {'status_4xx': (400, 499), 'status_5xx': (500, 599)}
                                for k in upstream:
                                    try:
                                        body = {'size': 0, "query": {"bool": {"must": [{"range": {"time_iso8601": {"gte": gte_date, "lte": lte_date}}},
                                                              {"match_phrase": {"host": {"query": host}}},
                                                              {"match_phrase": {"uri": {"query": uri}}},
                                                              {"range": {"status": {"gte": upstream[k][0], "lte": upstream[k][-1]}}}]}}}
                                        res = es.search(index=index, body=body)
                                    except Exception as e:
                                        logging.error(e)
                                    RC_CLUSTER.hset('domain_api_infos_%s_%s_%s'%(host,uri,tm),k,res['hits']['total'])
                                    #域名维度状态码统计
                                    RC_CLUSTER.hincrby('domain_api_infos_%s_%s' % (host, tm), k,int(float(res['hits']['total'])*100))
                                    # 记录到influxdb
                                    influx_fields[k]= float('%.2f' %float(res['hits']['total']))
                                # 获取域名下接口响应时间
                                upstream = {'resp_100': 0.1, 'resp_200': 0.2, 'resp_500': 0.5, 'resp_1000': 1}
                                for k in upstream:
                                    try:
                                        body = {'size': 0, "query": {
                                            "bool": {
                                                "must": [{"range": {"time_iso8601": {"gte": gte_date, "lte": lte_date}}},
                                                         {"match_phrase": {"host": {"query": host}}},
                                                         {"match_phrase": {"uri": {"query": uri}}},
                                                         {"range": {"upstream_response_time": {"gte": upstream[k]}}}]}, }}
                                        if k == 'resp_100':
                                            body = {'size': 0, "query": {
                                                "bool": {
                                                    "must": [{"range": {"time_iso8601": {"gte": gte_date, "lte": lte_date}}},
                                                             {"match_phrase": {"host": {"query": host}}},
                                                             {"match_phrase": {"uri": {"query": uri}}},
                                                             {"range": {"upstream_response_time": {"gte": upstream[k]}}}]}, },
                                                    "aggs": {
                                                        "avg_resp": {
                                                            "avg": {"field": "upstream_response_time"}
                                                        }
                                                    }}
                                        res = es.search(index=index, body=body)
                                    except Exception as e:
                                        logging.error(e)
                                    # 获取域名接口下平均延时响应时间
                                    if k == 'resp_100':
                                        avg_val = res['aggregations']['avg_resp']['value']
                                        if isinstance(avg_val, float):
                                            RC_CLUSTER.hset('domain_api_infos_%s_%s_%s' % (host, uri, tm), 'avg_resp',float('%.2f' % avg_val))
                                            # 域名维度接口响应时间统计
                                            RC_CLUSTER.hincrby('domain_api_infos_%s_%s' % (host, tm), 'avg_resp',int(float(avg_val)*100))
                                            # 记录到influxdb
                                            influx_fields['avg_resp'] = float('%.2f' % float(avg_val))
                                    #获取接口统计数据
                                    RC_CLUSTER.hset('domain_api_infos_%s_%s_%s'%(host,uri,tm),k,res['hits']['total'])
                                    # 域名维度接口响应时间统计
                                    RC_CLUSTER.hincrby('domain_api_infos_%s_%s' % (host, tm), k,int(float(res['hits']['total'])*100))
                                    # 记录到influxdb
                                    influx_fields[k] = float('%.2f' %float(res['hits']['total']))
                                RC_CLUSTER.expire('domain_api_infos_%s_%s_%s' % (host, uri, tm), 864000)
                                RC_CLUSTER.expire('domain_api_infos_%s_%s' % (host, tm), 864000)
                        except Exception as e:
                            logging.error(e)
                            continue
                        if influx_fields:
                            try:
                                #写入influxdb数据库
                                json_body = [{"measurement": "analysis_logs","tags": {"host":host,"uri":uri},"fields": influx_fields,"time":gd}]
                                Influx_cli.write_points(json_body)
                            except Exception as e:
                                logging.error(e)
            except Exception as e:
                logging.error(e)
                continue
    except Exception as e:
        logging.error(e)

def server_per():
    loging.write('start %s running......' %server_per.__name__)
    db_server = db_idc.idc_servers
    db_zabbix = db_idc.zabbix_info
    host_infos = db_server.query.with_entities(db_server.ip, db_server.ssh_port, db_server.hostname,
                                               db_server.cpu_core).filter(
        and_(db_server.status != '维护中', db_server.comment != '跳过')).all()
    Influx_cli = InfluxDBClient(influxdb_host, influxdb_port, influxdb_user, influxdb_pw, 'zabbix_infos')
    try:
        for host_info in host_infos:
            host,ssh_port,hostname,cpu_core = host_info
            now_date = datetime.datetime.now()
            tm = time.strftime('%Y-%m-%d %H:%M:%S')
            dm = now_date.strftime('%Y-%m-%dT%H:%M:00Z')
            disk_io = 0
            mem_use = 0
            cpu_load = 0
            openfile = 0
            icmpping = 0
            if tcpping(host=host, port=ssh_port, timeout=15):
                try:
                    Ssh = SSH.ssh(ip=host, ssh_port=ssh_port)
                    ssh_values = Ssh.Run('cat /proc/sys/fs/file-nr')
                    if ssh_values['stdout']:
                        openfile = int(ssh_values['stdout'][0].split('\t')[0])
                    ssh_values = Ssh.Run('w')
                    if ssh_values['stdout'] and int(cpu_core)>0:
                        cpu_load = int(int(float(ssh_values['stdout'][0].split(',')[-2]))/int(cpu_core)*100)
                    ssh_values = Ssh.Run('free -g')
                    if ssh_values['stdout']:
                        mem_use = int(float(ssh_values['stdout'][1].split()[2])/float(ssh_values['stdout'][1].split()[1])*100)
                    ssh_values = Ssh.Run('iostat -c')
                    if ssh_values['stdout']:
                        disk_io = float(ssh_values['stdout'][3].split()[3])
                    Ssh.Close()
                except:
                    continue
                else:
                    icmpping = 1
            try:
                # 写入数据库
                val = db_zabbix.query.filter(
                    and_(db_zabbix.ip == host, db_zabbix.ssh_port == ssh_port, db_zabbix.hostname == hostname)).all()
                if val:
                    db_zabbix.query.filter(and_(db_zabbix.ip == host, db_zabbix.ssh_port == ssh_port,
                                                db_zabbix.hostname == hostname)).update(
                        {db_zabbix.icmpping: icmpping, db_zabbix.cpu_load: cpu_load,
                         db_zabbix.mem_use: mem_use, db_zabbix.disk_io: disk_io, db_zabbix.openfile: openfile,
                         db_zabbix.update_time: tm})
                    db_idc.DB.session.commit()
                else:
                    v = db_zabbix(ip=host, ssh_port=ssh_port, hostname=hostname, icmpping=icmpping, cpu_load=cpu_load,
                                  mem_use=mem_use, disk_io=disk_io, openfile=openfile, update_time=tm)
                    db_idc.DB.session.add(v)
                    db_idc.DB.session.commit()
                # 写入influxdb数据库
                json_body = [
                    {"measurement": "server_infos", "tags": {"ip": host, "ssh_port": ssh_port, "hostname": hostname},
                     "fields": {'cpu_load': cpu_load, 'mem_use': mem_use, 'openfile': openfile}, "time": dm}]
                Influx_cli.write_points(json_body)
                #修改服务器状态
                if icmpping == 1:
                    db_server.query.filter(and_(db_server.status=='疑似下架',db_server.hostname==hostname)).update({db_server.status:'使用中'})
                    db_idc.DB.session.commit()
                else:
                    db_server.query.filter(db_server.hostname==hostname).update({db_server.status:'疑似下架'})
                    db_idc.DB.session.commit()
            except Exception as e:
                logging.error(e)
    except Exception as e:
        logging.error(e)
    finally:
        db_idc.DB.session.remove()

@tools.proce_lock()
def get_server_info():
    db_store = db_idc.idc_store
    db_server = db_idc.idc_servers
    db_idc_id = db_idc.idc_id
    server_val = db_server.query.with_entities(db_server.ip,db_server.ssh_port).filter(and_(db_server.status !='维护中',db_server.comment !='跳过')).all()
    #获取阿里云存储情况
    auth = oss2.Auth(oss_id, oss_key)
    service = oss2.Service(auth, 'http://oss.aliyuncs.com')
    Buckets = [b.name for b in oss2.BucketIterator(service)]
    #获取idc id
    idc_id = db_idc_id.query.with_entities(db_idc_id.id).filter(and_(db_idc_id.aid=='阿里云',db_idc_id.cid=='OSS')).all()
    if idc_id:
        store_val = db_store.query.with_entities(db_store.type).filter(db_store.idc_id == idc_id[0][0]).all()
        if store_val:
            store_val = [val[0] for val in store_val]
        # bucket信息写入数据库
        add_vals = set(Buckets) - set(store_val)
        if add_vals:
            for bucket_name in add_vals:
                bucket = oss2.Bucket(auth, 'http://oss.aliyuncs.com', bucket_name)
                bucket_info = bucket.get_bucket_info()
                c = db_store(idc_id=idc_id[0][0],type=bucket_name,ip='http://oss.aliyuncs.com',purch_date=bucket_info.creation_date.split('T')[0],expird_date='',status='使用中',comment='')
                db_idc.DB.session.add(c)
                db_idc.DB.session.commit()
        # 删除数据库中bucket信息
        del_vals = set(store_val)-set(Buckets)
        if del_vals:
            for bucket_name in del_vals:
                c = db_store.query.filter(db_store.type==bucket_name).all()
                for v in c:
                    db_idc.DB.session.delete(v)
                    db_idc.DB.session.commit()
    def get_info(info):
        sip,port= info
        sip = sip.strip()
        if tcpping(host=sip, port=port, timeout=3):
            try:
                Ssh = SSH.ssh(ip=sip, ssh_port=port)
                Ssh.Run('yum -y install dmidecode unzip zip md5sum')
                Ssh.Close()
            except:
                pass
            else:
                try:
                    Ssh = SSH.ssh(ip=sip, ssh_port=port)
                    # 获取系统磁盘容量
                    try:
                        disk_size = ''
                        disks = []
                        values = Ssh.Run("cat /proc/partitions")
                        for line in values['stdout']:
                            line = line.strip('\n')
                            if 'sd' in line or 'vd' in line or 'xvd' in line:
                                try:
                                    if int(line[-1]) >= 0 and 'xvd' not in line:
                                        continue
                                except:
                                    disks.append(int(round(float(line.split()[-2]) / 1000 / 1000)))
                                if 'xvd' in line:
                                    try:
                                        if int(line[-1]) >= 0:
                                            disks.append(int(round(float(line.split()[-2]) / 1000 / 1000)))
                                    except:
                                        continue
                        disk_count = len(disks)
                        if disks:
                            disk_size = '%sG' % disks[0]
                            if disk_count > 1:
                                disk_size = '%sG' % reduce(lambda x, y: x + y, disks)
                    except Exception as e:
                        logging.error(e)

                    # 获取IP信息
                    try:
                        ips = ''
                        IPS = []
                        cmd = "ip a|grep 'inet '"
                        values = Ssh.Run(cmd)
                        for line in values['stdout']:
                            IPS.append(line.strip('\n').split()[1].split('/')[0])
                        if '127.0.0.1' in IPS:
                            IPS.remove('127.0.0.1')
                        if sip in IPS:
                            IPS.remove(sip)
                        if IPS:
                            if len(IPS) == 1:
                                ips = '%s;'%IPS[0]
                            else:
                                ips ='%s;'%';'.join(IPS[:4])
                    except Exception as e:
                        logging.error(e)

                    #获取内存信息
                    try:
                        mem_size = ''
                        cmd = "free -m"
                        values = Ssh.Run(cmd)
                        for line in values['stdout']:
                            if 'Mem:' in line.strip('\n'):
                                mem_size ='{0}G'.format(int(round(float(line.split()[1])/1000)))
                                break
                    except Exception as e:
                        logging.error(e)

                    # 获取CPU信息
                    try:
                        datas = []
                        for cmd in ("cat /proc/cpuinfo|grep 'model name'|sed -n '1p' ", "cat /proc/cpuinfo|grep 'processor'|wc -l"):
                            values = Ssh.Run(cmd)
                            if values['stdout']:
                                values = values['stdout'][0].strip('\n')
                                if ':' in values:
                                    values = values.split(':')[-1].strip()
                                datas.append(values)
                            else:
                                datas.append('')
                        db_server.query.filter(and_(db_server.ip==sip,db_server.ssh_port==port)).update({db_server.s_ip:ips,db_server.cpu_info:datas[0],db_server.cpu_core:datas[1],
                                                                                                         db_server.mem:mem_size,db_server.disk_count:disk_count,db_server.disk_size:disk_size})
                        db_idc.DB.session.commit()
                    except Exception as e:
                        logging.error(e)

                    # 获取系统信息
                    try:
                        system = ''
                        values = Ssh.Run("cat /etc/redhat-release")
                        if values['stdout']:
                            system = values['stdout'][0].strip()
                        db_server.query.filter(and_(db_server.ip==sip,db_server.ssh_port==port)).update({db_server.system:system})
                        db_idc.DB.session.commit()
                    except Exception as e:
                        logging.error(e)

                    # 获取厂家信息
                    try:
                        infos = []
                        for cmd in ('/usr/sbin/dmidecode -s system-serial-number', '/usr/sbin/dmidecode -s system-product-name', '/usr/sbin/dmidecode -s system-manufacturer'):
                            values = Ssh.Run(cmd)
                            if values['stdout']:
                                infos.append(values['stdout'][0].strip('\n'))
                            else:
                                infos.append('Not Specified')
                        if infos[-1] in PHYSICAL_TYPES:
                            infos.append('physical')
                        else:
                            infos.append('vm')
                        db_server.query.filter(and_(db_server.ip==sip,db_server.ssh_port==port)).update({db_server.sn:infos[0],db_server.productname:infos[1],
                                                                                                         db_server.manufacturer:infos[2],db_server.host_type:infos[3]})
                        db_idc.DB.session.commit()
                    except Exception as e:
                        logging.error(e)
                except Exception as e:
                    logging.error(e)
                finally:
                    Ssh.Close()
    try:
        loging.write("start get server infos ......")
        if server_val:
            pool = ThreadPool(5)
            pool.map(get_info,server_val)
            pool.close()
            pool.join()
    except Exception as e:
        logging.error(e)
    finally:
        loging.write("get server infos complete!")
        db_idc.DB.session.remove()

@tools.proce_lock()
def auto_discovery():
    try:
        loging.write("start %s ......" % auto_discovery.__name__)
        db_ips = db_idc.resource_ip
        db_idc_id = db_idc.idc_id
        db_third = db_idc.third_resource
        db_project = db_op.project_list
        db_zabbix = db_idc.zabbix_info
        db_server = db_idc.idc_servers
        aids = db_ips.query.with_entities(db_ips.aid,db_ips.network).all()
        aids = {aid[-1]:aid[0] for aid in aids}
        exist_infos = db_server.query.with_entities(db_server.hostname,db_server.ip,db_server.ssh_port).all()
        exist_hostname = set([info[0] for info in exist_infos])
        exist_hosts = ["%s:%s"%(info[1],info[2]) for info in exist_infos]
        hosts_list = tools.get_server_list()
        dt = time.strftime('%Y-%m-%d', time.localtime())
        def discovery(info):
            ip, ssh_port, hostname,idc = info
            aid = aids[idc]
            if hostname not in exist_hostname:
                if "%s:%s" %(ip,ssh_port) in exist_hosts:
                    db_server.query.filter(and_(db_server.ip == ip,db_server.ssh_port == ssh_port)).update({db_server.hostname:hostname})
                    db_idc.DB.session.commit()
                else:
                    if tcpping(host=ip, port=ssh_port, timeout=15):
                        try:
                            Ssh = SSH.ssh(ip=ip, ssh_port=ssh_port)
                        except:
                            pass
                        else:
                            val = None
                            Ssh.Run("yum -y install dmidecode iproute")
                            sn_val = Ssh.Run('/usr/sbin/dmidecode -s system-serial-number')
                            if sn_val['stdout']:
                                if 'Specified' not in sn_val['stdout']:
                                    sn = sn_val['stdout']
                                    val = db_server.query.with_entities(db_server.ip,db_server.ssh_port).filter(db_server.sn==sn).all()
                                    if val:
                                        sip,ssh_port = val[0]
                                        #修改资产表
                                        db_server.query.filter(db_server.sn==sn).update({db_server.ip:ip})
                                        db_idc.DB.session.commit()
                                        #修改第三方资源表
                                        db_third.query.filter(and_(db_third.ip == sip,db_third.ssh_port == ssh_port)).update({db_third.ip:ip})
                                        db_idc.DB.session.commit()
                                        #修改自有服务资源表
                                        db_project.query.filter(and_(db_project.ip == sip,db_project.ssh_port == ssh_port)).update({db_project.ip:ip})
                                        db_op.DB.session.commit()
                                        #修改zabbix信息表
                                        db_zabbix.query.filter(and_(db_zabbix.ip == sip,db_zabbix.ssh_port == ssh_port)).update({db_zabbix.ip:ip})
                                        db_idc.DB.session.commit()
                            if not val:
                                dmi_val = Ssh.Run("/usr/sbin/dmidecode -s system-manufacturer")
                                Ssh.Close()
                                if dmi_val['stdout']:
                                    if dmi_val['stdout'][0].strip('\n') in PHYSICAL_TYPES:
                                        idc = db_idc_id.query.with_entities(db_idc_id.id).filter(and_(db_idc_id.aid == aid, db_idc_id.cid != 'KVM',db_idc_id.cid !='')).all()
                                        if not idc:
                                            idc = db_idc_id.query.with_entities(db_idc_id.id).filter(and_(db_idc_id.aid == aid, db_idc_id.cid == '')).all()
                                        idc_id = int(idc[0][0])
                                        v = db_server(idc_id=idc_id,ip=ip, ssh_port=ssh_port, s_ip='', host_type='physical', hostname=hostname, sn='',
                                                      manufacturer='', productname='',
                                                      system='', cpu_info='', cpu_core=0, mem='',disk_count=0, disk_size='', idrac='',
                                                      purch_date=dt,
                                                      expird_date='', status='使用中', comment='')
                                        db_idc.DB.session.add(v)
                                        db_idc.DB.session.commit()
                                    else:
                                        #判断机房机柜信息
                                        idc_id = db_idc_id.query.with_entities(db_idc_id.id).filter(and_(db_idc_id.aid==aid,db_idc_id.cid == 'KVM')).all()
                                        if not idc_id:
                                            c = db_idc_id(aid=aid,cid='KVM')
                                            db_idc.DB.session.add(c)
                                            db_idc.DB.session.commit()
                                        idc_id = db_idc_id.query.with_entities(db_idc_id.id).filter(and_(db_idc_id.aid == aid, db_idc_id.cid == 'KVM')).all()
                                        idc_id = int(idc_id[0][0])
                                        v = db_server(idc_id=idc_id,ip=ip,ssh_port=ssh_port,s_ip='',host_type='vm',hostname=hostname,sn='',manufacturer='',productname='',
                                                      system='',cpu_info='',cpu_core=0,mem='',disk_count=0,disk_size='',idrac='',purch_date=dt,expird_date='2999-12-12',status='使用中',comment='')
                                        db_idc.DB.session.add(v)
                                        db_idc.DB.session.commit()
                                    for cmd in ("yum -y install dmidecode","chmod +s /usr/sbin/dmidecode"):
                                        Ssh.Run(cmd)
                                    loging.write("auto discovery new server %s %s" %(ip,hostname))
        if hosts_list:
            pool = ThreadPool(10)
            pool.map(discovery,hosts_list)
            pool.close()
            pool.join()
    except Exception as e:
        logging.error(e)
    finally:
        loging.write("%s complete" %auto_discovery.__name__)
        db_idc.DB.session.remove()
        db_op.DB.session.remove()

@tools.proce_lock()
def get_app_service():
    def app_service(info):
        apps = defaultdict()
        app_ports = []
        ip, ssh_port = info
        # 判断ssh端口是否可连通
        if tcpping(host=ip, port=ssh_port, timeout=5):
            #获取应用监听端口
            try:
                Ssh = SSH.ssh(ip=ip, ssh_port=ssh_port)
            except:
                pass
            else:
                try:
                    pf = Ssh.Run("ss -l -t -4 -n -p")['stdout']
                    for line in pf:
                        if '*:*' in line:
                            line = line.strip().split()
                            try:
                                app = line[-1].split('"')[1]
                                pid = line[-1].split('"')[2].split(',')[1].split('=')[-1]
                                app_port = line[3].split(':')[-1]
                            except:
                                continue
                            if app and pid and app_port:
                                try:
                                    app_port = int(app_port)
                                except:
                                    continue
                                else:
                                    apps['%s:%s:%s' %(app,pid,app_port)] = app_port
                    # 单独获取lvs,keepalived
                    out_vals = Ssh.Run("ipvsadm -ln|wc -l")
                    if out_vals['stdout']:
                        if int(out_vals['stdout'][0]) > 3:
                            app_ports.append('lvs:0')
                    out_vals = Ssh.Run("ps -ef|grep keepalived|grep -v grep")
                    if out_vals['stdout']:
                        for line in out_vals['stdout']:
                            if 'keepalived' in line:
                                app_ports.append('keepalived:0')
                except:
                    pass
                else:
                    if apps:
                        #删除已下架自有服务
                        vals = db_project.query.with_entities(db_project.app_port).filter(and_(db_project.ip == ip, db_project.ssh_port == ssh_port,db_project.resource.in_(('tomcat',)))).all()
                        if vals:
                            ports = set([int(apps[app]) for app in apps])
                            for val in vals:
                                if int(val[0]) not in ports:
                                    v = db_project.query.filter(and_(db_project.ip == ip, db_project.ssh_port == ssh_port,db_project.app_port==int(val[0]))).all()
                                    for c in v:
                                        db_op.DB.session.delete(c)
                                        db_op.DB.session.commit()
                                    loging.write('delete self service %s %s' % (ip,val[0]))
                        #清洗应用服务数据
                        for info in apps:
                            try:
                                app = info.split(':')[0]
                                app_port = int(apps[info])
                                #java单独处理
                                if app =='java':
                                    #判断是不是自有资源服务
                                    val = db_project.query.filter(and_(db_project.ip == ip, db_project.ssh_port == ssh_port,db_project.app_port == app_port)).all()
                                    if not val:
                                        out_vals = Ssh.Run("ps -ef|grep java|grep -v grep")
                                        for line in out_vals['stdout']:
                                            for java_app in cluster_apps:
                                                if java_app in line:
                                                    if java_app == 'KFK':
                                                        java_app = 'kafka'
                                                    if java_app == 'ZK':
                                                        java_app = 'zookeeper'
                                                    app_ports.append('%s:0'%java_app)
                                        if app_port in RPCS.keys():
                                            app_ports.append('%s:%s' %(RPCS[app_port],app_port))
                                        #发现新的自有服务资源写入数据库
                                        val = db_project.query.with_entities(db_project.resource,db_project.project,db_project.domain,db_project.business_id).filter(db_project.app_port == app_port).first()
                                        if val:
                                            resource, project, domain, business_id = val
                                            loging.write('find new self service %s %s %s' %(ip,app_port,project))
                                            c = db_project(resource=resource,project=project,domain=domain,ip=ip,ssh_port=ssh_port,app_port=app_port,business_id=business_id,sys_args='java',env='生产',gray='',status='使用中',update_date=time.strftime('%Y-%m-%d',time.localtime()))
                                            db_op.DB.session.add(c)
                                            db_op.DB.session.commit()

                                else:
                                    if '-' in app:
                                        app = app.split('-')[0]
                                    if 'haprox' in app:
                                        app = 'haproxy'
                                    if 'kube' in app:
                                        app = 'Kubernetes'
                                    if 'memcache' in app:
                                        app = 'memcached'
                                    if 'rain_rate' in app:
                                        app = 'rain_rate'
                                    if 'Accuweather' in app:
                                        app = 'Accuweather'
                                    app = app.replace('(', '')
                                    #判断是否在统计应用列表里
                                    if app in in_apps:
                                        if app in cluster_apps:
                                            app_port = 0
                                        if 'nginx' in app:
                                            app_port = 80
                                        app_ports.append("%s:%s" %(app,app_port))
                                    else:
                                        RC_CLUSTER.sadd('op_exclude_apps',"%s:%s" %(app,app_port))
                            except Exception as e:
                                logging.error(e)
                        #写入第三方应用资源表
                        if app_ports:
                            application = db_third.query.with_entities(db_third.resource_type,db_third.app_port).filter(and_(db_third.ip == ip, db_third.ssh_port == ssh_port)).all()
                            application = ['%s:%s' % (val[0], val[1]) for val in application]
                            try:
                                # 删除第三方应用服务列表,不删除手工录入信息
                                for val in set(application):
                                    if val not in set(app_ports):
                                        if ':' in val:
                                            app,app_port = val.split(':')
                                            infos = db_third.query.with_entities(db_third.id,db_third.update_date).filter(and_(db_third.ip == ip,db_third.resource_type==app,db_third.app_port==int(app_port))).all()
                                            if infos:
                                                if '0000-00-00' not in infos[0]:
                                                    third_id = infos[0][0]
                                                    # 清除项目资源表
                                                    c = db_project_third.query.filter(db_project_third.third_id == int(third_id)).all()
                                                    if c:
                                                        for v in c:
                                                            db_op.DB.session.delete(v)
                                                            db_op.DB.session.commit()
                                                    #清除第三方资源表
                                                    c = db_third.query.filter(db_third.id == int(third_id)).all()
                                                    if c:
                                                        for v in c:
                                                            db_idc.DB.session.delete(v)
                                                            db_idc.DB.session.commit()
                                                    loging.write('del app service %s %s %s ' % (ip, app, app_port))
                            except Exception as e:
                                logging.error(e)
                            try:
                                #新增第三方资源信息
                                for val in set(app_ports):
                                    if val not in set(application):
                                        if ':' in val:
                                            app, app_port = val.split(':')
                                            RC.sadd('third_app_counts', app)
                                            cluster_type = '非集群'
                                            if app in cluster_apps:
                                                cluster_type = '集群模式'
                                            if app == 'hadoop':
                                                v = db_third(resource_type=app, cluster_type=cluster_type, ip=ip,
                                                         ssh_port=ssh_port, app_port=int(app_port),busi_id=0, department='',
                                                         person='', contact='', status='使用中',update_date=time.strftime('%Y-%m-%d',time.localtime()))
                                            else:
                                                v = db_third(resource_type=app, cluster_type=cluster_type, ip=ip,
                                                         ssh_port=ssh_port, app_port=int(app_port), department='TPD',busi_id=0,
                                                         person='', contact='', status='使用中',update_date=time.strftime('%Y-%m-%d',time.localtime()))
                                            db_idc.DB.session.add(v)
                                            db_idc.DB.session.commit()
                                            loging.write('add new app service %s %s %s' % (app, ip, app_port))
                                            # 新发现数据库写入mysql信息表
                                            if app == 'mysqld':
                                                db_v = db_mysqld(ip=ip, port=int(app_port), db='', master='否',slave='否',
                                                                 Master_Host='',Master_Port='',Master_User='')
                                                db_idc.DB.session.add(db_v)
                                                db_idc.DB.session.commit()
                            except Exception as e:
                                logging.error(e)
                finally:
                    Ssh.Close()
    try:
        loging.write("start run %s ......" %get_app_service.__name__)
        db_server = db_idc.idc_servers
        db_third = db_idc.third_resource
        db_project = db_op.project_list
        db_project_third = db_op.project_third
        db_mysqld = db_idc.idc_mysqldb
        RPCS = {9003:'weather-rpc', 9103:'location-rpc',9012:'sns-rpc',8647:'siriasis-rpc',8646:'sharebg-rpc',8648:'running-rpc',8649:'allergy-rpc'}
        cluster_apps = ('KFK', 'hadoop', 'cachecloud', 'elasticsearch', 'ZK', 'kafka', 'zookeeper','codis','Kubernetes','mongod','haproxy','lvs','keepalived','docker')
        in_apps = ['redis','nginx','mysqld','zookeeper','hadoop','elasticsearch','kafka','Kubernetes','codis','mongod','haproxy','docker','keepalived','rain_rate','searchd',
                   'cachecloud','java','lvs','memcached','Accuweather','influxd','etcd']
        in_apps.extend(RPCS.values())
        infos = db_server.query.with_entities(db_server.ip,db_server.ssh_port).filter(and_(db_server.status !='维护中',db_server.comment != '跳过')).all()
        if infos:
            pool = ThreadPool(10)
            pool.map(app_service,infos)
            pool.close()
            pool.join()
    except Exception as e:
        logging.error(e)
    finally:
        loging.write("%s complete!"  %get_app_service.__name__)
        db_idc.DB.session.remove()
        db_op.DB.session.remove()

@tools.proce_lock()
def get_project_app():
    def get_third_app(app_list):
        try:
            project_id, project, ip, ssh_port, app_port = app_list
            access_resource = []
            Ssh = SSH.ssh(ip=ip, ssh_port=ssh_port)
            Ssh.Run("yum -y install iproute")
            #获取应用活动连接
            values = Ssh.Run("ss -l -t -4 -n -p|grep {0}".format(app_port))
            try:
                if values['stdout']:
                    app_pid = values['stdout'][0].strip().split()[-1].split(',')[1]
                    if app_pid:
                        values = Ssh.Run("lsof -i -n -P|grep EST|grep {0}".format(app_pid))
                        if values['stdout']:
                            for line in values['stdout']:
                                if '->' in line:
                                    line = line.split()[8]
                                    if '->' in line:
                                        access_resource.append(line.split('->')[-1])
            except Exception as e:
                logging.error(e)
            Ssh.Close()
        except:
            pass
        else:
            if access_resource:
                for info in set(access_resource):
                    try:
                        idc_ids = []
                        third_ip, third_port = info.split(':')
                        if '127.0.0.1' in third_ip:
                            third_ip = ip
                        # 获取机房机柜ID
                        vals = db_servers.query.with_entities(db_servers.idc_id).filter(and_(db_servers.ip==ip,db_servers.ssh_port==ssh_port)).all()
                        if vals:
                            idc_id = vals[0][0]
                            # 获取机房信息
                            vals = db_idc_id.query.with_entities(db_idc_id.aid).filter(db_idc_id.id==idc_id).all()
                            if vals:
                                aid = vals[0][0]
                                # 获取机房下所有机柜ID
                                vals = db_idc_id.query.with_entities(db_idc_id.id).filter(db_idc_id.aid==aid).all()
                                if vals:
                                    idc_ids = [val[0] for val in vals]
                        # 获取web服务器机房机柜信息
                        vals = db_servers.query.with_entities(db_servers.ip,db_servers.ssh_port).filter(and_(db_servers.ip==third_ip,db_servers.idc_id.in_(tuple(idc_ids)))).all()
                        if vals:
                            third_ip, third_ssh_port = vals[0]
                        else:
                            vals = db_servers.query.with_entities(db_servers.ip, db_servers.ssh_port).filter(and_(db_servers.s_ip.like('%s{0};%'.format(third_ip)), db_servers.idc_id.in_(tuple(idc_ids)))).all()
                            if vals:
                                third_ip, third_ssh_port = vals[0]
                            else:
                                third_ip = third_ssh_port = None
                        # 获取远程资源应用名称
                        if third_ip and third_ssh_port:
                            third_id = None
                            # 查找应用服务ID
                            vals = db_third.query.with_entities(db_third.id).filter(and_(db_third.ip==third_ip,db_third.ssh_port==third_ssh_port,db_third.app_port==third_port)).all()
                            if vals:
                                third_id = vals[0][0]
                            else:
                                vals = db_third.query.with_entities(db_third.id).filter(and_(db_third.ip == third_ip, db_third.ssh_port == third_ssh_port,db_third.app_port=='')).all()
                                if vals:
                                    if len(vals[0]) == 1:
                                        third_id = vals[0][0]
                            if third_id:
                                vals = db_project_third.query.filter(and_(db_project_third.project == project,db_project_third.project_id == project_id,db_project_third.third_id == third_id)).all()
                                if not vals:
                                    v = db_project_third(project=project, project_id=project_id,third_id=third_id)
                                    db_op.DB.session.add(v)
                                    db_op.DB.session.commit()
                                    loging.write('add project app_service %s  %s  %s' % (project, project_id, third_id))
                    except Exception as e:
                        logging.error(e)
    try:
        db_servers = db_idc.idc_servers
        db_third = db_idc.third_resource
        db_idc_id = db_idc.idc_id
        db_project_third = db_op.project_third
        db_project = db_op.project_list
        app_lists = db_project.query.with_entities(db_project.id,db_project.project,db_project.ip,db_project.ssh_port,db_project.app_port).filter(db_project.resource.in_(('tomcat',))).all()
        if app_lists:
            pool = ThreadPool(10)
            pool.map(get_third_app,app_lists)
            pool.close()
            pool.join()
    except Exception as e:
        logging.error(e)
    finally:
        db_op.DB.session.remove()
        db_idc.DB.session.remove()

@tools.proce_lock()
def es_get_log_status():
    lte_date = datetime.datetime.now()
    gte_date = lte_date - datetime.timedelta(minutes=1)
    lte_date = lte_date.strftime('%Y-%m-%dT%H:%M:%S+08:00')
    gte_date = gte_date.strftime('%Y-%m-%dT%H:%M:%S+08:00')
    try:
        #获取es当前1分钟的数据
        res = helpers.scan(es, index='logstash-nginx-log-*', query={"query": {
            "bool": {
                "must": [{"range": {"time_iso8601": {"gte": gte_date, "lte": lte_date}}}],
                "must_not": [{"terms": {"status": [200, 301, 302, 304]}}]}}})
        for info in res:
            try:
                if info['_source']:
                    info = info['_source']
                    if 'time_iso8601' in info:
                        try:
                            time_d, time_t = tools.time_format(info['time_iso8601'])
                        except Exception as e:
                            logging.error(e)
                        else:
                            if 'upstream_addr' in info:
                                vals = [info[k] for k in ('remote_addr','status','host','uri','upstream_addr','upstream_response_time') if k in info]
                                vals.append(time_t)
                                counts_logs(vals)
            except Exception as e:
                logging.error(e)
                continue
    except Exception as e:
        logging.error(e)

@tools.proce_lock()
def es_get_log_time():
    lte_date = datetime.datetime.now()
    gte_date = lte_date - datetime.timedelta(minutes=1)
    lte_date = lte_date.strftime('%Y-%m-%dT%H:%M:%S+08:00')
    gte_date = gte_date.strftime('%Y-%m-%dT%H:%M:%S+08:00')
    try:
        #响应时间大于1秒的日志
        res = helpers.scan(es, index='logstash-nginx-log-*', query={"query": {"bool": {"must": [{"range": {"time_iso8601": {"gte": gte_date, "lte": lte_date}}},
                            {"terms": {"status": [200, 301, 302, 304]}},{"range": {"upstream_response_time": {"gte": 1}}}]},}})
        for info in res:
            try:
                if info['_source']:
                    info = info['_source']
                    if 'time_iso8601' in info:
                        try:
                            time_d, time_t = tools.time_format(info['time_iso8601'])
                        except Exception as e:
                            logging.error(e)
                        else:
                            if 'upstream_addr' in info:
                                vals = [info[k] for k in ('remote_addr','status','host','uri','upstream_addr','upstream_response_time')]
                                vals.append(time_t)
                                counts_logs(vals)
            except Exception as e:
                logging.error(e)
                continue
    except Exception as e:
        logging.error(e)

@tools.proce_lock()
def cron_run_task():
    loging.write("start run %s ......" %cron_run_task.__name__)
    MY_SQL = Mysql.MYSQL(db='mysql')
    try:
        # 清理资产资源表残留信息
        cmds = ("delete FROM op.project_third where project not in (select DISTINCT(project)from op.project_list);",
                "delete FROM op.project_other where server_id not in (select id from idc.servers);",
                "delete FROM op.project_third where third_id not in (select id from idc.third_resource);",
                "delete FROM idc.crontabs where server_id not in (select id from idc.servers);",
                "delete FROM idc.hosts where server_id not in (select id from idc.servers);",
                "delete FROM op.business where id not in (select business_id from op.project_list);"
                )
        for cmd in cmds:
            MY_SQL.Run(cmd)
        cmd = "select ip,ssh_port from idc.third_resource;"
        values = MY_SQL.Run(cmd)
        for vals in values:
            ip,ssh_port = vals
            cmd = "select id from idc.servers where ip='%s' and ssh_port=%i" %(ip,ssh_port)
            if not MY_SQL.Run(cmd):
                cmd = "delete from idc.third_resource where ip='%s' and ssh_port=%i" %(ip,ssh_port)
                MY_SQL.Run(cmd)
        cmd = "select ip,ssh_port from op.project_list;"
        values = MY_SQL.Run(cmd)
        for vals in values:
            ip, ssh_port = vals
            cmd = "select id from idc.servers where ip='%s' and ssh_port=%i" % (ip, ssh_port)
            if not MY_SQL.Run(cmd):
                cmd = "delete from op.project_list where ip='%s' and ssh_port=%i" % (ip, ssh_port)
                MY_SQL.Run(cmd)
        #清理redis信息表
        db_third = db_idc.third_resource
        db_servers = db_idc.idc_servers
        db_redis = db_idc.redis_info
        vals = db_third.query.with_entities(distinct(db_third.ip)).filter(db_third.resource_type=='redis').all()
        vals = tuple([val[0] for val in vals])
        ids = db_servers.query.with_entities(db_servers.id).filter(db_servers.ip.in_(vals)).all()
        ids = tuple([int(id[0]) for id in ids])
        v = db_redis.query.filter(~ db_redis.server_id.in_(ids)).all()
        for c in v:
            db_idc.DB.session.delete(c)
            db_idc.DB.session.commit()
    except Exception as e:
        logging.error(e)
    finally:
        loging.write("complete %s !" % cron_run_task.__name__)
        MY_SQL.Close()
        db_idc.DB.session.remove()

@tools.proce_lock()
def get_project_lists():
    try:
        loging.write("start %s ......" %get_project_lists.__name__)
        db_project = db_op.project_list
        db_business = db_op.business
        dt = time.strftime('%Y-%m-%d', time.localtime())
        lte_date = datetime.datetime.now()
        gte_date = lte_date - datetime.timedelta(minutes=60)
        lte_date = lte_date.strftime('%Y-%m-%dT%H:%M:%S+08:00')
        gte_date = gte_date.strftime('%Y-%m-%dT%H:%M:%S+08:00')
        try:
            # 动态更新项目域名接口列表
            res = helpers.scan(es, index='logstash-nginx-log-*', query={
                "query": {"bool": {"must": [{"range": {"time_iso8601": {"gte": gte_date, "lte": lte_date}}},
                                            {"terms": {"status": [200, 301, 302, 304]}},
                                            {"range": {"upstream_response_time": {"gte": 1}}}]}, }})
            for info in res:
                try:
                    if info['_source']:
                        info = info['_source']
                        if 'upstream_addr' in info:
                            app_port = int(info['upstream_addr'].split(':')[-1])
                            if app_port >1024:
                                domain = info['host']
                                # 更新项目对应域名列表
                                RC_CLUSTER.sadd('get_api_projects_%s' % dt,app_port)
                                RC_CLUSTER.expire('get_api_projects_%s' % dt,300)
                                RC_CLUSTER.sadd("get_api_%s_%s" % (app_port, dt),domain)
                                RC_CLUSTER.expire("get_api_%s_%s" % (app_port, dt),300)
                except Exception as e:
                    logging.error(e)
                    continue
            for app_port in RC_CLUSTER.smembers('get_api_projects_%s' % dt):
                try:
                    domains = RC_CLUSTER.smembers("get_api_%s_%s" % (app_port, dt))
                    if domains:
                        val = db_project.query.with_entities(distinct(db_project.domain)).filter(db_project.app_port == int(app_port)).all()
                        if val:
                            old_domain = val[0][0].split(',')[:-1]
                            old_domain.extend(domains)
                            old_domain = set(old_domain)
                            db_project.query.filter(db_project.app_port == int(app_port)).update({db_project.domain: '%s,' % ','.join(old_domain)})
                            db_op.DB.session.commit()
                        else:
                            domains = '%s,' % ','.join(domains)
                            project = '_'.join(domains.split(',')[0].split('.')[:-2])
                            val = db_business.query.filter(db_business.business==project).all()
                            if not val:
                                c = db_business(business=project,describe=project,person='',contact='')
                                db_op.DB.session.add(c)
                                db_op.DB.session.commit()
                            business_id = db_business.query.with_entities(db_business.id).filter(db_business.business==project).all()
                            c = db_project(resource='tomcat',project=project,domain=domains,ip='',ssh_port=20443,app_port=app_port,
                                           business_id = business_id[0][0],sys_args='java',env='生产',gray=0,status='使用中',update_date=dt)
                            db_op.DB.session.add(c)
                            db_op.DB.session.commit()
                            loging.write("find new project %s %s ......" %(project,app_port))
                except Exception as e:
                    logging.error(e)
                    continue
        except Exception as e:
            logging.error(e)
        # 业务大数据域名接口列表
        f = requests.get(app.config.get('BUSIURL'))
        for info in f.json():
            try:
                Key = 'api_domain_lists_%s' % dt
                RC_CLUSTER.sadd(Key,info['domain'])
                RC_CLUSTER.expire(Key,86400)
                Key = 'api_uri_lists_%s_%s' % (info['domain'], dt)
                RC_CLUSTER.sadd(Key, info['interface'])
                RC_CLUSTER.expire(Key,86400)
            except Exception as e:
                logging.error(e)
    except Exception as e:
        logging.error(e)
    finally:
        loging.write("complete %s !" %get_project_lists.__name__)
        db_op.DB.session.remove()

@tools.proce_lock()
def business_performance():
    #获取业务接口性能数据
    loging.write("start business_performance ......")
    dy = datetime.datetime.now()
    dy = dy - datetime.timedelta(days=1)
    dy = dy.strftime('%Y-%m-%d')
    try:
        dd = time.strftime('%Y-%m-%d', time.localtime())
        dt = datetime.datetime.now()
        nt = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        #采样时间段
        t = 3
        # 环比时间
        tt = dt - datetime.timedelta(minutes=t)
        ot = dt - datetime.timedelta(minutes=t * 2)
        tt = tt.strftime('%Y-%m-%dT%H:%M:%SZ')
        ot = ot.strftime('%Y-%m-%dT%H:%M:%SZ')
        # 同比时间
        sdt = dt - datetime.timedelta(days=1)
        stt = sdt - datetime.timedelta(minutes=t)
        sot = sdt - datetime.timedelta(minutes=t * 2)
        stt = stt.strftime('%Y-%m-%dT%H:%M:%SZ')
        sot = sot.strftime('%Y-%m-%dT%H:%M:%SZ')
        #获取指定域名列表
        Key = 'api_domain_lists_%s' % dd
        hosts = RC_CLUSTER.smembers(Key)
        # 获取当前时间段域名接口列表
        cmd = "select host,uri,avg_resp from analysis_logs WHERE time >= '%s' and time <='%s'" % (tt, nt)
        result = Influx_cli.query(cmd)
    except Exception as e:
        logging.error(e)
    else:
        try:
            host_key = 'influx_hosts_%s' % nt
            for infos in result.get_points():
                host = infos['host'].replace("'", '')
                if host in hosts:
                    uri = infos['uri'].replace("'", '')
                    # 获取指定域名接口列表
                    Key = 'api_uri_lists_%s_%s' % (host, dd)
                    uris = RC_CLUSTER.smembers(Key)
                    if uri in uris:
                        uri_key = 'influx_%s_%s' % (host, nt)
                        RC.sadd(host_key, host)
                        RC.expire(host_key,3600)
                        RC.sadd(uri_key, uri)
                        RC.expire(uri_key, 3600)
        except Exception as e:
            logging.error(e)
        else:
            for host in RC.smembers(host_key):
                uri_key = 'influx_%s_%s' % (host, nt)
                for uri in RC.smembers(uri_key):
                    try:
                        now_infos = defaultdict()
                        old_infos = defaultdict()
                        bef_infos = defaultdict()
                        try:
                            #获取当前数据
                            cmd = "select mean(*) from analysis_logs WHERE time >= '%s' and time <='%s' and host='%s' and uri='%s'" % (
                            tt, nt, host, uri)
                            result = Influx_cli.query(cmd)
                            for infos in result.get_points():
                                now_infos = infos
                        except Exception as e:
                            logging.error(e)
                        try:
                            #获取环比数据
                            cmd = "select mean(*) from analysis_logs WHERE time >= '%s' and time <='%s' and host='%s' and uri='%s'" % (
                            ot, tt, host, uri)
                            result = Influx_cli.query(cmd)
                            for infos in result.get_points():
                                old_infos = infos
                        except Exception as e:
                            logging.error(e)
                        try:
                            #获取同比数据
                            cmd = "select mean(*) from analysis_logs WHERE time >= '%s' and time <='%s' and host='%s' and uri='%s'" % (
                                sot, stt, host, uri)
                            result = Influx_cli.query(cmd)
                            for infos in result.get_points():
                                bef_infos = infos
                        except Exception as e:
                            logging.error(e)
                        if now_infos and old_infos and bef_infos:
                            values = defaultdict()
                            #获取接口指标列表
                            Keys = ('mean_avg_resp', 'mean_status_5xx', 'mean_status_4xx', 'mean_resp_1000', 'mean_pv')
                            for key in Keys:
                                try:
                                    alart_old = 0.0
                                    alart_bef = 0.0
                                    old_val = 0.0
                                    bef_val = 0.0
                                    now_val = 0.0
                                    try:
                                        #获取报警阀值
                                        if key != 'mean_pv':
                                            val = RC.hget('op_influxdb_alarm_%s' %dy,'%s%s' %(host,uri))
                                            alarm_arg = 0.0
                                            if val:
                                                val = eval(val)
                                                if key in val:
                                                    alarm_arg = float('%.3f' %val[key])*0.8
                                    except Exception as e:
                                        logging.error(e)
                                    else:
                                        #对数据进行清洗和计算
                                        if now_infos[key] and old_infos[key] and bef_infos[key]:
                                            if now_infos[key] > 0 and old_infos[key] > 0 and bef_infos[key] > 0:
                                                if key == 'mean_avg_resp':
                                                    try:
                                                        if now_infos[key] > alarm_arg and now_infos[key]>1:
                                                            #当前值
                                                            now_val = float(now_infos[key])
                                                            old_val = float(old_infos[key])
                                                            bef_val = float(bef_infos[key])
                                                            # 环比数据
                                                            alart_old = float(now_val - old_val) / old_val
                                                            # 同比数据
                                                            alart_bef = float(now_val - bef_val) / bef_val
                                                    except Exception as e:
                                                        logging.error(e)
                                                elif key == 'mean_pv':
                                                    try:
                                                        if now_infos[key] >15000 or (old_infos[key]-now_infos[key]) < -15000:
                                                            #当前值
                                                            now_val = int(now_infos[key])*t
                                                            old_val = int(old_infos[key])*t
                                                            bef_val = int(bef_infos[key])*t
                                                            # 环比数据
                                                            alart_old = float(now_val - old_val) /old_val
                                                            # 同比数据
                                                            alart_bef = float(now_val - bef_val) /bef_val
                                                    except Exception as e:
                                                        logging.error(e)
                                                else:
                                                    try:
                                                        alart_now = float(now_infos[key])/float(now_infos['mean_pv'])
                                                        alarm_old = float(old_infos[key])/float(old_infos['mean_pv'])
                                                        alarm_bef = float(bef_infos[key])/float(bef_infos['mean_pv'])
                                                        if alart_now > alarm_arg and alart_now >0.01:
                                                            # 当前值
                                                            now_val = alart_now*100
                                                            old_val = alarm_old*100
                                                            bef_val = alarm_bef*100
                                                            # 环比数据
                                                            alart_old = float(alart_now - alarm_old) / alarm_old
                                                            # 同比数据
                                                            alart_bef = float(alart_now - alarm_bef) / alarm_bef
                                                    except Exception as e:
                                                        logging.error(e)
                                                try:
                                                    #环比大于50%以上或者同比大于50%以上
                                                    if alart_old > 0.5 or alart_bef > 0.5:
                                                        values[key] = {
                                                                        'old':round(alart_old,1),
                                                                        'old_val':round(old_val,1),
                                                                        'bef':round(alart_bef,1),
                                                                        'bef_val':round(bef_val,1),
                                                                        'now':round(now_val,1),
                                                                        'sample': t
                                                                       }
                                                except Exception as e:
                                                    logging.error(e)
                                                try:
                                                    #环比减少50%以上，同比减少50%以上
                                                    if alart_old < -0.5 and alart_bef < -0.5:
                                                        values[key] = {
                                                                       'old':round(alart_old,1),
                                                                        'old_val':round(old_val,1),
                                                                        'bef':round(alart_bef,1),
                                                                        'bef_val':round(bef_val,1),
                                                                        'now':round(now_val,1),
                                                                        'sample': t
                                                                       }
                                                except Exception as e:
                                                    logging.error(e)
                                except Exception as e:
                                    logging.error(e)
                                    continue
                            if values:
                                incr_key = "influxdb_incr_http://%s%s" % (host, uri)
                                RC.incr(incr_key)
                                #计数过期时间
                                RC.expire(incr_key,180)
                                RC.hset('influxdb_mean_%s'%dd,"http://%s%s" % (host, uri),values)
                                RC.expire('influxdb_mean_%s' % dd,86400)
                    except Exception as e:
                        logging.error(e)
                        continue
    #业务接口性能报警
    try:
        alarm_values = defaultdict()
        db_project = db_op.project_list
        db_business = db_op.business
        dd = time.strftime('%Y-%m-%d', time.localtime())
        url_busi_key = 'interface_url_business_%s' %dd
        alarm_key = 'interface_alarm_%s' % dd
        mean_key = 'influxdb_mean_%s' % (dd)
        alarm_lists = 'interface_list_%s' % dd
        if RC.exists(mean_key):
            values = RC.hgetall(mean_key)
            values = {key: eval(values[key]) for key in values}
            for url in values:
                try:
                    incr_key = "influxdb_incr_%s" % url
                    if RC.exists(incr_key):
                        incr = int(RC.get(incr_key))
                        if incr > 1:
                            business = '未知'
                            domain = url.split('/')[2]
                            #获取接口对应的业务信息
                            business_id = db_project.query.with_entities(distinct(db_project.business_id)).filter(
                                db_project.domain.like('%{0},%'.format(domain))).all()
                            if business_id:
                                business_id = business_id[0][0]
                                business = db_business.query.with_entities(db_business.business).filter(
                                    db_business.id == business_id).all()
                                business = business[0][0]
                            values[url]['incr'] = incr
                            values[url]['business'] = business
                            RC.hset(alarm_key, url, values[url])
                            RC.expire(alarm_key,180)
                except Exception as e:
                    logging.error(e)
                    continue
            if RC.exists(alarm_key):
                Keys = {'mean_avg_resp': '平均响应时间',
                        'mean_status_5xx': '5xx状态码',
                        'mean_status_4xx': '4xx状态码',
                        'mean_resp_1000': '响应时间大于1s',
                        'mean_pv':'pv访问量'}
                alarm_values = RC.hgetall(alarm_key)
                alarm_values = {key: eval(alarm_values[key]) for key in alarm_values}
                for url in alarm_values:
                    try:
                        #收集业务名称信息
                        RC.hset(url_busi_key, url, alarm_values[url]['business'])
                        #报警条件判断
                        if int(alarm_values[url]['incr']) >3:
                            RC.sadd(alarm_lists,url)
                            for key in alarm_values[url]:
                                if key in Keys:
                                    vals = alarm_values[url][key]
                                    if key == 'mean_avg_resp':
                                        info = '当前数值:{0}s'.format('%.2f'%vals['now'])
                                    elif key  == 'mean_pv':
                                        info = '当前pv:{0}'.format('%.2f' %vals['now'])
                                    else:
                                        info = '当前占比:{0}%'.format('%.2f' %vals['now'])
                                    if float(vals['bef']) >=0:
                                        if key =='mean_avg_resp':
                                            bef_info = '同比增长:{0}%(昨天数值:{1}s)'.format(round(vals['bef']* 100,1),round(vals['bef_val'],1))
                                        elif key =='mean_pv':
                                            bef_info = '同比增长:{0}%(昨天pv:{1})'.format(round(vals['bef']* 100,1),round(vals['bef_val']))
                                        else:
                                            bef_info = '同比增长:{0}%(昨天占比:{1}%)'.format(round(vals['bef']* 100,1),round(vals['bef_val'],1))
                                    else:
                                        if key =='mean_avg_resp':
                                            bef_info = '同比减少:{0}%(昨天数值:{1}s)'.format(round(vals['bef']* 100,1),round(vals['bef_val'],1))
                                        elif key =='mean_pv':
                                            bef_info = '同比减少:{0}%(昨天pv:{1})'.format(round(vals['bef']* 100,1),round(vals['bef_val']))
                                        else:
                                            bef_info = '同比减少:{0}%(昨天占比:{1}%)'.format(round(vals['bef']* 100,1),round(vals['bef_val'],1))
                                    if float(vals['old']) >=0:
                                        if key =='mean_avg_resp':
                                            old_info = '环比增长:{0}%(三分钟前数值:{1}s)'.format(round(vals['old']* 100,1),round(vals['old_val'],1))
                                        elif key == 'mean_pv':
                                            old_info = '环比增长:{0}%(三分钟前pv:{1})'.format(round(vals['old']* 100,1),round(vals['old_val']))
                                        else:
                                            old_info = '环比增长:{0}%(三分钟前占比:{1}%)'.format(round(vals['old']* 100,1),round(vals['old_val'],1))
                                    else:
                                        if key == 'mean_avg_resp':
                                            old_info = '环比减少:{0}%(三分钟前数值:{1}s)'.format(round(vals['old']* 100,1),round(vals['old_val'],1))
                                        elif key == 'mean_pv':
                                            old_info = '环比减少:{0}%(三分钟前pv:{1})'.format(round(vals['old']* 100,1),round(vals['old_val']))
                                        else:
                                            old_info = '环比减少:{0}%(三分钟前占比:{1}%)'.format(round(vals['old']* 100,1),round(vals['old_val'],1))
                                    text = ['**线上业务:%s**' % alarm_values[url]['business'],"业务接口:%s" % url,'**详情:**',
                                            '性能指标:%s,%s' %(Keys[key],info),bef_info,old_info
                                            ,'采样数据:{0}分钟,持续时间:{1}分钟'.format(vals['sample'],int(alarm_values[url]['incr'])*3),
                                            '**接口性能异常!**']
                                    if str(alarm_values[url]['business']) not in ['web']:
                                        tools.dingding_msg(text)
                                        #统计业务接口报警次数
                                        alarm_count_key = 'op_business_alarm_count_%s' %dd
                                        RC_CLUSTER.hincrby(alarm_count_key,url,1)
                                        alarm_busi_key = 'op_business_alarm_busi_%s' %dd
                                        RC_CLUSTER.hincrby(alarm_busi_key,alarm_values[url]['business'],1)
                                        alarm_perf_key = 'op_business_alarm_perf_%s' %dd
                                        RC_CLUSTER.hincrby(alarm_perf_key,Keys[key],1)
                                        RC_CLUSTER.expire(alarm_count_key,604800)
                                        RC_CLUSTER.expire(alarm_busi_key,604800)
                                        RC_CLUSTER.expire(alarm_perf_key,604800)
                                        time.sleep(1)
                    except Exception as e:
                        logging.error(e)
                        continue
    except Exception as e:
        logging.error(e)
    finally:
        # 接口性能恢复通知
        if alarm_values and RC.exists(alarm_lists):
            url_lists = RC.smembers(alarm_lists)
            alarms = [url for url in alarm_values if int(alarm_values[url]['incr']) >2]
            for url in url_lists:
                if url not in alarms:
                    business = RC.hget(url_busi_key, url)
                    text = ['**线上业务:%s**' %business, "业务接口:%s" % url, '**接口性能恢复正常!**']
                    RC.srem(alarm_lists, url)
                    #发送报警恢复信息
                    if business not in ['web']:
                        tools.dingding_msg(text)
        RC.expire(alarm_lists,86400)
        RC.expire(url_busi_key, 86400)
        db_op.DB.session.remove()
        loging.write("complete business_performance !")

@tools.proce_lock()
def reboot_tomcat():
    try:
        loging.write("start %s ......" %reboot_tomcat.__name__)
        lte_date = datetime.datetime.now()
        gte_date = lte_date - datetime.timedelta(minutes=5)
        lte_date = lte_date.strftime('%Y-%m-%dT%H:%M:%S+08:00')
        gte_date = gte_date.strftime('%Y-%m-%dT%H:%M:%S+08:00')
        db_project = db_op.project_list
        Msg = []
        def action(reboot_lists, text, reboot=False):
            try:
                cmds = {6695: "weather_v3", 5661: "tomcat-L1", 5662: "tomcat-L2",6671:'tomcat-whapi1'}
                # 判断ip是否在自有服务列表
                for host, app_port in reboot_lists:
                    if host and app_port:
                        if ',' in app_port:
                            app_port = app_port.split(',')[0]
                        if int(app_port) >1024:
                            project = '未知项目'
                            #判断服务器的真实ip
                            host = tools.real_ip(host)
                            #获取服务器ssh端口
                            vals = db_project.query.with_entities(db_project.ssh_port, db_project.project).filter(
                                and_(db_project.ip == host, db_project.app_port == app_port)).all()
                            if vals and host not in ('192.168.1.15', '192.168.1.16'):
                                if len(vals[0]) == 2:
                                    ssh_port, project = vals[0]
                                    if reboot:
                                        try:
                                            # 远程进行tomcat重启操作
                                            Ssh = SSH.ssh(ip=host, ssh_port=ssh_port)
                                            Ssh.Run("supervisorctl  restart  {0}".format(cmds[int(app_port)]))
                                            Ssh.Close()
                                            time.sleep(15)
                                        except Exception as e:
                                            logging.error(e)
                                            continue
                                        else:
                                            text.append("%s:%s -> %s:%s" % (host,ssh_port,app_port,project))
                            if not reboot and vals:
                                text.append("%s:%s -> %s" % (host, app_port, project))
            except Exception as e:
                logging.error(e)
            finally:
                return text
        #499状态码
        try:
            body = {"size": 0, "query": {"bool": {"must": [{"query_string": {"query": "status:499",}},{"range": {"time_iso8601": {
                                "gte": gte_date,"lte": lte_date}}}]}},"aggs": {"hosts": {"terms": {"field": "upstream_addr.keyword",
                                "size": 5,"order": {"_count": "desc"}}}}}
            indexs = ('logstash-nginx-log-whv3*',)
            text = ["**自动重启tomcat以下实例:**"]
            reboot_lists = []
            for index in indexs:
                res = es.search(index=index, body=body)
                reboot_lists = [info['key'].split(':') for info in res['aggregations']['hosts']['buckets'] if info['doc_count'] > 60 if len(info['key'].split(':'))==2]
            if reboot_lists:
                text = action(reboot_lists, text, reboot=True)
            Msg.append(text)
        except Exception as e:
            logging.error(e)
        #响应超时
        try:
            text = ["**自动重启tomcat以下实例:**"]
            body = {"size": 0,
                    "query": {
                        "bool": {
                            "filter": [{
                                "range": {
                                    "time_iso8601": {
                                        "gte":gte_date,
                                        "lte":lte_date
                                    }
                                }
                            },]
                        }
                    },
                    "aggs": {
                        "3": {
                            "terms": {
                                "field": "upstream_addr.keyword",
                                "size": 100,
                                "order": {
                                    "rt": "desc"
                                }
                            },
                            "aggs": {
                                "rt": {
                                    "avg": {
                                        "field": "upstream_response_time"
                                    }
                                }
                            }
                        }
                    }
                    }
            res = es.search(index='logstash-nginx-log-coapi-*', body=body)
            rt_lists = {}
            reboot_lists = []
            for info in res['aggregations']['3']['buckets']:
                if ',' not in info['key']:
                    rt = int(float(info['rt']['value']) * 1000)
                    if rt > 50 and int(info['doc_count']) > 10000:
                        host, app_port = info['key'].split(':')
                        # 判断服务器的真实ip
                        host = tools.real_ip(host)
                        rt_lists[rt] = (host,app_port)
            if rt_lists:
                rt_lists = sorted(rt_lists.items(), key=lambda item: item[0],reverse=True)
                reboot_lists.append(rt_lists[0][1])
                host,app_port = rt_lists[0][1]
                text.append("{0}:{1} -> {2}ms".format(host, app_port,rt_lists[0][0]))
                text = action(reboot_lists, text, reboot=True)
            Msg.append(text)
        except Exception as e:
            logging.error(e)

        #5xx状态码
        try:
            reboot_lists = []
            body = {"size": 0,
                    "query": {"bool": {"must": [{"range": {"status": {"gte": 500, "lte": 599}}}, {"range": {"time_iso8601": {
                        "gte": gte_date, "lte": lte_date}}}]}},
                    "aggs": {"hosts": {"terms": {"field": "upstream_addr.keyword",
                                                 "size": 10, "order": {"_count": "desc"}}}}}
            indexs = ('logstash-nginx-log-*',)
            text = ["**tomcat服务5xx状态码实例:**"]
            for index in indexs:
                res = es.search(index=index, body=body)
                reboot_lists = [info['key'].split(':') for info in res['aggregations']['hosts']['buckets'] if
                                info['doc_count'] > 60 if len(info['key'].split(':'))==2]
            if reboot_lists:
                text = action(reboot_lists, text, reboot=False)
            Msg.append(text)
        except Exception as e:
            logging.error(e)
    except Exception as e:
        logging.error(e)
    finally:
        # 发送钉钉群消息
        for msg in Msg:
            if len(msg) > 1:
                tools.dingding_msg(msg)
        loging.write("complete %s !" % reboot_tomcat.__name__)
        db_op.DB.session.remove()

@tools.proce_lock()
def business_monitor(check_url=None):
    try:
        td = time.strftime("%Y-%m-%d %H:%M:00", time.localtime())
        checks = []
        db_busi_m = db_op.business_monitor
        values = db_busi_m.query.with_entities(db_busi_m.url, db_busi_m.method, db_busi_m.project, db_busi_m.version,
                                               db_busi_m.lock, db_busi_m.alart_token).all()
        if check_url:
            values = db_busi_m.query.with_entities(db_busi_m.url, db_busi_m.method, db_busi_m.project, db_busi_m.version,
                                                   db_busi_m.lock, db_busi_m.alart_token).filter(
                db_busi_m.url == check_url).all()
        def check_interface(val):
            try:
                URL,method,project,version,lock,alart_token = val
                def alarm():
                    # 记录故障次数
                    RC.incr(error_alarm)
                    RC.expire(error_alarm, 600)
                    # 判断触发报警条件
                    if int(RC.get(error_alarm)) > 3:
                        try:
                            if int(lock) == 0:
                                tools.dingding_msg(text, alart_token)
                                db_busi_m.query.filter(db_busi_m.url == URL).update({db_busi_m.update_time: td,
                                                                                     db_busi_m.alarm_time: td,
                                                                                     db_busi_m.code: 1,
                                                                                     db_busi_m.error_ip: ip})
                                db_op.DB.session.commit()
                        except Exception as e:
                            logging.error(e)
                        else:
                            RC.delete(recovery_alarm)
                            RC.delete(error_alarm)
                            # 标记恢复通知
                            RC.incr(recovery_alarm)
                domain = URL.split('/')[2]
                if ':' in domain:
                    domain = domain.split(':')[0]
                headers = {'Host':domain}
                if URL.count(':') >1:
                    ipaddress = [domain]
                else:
                    ipaddress = tools.dig(domain)
                if ipaddress:
                    for ip in set(ipaddress):
                        try:
                            isp = ip_adress.Search(ip)
                            if isp:
                                isp = isp.split(',')[-1]
                            url = URL.split('/')
                            url[2]= ip
                            url = '/'.join(url)
                            error_alarm = 'error_%s_%s'%(URL,ip)
                            recovery_alarm = 'recovery_%s_%s' % (URL, ip)
                            text = ['项目:%s' % project, "线上版本:%s" % version,'监控接口:%s' % URL,'解析IP:%s' % ip, 'ISP线路:%s' % isp,'**健康检测失败!**']
                            try:
                                if method == 'post':
                                    resp = requests.post(url, data={'src': 1}, headers=headers,timeout=5)
                                else:
                                    resp = requests.get(url,headers=headers,timeout=5)
                            except Exception as e:
                                loging.write(e)
                                if check_url:
                                    checks.append(ip)
                                else:
                                    text.insert(5, "故障原因:%s" % str(e).split(':')[-1])
                                    alarm()
                            else:
                                if int(resp.status_code) in (200,301,302,304):
                                    result = resp.json()
                                    ver = ''
                                    proj = ''
                                    if 'rc' in result:
                                        if 'ver' in result['rc']:
                                            ver = result['rc']['ver']
                                        if 'proj' in result['rc']:
                                            proj = result['rc']['proj']
                                    db_busi_m.query.filter(db_busi_m.url == URL).update({db_busi_m.version:ver,
                                                                                     db_busi_m.project:proj,
                                                                                    db_busi_m.code: 0,
                                                                                     db_busi_m.update_time:td})
                                    db_op.DB.session.commit()
                                    #故障恢复通知条件判断
                                    if RC.exists(recovery_alarm):
                                        RC.incr(recovery_alarm)
                                        RC.expire(recovery_alarm,600)
                                        if int(RC.get(recovery_alarm)) >2:
                                            text = ['项目:%s' % project, "线上版本:%s" % version, '监控接口:%s' % URL,
                                            '解析IP:%s' % ip, 'ISP线路:%s' % isp, '**服务恢复正常!**']
                                            try:
                                                tools.dingding_msg(text,alart_token)
                                                #自动解除报警锁定及故障状态
                                                RC.delete(recovery_alarm)
                                                RC.delete(error_alarm)
                                                db_busi_m.query.filter(and_(db_busi_m.url == URL)).update({db_busi_m.lock:0,
                                                                                                           db_busi_m.code:0,
                                                                                                           db_busi_m.error_ip:''})
                                                db_op.DB.session.commit()
                                            except Exception as e:
                                                logging.error(e)
                                else:
                                    if check_url:
                                        checks.append(ip)
                                    else:
                                        text.insert(5,'故障原因:status code %s' % resp.status_code)
                                        alarm()
                        except Exception as e:
                            logging.error(e)
            except Exception as e:
                logging.error(e)
        if values:
            pool = ThreadPool(10)
            pool.map(check_interface,values)
            pool.close()
            pool.join()
        if check_url:
            return checks
    except Exception as e:
        logging.error(e)
    finally:
        db_op.DB.session.remove()

@tools.proce_lock()
def es_business_data():
    tm = datetime.datetime.now()
    tt = tm.strftime('%H:%M')
    td = time.strftime("%Y-%m-%d", time.localtime())
    web_key = 'internet_access_%s' % td
    lte_date = datetime.datetime.now()
    gte_date = lte_date - datetime.timedelta(minutes=1)
    lte_date = lte_date.strftime('%Y-%m-%dT%H:%M:%S+08:00')
    gte_date = gte_date.strftime('%Y-%m-%dT%H:%M:%S+08:00')
    # 获取网站并发数据
    try:
        body = {"query":{"range":{"time_iso8601": {"gte": "%s" % gte_date,"lte": "%s" % lte_date}}},
                "aggs": {
                    "avg_resp": {
                        "avg": {"field": "upstream_response_time"}
                    }
                }}
        res = es.search(index='logstash-nginx-log-*', body=body)
        if res['hits']['total']:
            rt = float(res['aggregations']['avg_resp']['value'])
            if rt >1:
                RC.rpush(web_key, [tt,int(res['hits']['total'])*rt])
            else:
                RC.rpush(web_key, [tt, int(res['hits']['total'])])
            RC.expire(web_key,864000)
    except Exception as e:
        logging.error(e)
    try:
        #获取错误状态码数据
        err_4xx = 'error_4xx_%s' % td
        err_5xx = 'error_5xx_%s' % td
        body = {'size': 0, "query": {"bool": {"must": [{"range": {"time_iso8601": {"gte": gte_date, "lte": lte_date}}},
                                                       {"range": {"status": {"gte": 400, "lte": 499}}}]}, }}
        res = es.search(index='logstash-nginx-log-*', body=body)
        if res:
            RC.rpush(err_4xx, [tt, int(res['hits']['total'])])
            RC.expire(err_4xx, 86400)
        body = {'size': 0, "query": {"bool": {"must": [{"range": {"time_iso8601": {"gte": gte_date, "lte": lte_date}}},
                                                       {"range": {"status": {"gte": 500, "lte": 599}}}]}, }}
        res = es.search(index='logstash-nginx-log-*', body=body)
        if res:
            RC.rpush(err_5xx, [tt, int(res['hits']['total'])])
            RC.expire(err_5xx, 86400)
    except Exception as e:
        logging.error(e)
    #获取响应时间段数据
    try:
        upstream = {'0-100':(0,0.1),'100-200':(0.1,0.2),'200-500':(0.2,0.5),'500-1000':(0.5,1),'1000-3000':(1,3),'3000+':(3,60)}
        for k in upstream:
            Key = 'es_get_time_%s_%s' %(k,td)
            res = es.search(index='logstash-nginx-log-*', body={"query": {
                "bool": {
                    "must": [{"range": {"time_iso8601": {"gte": gte_date, "lte": lte_date}}},
                             {"range": {"upstream_response_time": {"gte": upstream[k][0], "lte": upstream[k][1]}}}]
                },
            },
                "aggs": {
                    "avg_resp": {
                        "avg": {"field": "upstream_response_time"}
                    }
                }
            })
            if res['aggregations']['avg_resp']['value']:
                val = [int(res['hits']['total']),int(float(res['aggregations']['avg_resp']['value'])*1000)]
                RC.hset(Key,'%s_%s'%(k,tt),val)
                RC.expire(Key,86400)
    except Exception as e:
        logging.error(e)

@tools.proce_lock()
def influxdb_counts():
    dt = datetime.datetime.now()
    tt = dt - datetime.timedelta(hours=1)
    nt = dt.strftime('%Y-%m-%dT%H:00:00Z')
    tt = tt.strftime('%Y-%m-%dT%H:00:00Z')
    Influx_wri = InfluxDBClient(influxdb_host,influxdb_port,influxdb_user,influxdb_pw, 'analysis_logs')
    cmd = "select host,uri,avg_resp from analysis_logs WHERE time >= '%s' and time <'%s'" % (tt,nt)
    result = Influx_cli.query(cmd)
    if result:
        for infos in result.get_points():
            try:
                host = infos['host'].replace("'", '')
                RC.sadd('influx_hosts_%s' % nt, host)
                uri = infos['uri'].replace("'", '')
                RC.sadd('influx_%s_%s' % (host, nt), uri)
            except Exception as e:
                logging.error(e)
                continue
    for host in RC.smembers('influx_hosts_%s' % nt):
        for uri in RC.smembers('influx_%s_%s' % (host, nt)):
            try:
                cmd = "select mean(*) from analysis_logs WHERE time >= '%s' and time <'%s' and host='%s' and uri='%s'" % (tt,nt, host, uri)
                result = Influx_cli.query(cmd)
                if result:
                    for infos in result.get_points():
                        del infos['time']
                        infos = {info:float(infos[info]) for info in infos}
                        json_body = [{"measurement": "analysis%s" % tt.split('T')[0].split('-')[0], "tags": {"host": host, "uri": uri},
                             "fields": infos, 'time': nt}]
                        Influx_wri.write_points(json_body)
            except Exception as e:
                logging.error(e)
                continue

@tools.proce_lock()
def influxdb_alarm():
    dt = datetime.datetime.now()
    tt = dt - datetime.timedelta(days=3)
    nt = dt.strftime('%Y-%m-%dT00:00:00Z')
    dd = tt.strftime('%Y-%m-%d')
    tt = tt.strftime('%Y-%m-%dT00:00:00Z')
    Influx_cli = InfluxDBClient(influxdb_host, influxdb_port, influxdb_user, influxdb_pw,'analysis_logs')
    Key = 'api_domain_lists_%s' % dd
    hosts = RC_CLUSTER.smembers(Key)
    try:
        for host in hosts:
            Key = 'api_uri_lists_%s_%s' % (host, dd)
            uris = RC_CLUSTER.smembers(Key)
            for uri in uris:
                try:
                    infos = None
                    cmd = "select max(*) from " + 'analysis%s' %time.strftime('%Y',time.localtime()) + " WHERE time >= '%s' and time <='%s' and host='%s' and uri='%s'" % (
                    tt, nt, host, uri)
                    result = Influx_cli.query(cmd)
                    if result:
                        for infos in result.get_points():
                            infos = infos
                        if infos:
                            Key = 'op_influxdb_alarm_%s' %dd
                            RC.hset(Key,'%s%s' %(host,uri),{
                                'mean_avg_resp':infos['max_mean_avg_resp'],
                                'mean_resp_1000':infos['max_mean_resp_1000']/infos['max_mean_pv'],
                                'mean_status_4xx':infos['max_mean_status_4xx']/infos['max_mean_pv'],
                                'mean_status_5xx':infos['max_mean_status_5xx']/infos['max_mean_pv']
                            })
                            RC.expire(Key,864000)
                except Exception as e:
                    logging.error(e)
                    continue
    except Exception as e:
        logging.error(e)

@tools.proce_lock()
def zabbix_counts():
    dict_load = defaultdict()
    dict_mem = defaultdict()
    dict_openfile = defaultdict()
    free_load = []
    free_mem = []
    free_openfile = []
    now_time = datetime.datetime.now()
    dt = now_time - datetime.timedelta(minutes=15)
    dt = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    Influx_cli = InfluxDBClient(influxdb_host, influxdb_port, influxdb_user, influxdb_pw, 'zabbix_infos')
    cmd = "select mean(*) from server_infos where time >='%s' group by hostname" % dt
    try:
        results = Influx_cli.query(cmd)
        if results:
            for key in results.keys():
                hostname = key[-1]['hostname']
                if not hostname.startswith('nj'):
                    for infos in results[key]:
                        if infos['mean_cpu_load'] >= 0:
                            dict_load[hostname] = infos['mean_cpu_load']
                        if infos['mean_mem_use'] >=0:
                            dict_mem[hostname] = infos['mean_mem_use']
                        if infos['mean_openfile'] >=0:
                            dict_openfile[hostname] = infos['mean_openfile']
    except Exception as e:
        logging.error(e)
    try:
        if dict_load:
            loads = sorted(dict_load.items(), key=lambda item: int(item[1]), reverse=True)
            RC_CLUSTER.set('op_zabbix_server_load_top',loads[:20])
            free_load = [info[0] for info in loads if int(info[-1]) <=3]
        if dict_mem:
            mems = sorted(dict_mem.items(), key=lambda item: int(item[1]), reverse=True)
            RC_CLUSTER.set('op_zabbix_server_mem_top', mems[:20])
            free_mem = [info[0] for info in mems if int(info[-1]) <= 5]
        if dict_openfile:
            openfiles = sorted(dict_openfile.items(), key=lambda item: int(item[1]), reverse=True)
            RC_CLUSTER.set('op_zabbix_server_openfile_top', openfiles[:20])
            free_openfile = [info[0] for info in openfiles if int(info[-1]) <= 1024]
        if free_load and free_mem and free_openfile:
            RC_CLUSTER.set('op_zabbix_free_servers',set(free_load)&set(free_mem)&set(free_openfile))
        for key in ('op_zabbix_server_load_top','op_zabbix_server_mem_top','op_zabbix_server_openfile_top','op_zabbix_free_servers'):
            RC_CLUSTER.expire(key,360)
    except Exception as e:
        logging.error(e)
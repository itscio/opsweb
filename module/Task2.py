#-*- coding: utf-8 -*-
import redis
from module import loging,SSH,db_idc,db_op,tools
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_,distinct
from influxdb import InfluxDBClient
from collections import defaultdict
from pyzabbix.api import ZabbixAPI
import datetime
import time
import pytz
from elasticsearch import Elasticsearch
from functools import reduce
from multiprocessing.dummy import Pool as ThreadPool
from tcpping import tcpping
from kubernetes import client
from pykafka import KafkaClient
app = Flask(__name__)
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/sql.conf')
app.config.from_pyfile('../conf/es.conf')
app.config.from_pyfile('../conf/tokens.conf')
app.config.from_pyfile('../conf/kafka.conf')
app.config.from_pyfile('../conf/zabbix.conf')
logging = loging.Error()
zabbix_url = app.config.get('ZABBIX_URL')
zabbix_user = app.config.get('ZABBIX_USER')
zabbix_pw = app.config.get('ZABBIX_PW')
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
RC = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
redis_data = app.config.get('REDIS_DATA')
RC_CLUSTER = redis.StrictRedis(host=redis_data, port=redis_port,decode_responses=True)
influxdb_host = app.config.get('INFLUXDB_HOST')
influxdb_port = app.config.get('INFLUXDB_PORT')
influxdb_user = app.config.get('INFLUXDB_USER')
influxdb_pw = app.config.get('INFLUXDB_PASSWORD')
influxdb_db = app.config.get('INFLUXDB_DB')
es_hosts = app.config.get('ES_HOSTS')
es = Elasticsearch(hosts=es_hosts,timeout=60)
ops_token = app.config.get('OPS_TOKEN')
redis_token = app.config.get('REDIS_TOKEN')
KAFKA_HOSTS = app.config.get('KAFKA_HOSTS')
config,contexts,config_file = tools.k8s_conf()
@tools.proce_lock()
def task_cron_run():
    try:
        # 获取业务访问数据
        db_business = db_op.business
        db_project = db_op.project_list
        business = db_business.query.with_entities(db_business.id, db_business.business).all()
        year = time.strftime('%Y', time.localtime())
        ot = datetime.datetime.now() - datetime.timedelta(days=0)
        ot = ot.strftime('%Y-%m-%dT00:00:00Z')
        Key = 'op_business_pv_%s' % ot.split('T')[0]
        Influx_cli = InfluxDBClient(influxdb_host, influxdb_port, influxdb_user, influxdb_pw, 'analysis_logs')
        business = {busi[0]: busi[1] for busi in business if busi}
        for id in business:
            business_domain = db_project.query.with_entities(distinct(db_project.domain)).filter(and_(
                db_project.business_id == int(id),db_project.domain != '')).all()
            if business_domain:
                pv_sum = []
                try:
                    for hosts in [domain[0] for domain in business_domain if domain]:
                        if ',' in hosts:
                            hosts = hosts.split(',')
                            for host in hosts:
                                try:
                                    cmd = 'select sum(mean_pv) from ' + 'analysis%s' % year + " where time >='%s' and host = '%s';" % (
                                    ot, host)
                                    result = Influx_cli.query(cmd)
                                    if result:
                                        for infos in result.get_points():
                                            if infos:
                                                pv_sum.append(infos['sum'] * 60)
                                except Exception as e:
                                    logging.error(e)
                except Exception as e:
                    logging.error(e)
                if pv_sum:
                    pv_sum = reduce(lambda x, y: x + y, pv_sum)
                    RC_CLUSTER.hset(Key, business[id], pv_sum)
    except Exception as e:
        logging.error(e)

@tools.proce_lock()
def other_info_task():
    db_project_other = db_op.project_other
    db_crontabs = db_idc.crontabs
    db_servers = db_idc.idc_servers
    db_hosts = db_idc.hosts
    update_date = time.strftime('%Y-%m-%d', time.localtime())
    infos = db_servers.query.with_entities(db_servers.id,db_servers.ip,db_servers.ssh_port).filter(and_(db_servers.status !='维护中',db_servers.comment !='跳过')).all()
    try:
        for info in infos:
            server_id,ip,ssh_port = info
            if tcpping(host=ip, port=ssh_port, timeout=3):
                try:
                    Ssh = SSH.ssh(ip=ip, ssh_port=ssh_port)
                except:
                    continue
                else:
                    try:
                        #收集crontab信息
                        results = Ssh.Run("ls /var/spool/cron/")
                        if results['stdout']:
                            for user in results['stdout']:
                                user = user.strip()
                                results = Ssh.Run("cat /var/spool/cron/%s" %user)
                                if results['stdout']:
                                    v = db_crontabs.query.filter(db_crontabs.server_id==int(server_id)).all()
                                    for c in v:
                                        db_idc.DB.session.delete(c)
                                        db_idc.DB.session.commit()
                                    for result in results['stdout']:
                                        if not result.startswith('#') and '*' in result:
                                            result = result.strip().split()
                                            cron = ' '.join(result[:5])
                                            action = ' '.join(result[5:])
                                            c = db_crontabs(cron=cron,user=user,action=action,server_id=int(server_id),update_time=update_date)
                                            db_idc.DB.session.add(c)
                                            db_idc.DB.session.commit()
                    except Exception as e:
                        logging.error(e)
                    # 收集jar运行信息
                    try:
                        results = Ssh.Run("ps -ef|grep java|grep -e '.jar$'")
                        if results['stdout']:
                            vals = []
                            v = db_project_other.query.filter(db_project_other.server_id == int(server_id)).all()
                            for c in v:
                                db_op.DB.session.delete(c)
                                db_op.DB.session.commit()
                            for result in results['stdout']:
                                if 'hadoop' not in result and 'hive' not in result:
                                    result = result.strip().split()[-1]
                                    if '/' in result:
                                        result = result.split('/')[-1]
                                    vals.append(result)
                            for val in set(vals):
                                result = db_project_other.query.filter(and_(db_project_other.project==val,db_project_other.server_id==server_id)).all()
                                if not result:
                                    business_id = 0
                                    business = db_project_other.query.with_entities(db_project_other.business_id).filter(and_(
                                        db_project_other.project == val,db_project_other.business_id != 0)).all()
                                    if business:
                                        business_id = business[0][0]
                                    c = db_project_other(lable='java', project=val, server_id=server_id,business_id=business_id, update_time=update_date)
                                    db_op.DB.session.add(c)
                                    db_op.DB.session.commit()
                    except Exception as e:
                        logging.error(e)
                    #收集hosts信息
                    try:
                        results = Ssh.Run("cat /etc/hosts")
                        if results['stdout']:
                            v = db_hosts.query.filter(db_hosts.server_id == int(server_id)).all()
                            for c in v:
                                db_idc.DB.session.delete(c)
                                db_idc.DB.session.commit()
                            for line in results['stdout']:
                                if not line.startswith('#') and '127.0.0.1' not in line:
                                    line = line.strip().split()
                                    if line:
                                        if len(line) == 2:
                                            if 'localhost' not in line[1]:
                                                c = db_hosts(host=line[0],hostname=line[1],server_id=server_id,update_time=update_date)
                                                db_idc.DB.session.add(c)
                                                db_idc.DB.session.commit()
                                        if len(line) > 2:
                                            for hostname in line[1:]:
                                                if not hostname.startswith('#') and not 'localhost' in  hostname:
                                                    c = db_hosts(host=line[0],hostname=hostname, server_id=server_id,
                                                                 update_time=update_date)
                                                    db_idc.DB.session.add(c)
                                                    db_idc.DB.session.commit()
                    except Exception as e:
                        logging.error(e)
                    Ssh.Close()
    except Exception as e:
        logging.error(e)
    finally:
        db_idc.DB.session.remove()
        db_op.DB.session.remove()

@tools.proce_lock()
def redis_info_task():
    loging.write("start %s ......" % redis_info_task.__name__)
    db_third = db_idc.third_resource
    db_redis = db_idc.redis_info
    db_servers = db_idc.idc_servers
    update_date = time.strftime('%Y-%m-%d', time.localtime())
    try:
        server_ids = db_servers.query.with_entities(db_servers.id,db_servers.ip,db_servers.ssh_port,db_servers.hostname).all()
        for infos in server_ids:
            RC_CLUSTER.hset('op_server_hostnames',infos[0],infos[-1])
            RC_CLUSTER.hset('op_server_hostnames', '%s:%s'%(infos[1],infos[2]), infos[-1])
        server_ids = {"%s:%s"%(infos[1],infos[2]):infos[0] for infos in server_ids}
        redis_list = db_third.query.with_entities(db_third.ip,db_third.ssh_port,db_third.app_port).filter(db_third.resource_type == 'redis').all()
        ssh_ports = {"%s:%s" %(infos[0],infos[2]):infos[1] for infos in redis_list}
        def Redis_info(info):
            ip,ssh_port,app_port = info
            #初始化参数
            masterauth = None
            requirepass = None
            pid = None
            conf_dir = None
            conf_file = ""
            redis_type = {'master': '否', 'slave': '否', 'cluster': '否'}
            #判断ssh端口是否连通
            if tcpping(host=ip, port=app_port, timeout=5):
                try:
                    Ssh = SSH.ssh(ip=ip, ssh_port=ssh_port)
                except:
                    pass
                else:
                    cmd = "netstat -lntp|grep :%s" % app_port
                    results = Ssh.Run(cmd)
                    if results['stdout']:
                        for line in results['stdout'][0].split():
                            if '/redis' in line:
                                pid = line.split('/')[0]
                                break
                        if pid:
                            cmd = "/bin/ps -ef|grep -v grep|grep {}".format(pid)
                            results = Ssh.Run(cmd)
                            if results['stdout']:
                                result = results['stdout'][0]
                                if 'cluster' in result:
                                    redis_type['cluster'] = '是'
                                else:
                                    try:
                                        result = results['stdout'][0].split()[-1]
                                        if '/' in result:
                                            conf_file = "/xxxx/xxxx/xxxx/redis/etc/{}".format(result.split('/')[-1])
                                        if not conf_file.endswith('.conf'):
                                            cmd = "lsof -p {}|grep 'cwd'".format(pid)
                                            cwd = Ssh.Run(cmd)
                                            if cwd['stdout']:
                                                for line in cwd['stdout']:
                                                    if 'redis' in line:
                                                        conf_dir = line.split()[-1]
                                                        break
                                                if conf_dir:
                                                    cmd = "grep {0} -r {1}/|grep '.conf:port'".format(app_port, conf_dir)
                                                    results = Ssh.Run(cmd)
                                                    if results['stdout']:
                                                        for line in results['stdout']:
                                                            if ':port {}'.format(app_port) in line:
                                                                conf_file = line.split(':')[0]
                                        if conf_file.endswith('.conf'):
                                            cmd = "grep masterauth {}".format(conf_file)
                                            results = Ssh.Run(cmd)
                                            if results['stdout']:
                                                masterauth =  results['stdout'][0].split()[-1].strip()
                                            cmd = "grep requirepass {}".format(conf_file)
                                            pw_result = Ssh.Run(cmd)
                                            if pw_result['stdout']:
                                                requirepass =  pw_result['stdout'][0].split()[-1].strip()
                                        RC = redis.StrictRedis(ip, int(app_port),decode_responses=True)
                                        if requirepass:
                                            RC = redis.StrictRedis(ip,int(app_port),password=requirepass,decode_responses=True)
                                        Infos = RC.info()
                                        if Infos['role'] == 'master':
                                            redis_type['master'] = '是'
                                        if Infos['role'] == 'slave':
                                            redis_type['slave'] = '是'
                                        counts = int((Infos['connected_slaves']))
                                        Ssh.Close()
                                    except:
                                        pass
                                    else:
                                        try:
                                            #修改记录slave信息
                                            if counts > 0:
                                                for i in range(counts):
                                                    Info = Infos['slave%s' % i]
                                                    if isinstance(Info,dict):
                                                        slave_ip = Info['ip']
                                                        slave_port = Info['port']
                                                        slave_status = Info['state']
                                                    else:
                                                        slave_ip, slave_port, slave_status = Info.split(',')
                                                    if slave_status == 'online' and int(slave_port) >1024:

                                                        try:
                                                            SSH_port = ssh_ports['%s:%s' % (slave_ip, slave_port)]
                                                            server_id = server_ids['%s:%s' %(slave_ip,SSH_port)]
                                                        except:
                                                            server_id = slave_ip
                                                            servers = db_servers.query.with_entities(db_servers.ip).filter(db_servers.s_ip.like('%{0};%'.format(slave_ip))).all()
                                                            if servers:
                                                                for server in servers:
                                                                    val = db_third.query.filter(and_(db_third.ip==server[0],db_third.app_port==slave_port)).all()
                                                                    if val:
                                                                        SSH_port = ssh_ports['%s:%s' % (server[0], slave_port)]
                                                                        server_id = server_ids['%s:%s' %(server[0],SSH_port)]
                                                                        break
                                                        try:
                                                            master_id = server_ids['%s:%s' % (ip, ssh_port)]
                                                        except:
                                                            master_id = ip
                                                        val = db_redis.query.filter(and_(db_redis.server_id == server_id, db_redis.port == slave_port)).all()
                                                        if val:
                                                            db_redis.query.filter(and_(db_redis.server_id == server_id, db_redis.port == slave_port)).update(
                                                                {db_redis.masterauth: masterauth, db_redis.requirepass: requirepass,
                                                                 db_redis.master: '否',db_redis.slave: '是',db_redis.cluster: '否',
                                                                 db_redis.Master_Host: master_id,db_redis.Master_Port: app_port})
                                                            db_idc.DB.session.commit()
                                                        else:
                                                            c = db_redis(server_id=server_id, port=slave_port, masterauth=masterauth,
                                                                         requirepass=requirepass, master='否',
                                                                         slave='是',cluster='否', Master_host=master_id,
                                                                         Master_Port=app_port, start_time=update_date,last_time='')
                                                            db_idc.DB.session.add(c)
                                                            db_idc.DB.session.commit()
                                        except:
                                            db_idc.DB.session.rollback()
                                try:
                                    #修改记录master或者cluster信息
                                    if redis_type['master'] == '是' or redis_type['cluster'] == '是':
                                        try:
                                            server_id = server_ids['%s:%s' % (ip, ssh_port)]
                                        except:
                                            server_id = ip
                                            servers = db_servers.query.with_entities(db_servers.ip).filter(db_servers.s_ip.like('%{0};%'.format(ip))).all()
                                            if servers:
                                                for server in servers:
                                                    val = db_third.query.filter(and_(db_third.ip == server[0],db_third.app_port == app_port)).all()
                                                    if val:
                                                        server_id = server_ids['%s:%s' % (server[0], ssh_port)]
                                                        break
                                        val = db_redis.query.filter(and_(db_redis.server_id == server_id, db_redis.port == app_port)).all()
                                        if val:
                                            db_redis.query.filter(
                                                and_(db_redis.server_id == server_id, db_redis.port == app_port)).update(
                                                {db_redis.masterauth: masterauth, db_redis.requirepass: requirepass,
                                                 db_redis.master: redis_type['master'],
                                                 db_redis.slave: redis_type['slave'],
                                                 db_redis.cluster: redis_type['cluster'],
                                                 db_redis.Master_Host: '',
                                                 db_redis.Master_Port: ''})
                                            db_idc.DB.session.commit()
                                        else:
                                            loging.write("add new redis %s  %s  ......" % (ip, app_port))
                                            c = db_redis(server_id=server_id, port=app_port, masterauth=masterauth,
                                                         requirepass=requirepass, master=redis_type['master'],
                                                         slave=redis_type['slave'], cluster=redis_type['cluster'],
                                                         Master_host='', Master_Port='',
                                                         start_time=update_date,last_time='')
                                            db_idc.DB.session.add(c)
                                            db_idc.DB.session.commit()
                                except:
                                    db_idc.DB.session.rollback()
            else:
                loging.write("delete not exist redis %s  %s  ......" %(ip,app_port))
                v= db_third.query.filter(and_(db_third.ip==ip,db_third.app_port==app_port)).all()
                for c in v:
                    db_idc.DB.session.delete(c)
                    db_idc.DB.session.commit()
        if redis_list:
            pool = ThreadPool(5)
            pool.map(Redis_info,set(redis_list))
            pool.close()
            pool.join()
    except Exception as e:
        logging.error(e)
    finally:
        db_idc.DB.session.remove()
        loging.write("%s complete!" %redis_info_task.__name__)

@tools.proce_lock()
def k8s_check_task():
    loging.write("start %s ......" % k8s_check_task.__name__)
    for context in contexts:
        config.load_kube_config(config_file, context=context)
        # nodes健康检测
        v1 = client.CoreV1Api()
        try:
            ret = v1.list_node(watch=False)
            for i in ret.items:
                if 'node-role.kubernetes.io/master' in i.metadata.labels:
                    node_type = 'master'
                else:
                    node_type = 'node'
                status = i.status.conditions[-1].type
                if status != 'Ready':
                    text = ['**容器平台NODE报警:%s**' % i.metadata.name,'k8s集群:%s' %context,'节点类型:%s' %node_type,'节点状态:%s' %status,'需及时处理!']
                    tools.dingding_msg(text,token=ops_token)
        except Exception as e:
            logging.error(e)
        # endpoints健康检测
        try:
            ret = v1.list_namespaced_endpoints('default')
            for i in ret.items:
                try:
                    for infos in i.subsets:
                        try:
                            for info in infos.addresses:
                                try:
                                    ip_header = '.'.join(str(info.ip).split('.')[:2])
                                    if '{}.'.format(ip_header) in ('172.16.', '10.10.'):
                                        if not tcpping(host=info.ip, port=infos.ports[0].port, timeout=5):
                                            text = ['**容器平台endpoints报警:**','k8s集群:%s' %context, 'IP:%s' % info.ip,
                                                    '服务端口:%s' % infos.ports[0].port, '服务端口不可用,需及时处理!']
                                            tools.dingding_msg(text)
                                except:
                                    continue
                        except:
                            continue
                except:
                    continue
        except Exception as e:
            logging.error(e)
        # 获取k8s的hpa副本数量
        try:
            td = time.strftime('%Y-%m-%d', time.localtime())
            th = time.strftime('%H:%M', time.localtime())
            v1_hpa = client.AutoscalingV1Api()
            ret = v1_hpa.list_horizontal_pod_autoscaler_for_all_namespaces()
            Key = 'op_hpa_chart_%s_%s' % (context, td)
            for i in ret.items:
                RC.hset(Key, '%s_%s' % (i.metadata.name, th), i.status.current_replicas)
        except Exception as e:
            logging.error(e)
        # 获取pod信息
        try:
            db_pods = db_idc.k8s_pods
            ret = v1.list_namespaced_pod(namespace='default')
            for i in ret.items:
                try:
                    val = db_pods.query.filter(and_(db_pods.pod_name==i.metadata.name,db_pods.node_name==i.spec.node_name)).all()
                    if not val:
                        c = db_pods(context=context,pod_ip=i.status.pod_ip,pod_name=i.metadata.name,
                                    node_name=i.spec.node_name,uptime=time.strftime('%Y-%m-%d %H:%M:%S',time.localtime()))
                        db_idc.DB.session.add(c)
                        db_idc.DB.session.commit()
                except Exception as e:
                    logging.error(e)
        except Exception as e:
            logging.error(e)
        finally:
            db_idc.DB.session.remove()
        # 获取event事件信息
        try:
            db_events = db_op.k8s_events
            ret = v1.list_namespaced_event('default')
            for info in ret.items:
                timestamp = str(info.first_timestamp)
                if '+' in timestamp:
                    timestamp = timestamp.split('+')[0]
                y, m, d = timestamp.split()[0].split('-')
                H, M, S = timestamp.split()[1].split(':')
                try:
                    timestamp = datetime.datetime(int(y), int(m), int(d), int(H), int(M), int(S),
                                           tzinfo=pytz.timezone('Asia/Shanghai'))
                    timestamp = timestamp + datetime.timedelta(hours=8)
                    timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    c = db_events(context=context,date_time=timestamp,kind=info.involved_object.kind,
                                  name=info.involved_object.name,namespace=info.involved_object.namespace,
                                  message=info.message,reason=info.reason,type=info.type)
                    db_op.DB.session.add(c)
                    db_op.DB.session.commit()
                except:
                    continue
        except Exception as e:
            logging.error(e)
        finally:
            db_op.DB.session.remove()

@tools.proce_lock()
def alarm_load_task():
    try:
        loging.write("start %s ......" %alarm_load_task.__name__)
        whitelist = []
        dict_load = defaultdict()
        db_server = db_idc.idc_servers
        db_zabbix = db_idc.zabbix_info
        db_project = db_op.project_list
        db_project_other = db_op.project_other
        Influx_cli = InfluxDBClient(influxdb_host, influxdb_port, influxdb_user, influxdb_pw, 'zabbix_infos')
        host_infos = db_zabbix.query.with_entities(db_zabbix.ip, db_zabbix.ssh_port,db_zabbix.hostname,
                                                   db_zabbix.update_time).filter(and_(db_zabbix.cpu_load > 100,
                                                                                      db_zabbix.icmpping == 1)).all()
        Key = "op_alarm_load_whitelist"
        if RC_CLUSTER.exists(Key):
            whitelist = RC_CLUSTER.smembers(Key)
        #循环监控疑似问题服务器
        for infos in host_infos:
            host,ssh_port,hostname,update_time=infos
            if time.strftime('%Y-%m-%d',time.localtime()) in update_time:
                try:
                    if not host.startswith('172.16.19.'):
                        now_time = datetime.datetime.now()
                        dt = now_time - datetime.timedelta(minutes=10)
                        dt = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                        cmd = "select mean(*) from server_infos where time >='%s' group by hostname" % dt
                        results = Influx_cli.query(cmd)
                        if results:
                            for key in results.keys():
                                if hostname == key[-1]['hostname']:
                                    for infos in results[key]:
                                        if infos['mean_cpu_load'] >100:
                                            dict_load[hostname] = (host,ssh_port,int(infos['mean_cpu_load']))
                except:
                    continue
        #进行重启操作
        if dict_load:
            for hostname in dict_load:
                host,ssh_port,cpu_load = dict_load[hostname]
                # 判断ssh是否可以登录
                try:
                    Ssh = SSH.ssh(ip=host,ssh_port=ssh_port)
                except:
                    continue
                else:
                    try:
                        Key = 'op_alarm_load_%s' % hostname
                        Project = None
                        RC_CLUSTER.incr(Key, 5)
                        RC_CLUSTER.expire(Key, 600)
                        ctime = int(RC_CLUSTER.get(Key))
                        if hostname not in whitelist:
                            #筛查可重启服务进程
                            results = Ssh.Run("ps -aux | sort -k3nr |head -n 1")
                            if results['stdout']:
                                results = results['stdout'][0].strip().split()
                                try:

                                    if results[-1].endswith('-rpc.jar'):
                                        pro_jar = results[-1]
                                        if pro_jar in ['xxxx.jar']:
                                            Project =pro_jar.split('.')[0]
                                    else:
                                        for line in results:
                                            if '-Dcatalina.home=' in line :
                                                Project = line.strip().split('/')[-1]
                                                break
                                except Exception as e:
                                    logging.error(e)
                                if Project:
                                    try:
                                        text = None
                                        token = ops_token
                                        # 判断是否是tomcat项目
                                        ret = db_project.query.filter(and_(db_project.ip == host, db_project.ssh_port == ssh_port)).all()
                                        if ret:
                                            #重启问题tomcat
                                            result = Ssh.Run("supervisorctl  restart  {0}".format(Project))
                                            if result['stderr']:
                                                text = ['**线上服务重启:%s**' % hostname, "CPU持续{0}分钟平均使用率:{1}%".format(ctime,cpu_load),
                                                        "相关进程:{0}".format(Project), '**服务重启失败,需手动处理!**']
                                            else:
                                                text = ['**线上服务重启:%s**' % hostname, "CPU持续{0}分钟平均使用率:{1}%".format(ctime,cpu_load),
                                                        "相关进程:{0}".format(Project), '**服务重启成功!**']
                                                token = None
                                        else:
                                            # 判断是否是jar项目
                                            server_id = db_server.query.with_entities(db_server.id).filter(db_server.hostname==hostname).all()
                                            if server_id[0]:
                                                ret = db_project_other.query.filter(db_project_other.server_id == int(server_id[0][0])).all()
                                                if ret:
                                                    text = ['**线上服务器预警:%s**' % hostname, "CPU持续{0}分钟平均使用率:{1}%".format(ctime,cpu_load),
                                                    "相关进程:{0}".format(Project), '**请及时进行处理!**']
                                        if text and not hostname.startswith('nj'):
                                            tools.dingding_msg(text,token)
                                    except Exception as e:
                                        logging.error(e)
                    finally:
                        Ssh.Close()
    finally:
        loging.write("%s complete!" %alarm_load_task.__name__)
        db_idc.DB.session.remove()
        db_op.DB.session.remove()

@tools.proce_lock()
def ingress_log():
    td = time.strftime('%Y-%m-%d', time.localtime())
    th = time.strftime('%H:%M', time.localtime())
    Key = 'op_k8s_ingress_log'
    stat_key = 'op_k8s_ingress_stat'
    rt_key = 'op_k8s_ingress_rt'
    k8s_domains_key = 'op_k8s_domains_%s' %td
    k8s_pv_key = 'op_k8s_pv_%s' %td
    now_date = datetime.datetime.now()
    lte_date = now_date.strftime('%Y-%m-%dT%H:%M:%S+08:00')
    gte_date = now_date - datetime.timedelta(minutes=1)
    gte_date = gte_date.strftime('%Y-%m-%dT%H:%M:%S+08:00')
    db_k8s_ingress = db_op.k8s_ingress
    k8s_domains = db_k8s_ingress.query.with_entities(db_k8s_ingress.domain).all()
    k8s_domains = [domain[0] for domain in k8s_domains]
    Domains = []
    def auto_delete_pod(pod_name,text):
        try:
            namespace = "default"
            for context in contexts:
                config.load_kube_config(config_file,context)
                api_instance = client.CoreV1Api()
                ret = api_instance.list_namespaced_pod(namespace=namespace)
                for i in ret.items:
                    if i.metadata.name.startswith(pod_name):
                        RC.incr(delete_pod_key, 1)
                        api_instance.delete_namespaced_pod(name=i.metadata.name,
                                                       namespace=namespace,
                                                       body=client.V1DeleteOptions())
                        time.sleep(30)
        except Exception as e:
            logging.error(e)
        finally:
            counts = RC.get(delete_pod_key)
            RC.delete(delete_pod_key)
            if counts:
                text.append('**自动处理问题pod数量:{}**'.format(counts))
            return text
    try:
        loging.write('start %s ......' % ingress_log.__name__)
        # 获取容器平台并发访问数据
        try:
            body = {"query": {"range": {"time_iso8601": {"gte": "%s" % gte_date, "lte": "%s" % lte_date}}},
                    "aggs": {
                        "avg_resp": {
                            "avg": {"field": "upstream_response_time"}
                        }
                    }}
            res = es.search(index='k8s-ingress-log-*', body=body)
            if res['hits']['total']:
                rt = float(res['aggregations']['avg_resp']['value'])
                counts = int(res['hits']['total'])
                if rt > 1:
                    # 统计全部访问量
                    RC.hset('%s_%s' % (Key, td), th, counts*rt)
                else:
                    RC.hset('%s_%s' % (Key, td), th, counts)
                RC.expire('%s_%s' % (Key, td), 864000)
                # 统计k8s总访问量
                RC.incr(k8s_pv_key, counts)
                RC.expire(k8s_pv_key, 864000)
        except Exception as e:
            logging.error(e)
        # 获取es当前1分钟的状态码统计
        try:
            body = {'size': 0, "query": {
                "bool": {
                    "must": [{"range": {"time_iso8601": {"gte": gte_date, "lte": lte_date}}}]}},
                    "aggs": {
                        "hosts": {
                            "terms": {
                                "field": "host.keyword",
                                "size": 100
                            },
                            "aggs": {
                                "counts": {
                                    "terms": {
                                        "field": "status",
                                        "size": 100
                                    }
                                }
                            }
                        }
                    }}
            res = es.search(index='k8s-ingress-log-*', body=body)
            for infos in res['aggregations']['hosts']['buckets']:
                try:
                    domain = infos['key']
                    if domain in k8s_domains:
                        Domains.append(domain)
                        counts = int(infos['doc_count'])
                        #统计域名列表
                        RC.sadd(k8s_domains_key,domain)
                        #统计域名访问量
                        RC.hset('%s_%s_%s'%(Key,domain,td),th,counts)
                        RC.expire('%s_%s_%s' % (Key, domain, td), 864000)
                        #状态码统计
                        vals = {info['key']: info['doc_count'] for info in infos['counts']['buckets']}
                        RC.hset('%s_%s_%s' % (stat_key, domain, td), th, vals)
                        RC.expire('%s_%s_%s' % (stat_key, domain, td), 864000)
                except:
                    continue
        except Exception as e:
            logging.error(e)
        try:
            # 获取es当前1分钟的响应时间统计
            body = {'size': 0, "query": {
                "bool": {
                    "must": [{"range": {"time_iso8601": {"gte": gte_date, "lte": lte_date}}}]}},
                    "aggs": {
                        "hosts": {
                            "terms": {
                                "field": "host.keyword",
                                "size": 100
                            },
                    "aggs": {
                        "avg_resp": {
                            "avg": {"field": "upstream_response_time"}
                        }
                        }}}
                    }
            res = es.search(index='k8s-ingress-log-*', body=body)
            for infos in res['aggregations']['hosts']['buckets']:
                try:
                    domain = infos['key']
                    if domain in k8s_domains:
                        RC.hset('%s_%s_%s' % (rt_key, domain, td), th,float('%.3f'%infos['avg_resp']['value']))
                        RC.expire('%s_%s_%s' % (rt_key, domain, td), 864000)
                except:
                    continue
        except Exception as e:
            logging.error(e)
        try:
            for domain in Domains:
                #业务状态码和响应时间超时报警
                text = ['**容器平台业务报警:%s**' % domain]
                stat_vals = 0.1
                nd = now_date - datetime.timedelta(minutes=1)
                th = nd.strftime('%H:%M')
                vals = RC.hget('%s_%s_%s' % (stat_key, domain, td), th)
                if vals:
                    vals = eval(str(vals))
                    if 200 in vals:
                        stat_vals = vals[200]
                    if len(vals) >1:
                        total_vals = reduce(lambda x, y: x + y, vals.values())
                    else:
                        total_vals = stat_vals
                    diff_vals = float(stat_vals)/float(total_vals)
                    if diff_vals < 0.98:
                        rt_vals = RC.hget('%s_%s_%s' % (rt_key, domain, td), th)
                        Key = 'op_k8s_project_alarm'
                        RC.incr(Key, 1)
                        RC.expire(Key, 300)
                        if int(RC.get(Key)) >3:
                            db_project = db_op.project_list
                            project = db_project.query.with_entities(distinct(db_project.project)).filter(
                                db_project.domain.like('%{}%'.format(domain))).all()
                            if project:
                                db_k8s_deploy = db_op.k8s_deploy
                                pod_name = db_k8s_deploy.query.with_entities(db_k8s_deploy.deployment).filter(
                                    db_k8s_deploy.project == project[0][0]).all()
                                if pod_name:
                                    pod_name = pod_name[0][0]
                                    text.append("服务可用率:{}%".format('%.2f' % (diff_vals * 100)))
                                    if rt_vals:
                                        text.append("服务响应时间:{}ms".format(int(float(rt_vals) * 1000)))
                                    delete_pod_key = 'op_auto_delete_pod_%s_%s' % (pod_name, td)
                                    if not RC.exists(delete_pod_key):
                                        text = auto_delete_pod(pod_name,text)
                                        tools.dingding_msg(text)
                                        RC.delete(Key)
        except Exception as e:
            logging.error(e)
    except Exception as e:
        logging.error(e)
    finally:
        db_op.DB.session.remove()
        for key in (k8s_domains_key,k8s_pv_key):
            RC.expire(key,864000)
        loging.write('complete %s !' %ingress_log.__name__)

@tools.proce_lock()
def Redis_alarm_task():
    loging.write("start %s ......" %Redis_alarm_task.__name__)
    # 检测redis异常
    def check_online(info):
        try:
            server_id, port, cluster, last_time = info
            if str(server_id) in server_ids:
                ip = server_ids[str(server_id)]
                hostname = hosts[str(server_id)]
                if tcpping(ip, port, timeout=3):
                    RC_CLUSTER.srem('op_redis_health_check', f"{hostname}:{port}")
                    db_redis.query.filter(and_(db_redis.server_id == server_id, db_redis.port == port)).update(
                        {db_redis.last_time: uptime})
                    db_idc.DB.session.commit()
                else:
                    if cluster == '否':
                        RC_CLUSTER.sadd('op_redis_health_check', f"{hostname}:{port}")
                        # 异常redis报警
                        if last_time == uptime:
                            key = f'op_redis_alarm_{hostname}_{port}'
                            RC.incr(key,1)
                            if int(RC.get(key)) >2:
                                text = ['**线上Redis服务报警:**',
                                        "Redis:%s %s" % (hostname, port),
                                        "服务端口检测异常!",
                                        '**请及时进行处理!**']
                                tools.dingding_msg(text)
                                RC.expire(key,360)
        except Exception as e:
            logging.error(e)
    def check_slave(info):
        server_id, sport, requirepass = info
        if str(server_id) in server_ids:
            sip = server_ids[str(server_id)]
            if sip not in blacklist and int(sport) not in black_port:
                try:
                    RC = redis.StrictRedis(sip, int(sport), decode_responses=True)
                    if requirepass:
                        RC = redis.StrictRedis(sip, int(sport), password=requirepass, decode_responses=True)
                except Exception as e:
                    logging.error(e)
                else:
                    info = RC.info()
                    if 'master_link_status' in info:
                        if  info['master_link_status'] != 'up':
                            text = ['**线上Redis同步报警:**',
                                    "Redis:%s:%s" % (sip, sport),
                                    "master_link_status:%s" %info['master_link_status'],
                                    '**请及时进行处理!**']
                            # redis异常报警
                            key = f'op_redis_alarm_{sip}_{sport}'
                            RC.incr(key,1)
                            if int(RC.get(key)) >2:
                                token = ops_token
                                if int(sport) in (8379, 6387, 17379):
                                    token = redis_token
                                tools.dingding_msg(text, token=token)
                                RC.expire(key,360)
    try:
        last_time = datetime.datetime.now()
        last_time = last_time - datetime.timedelta(days=3)
        last_time = last_time.strftime('%Y-%m-%d')
        uptime = time.strftime('%Y-%m-%d', time.localtime())
        db_servers = db_idc.idc_servers
        db_redis = db_idc.redis_info
        redis_infos = db_redis.query.with_entities(db_redis.server_id, db_redis.port,
                                                   db_redis.cluster, db_redis.last_time
                                                   ).filter(db_redis.last_time >= last_time).all()
        # 获取从redis列表
        Slaves = db_redis.query.with_entities(db_redis.server_id, db_redis.port,
                                              db_redis.requirepass).filter(
            and_(db_redis.slave == '是', db_redis.last_time >= last_time)).all()
        # 获取服务器信息
        blacklist = ('172.16.70.34', '172.16.19.104', '172.16.70.48', '54.69.57.114')
        black_port = [10080]
        server_infos = db_servers.query.with_entities(db_servers.id, db_servers.ip,db_servers.hostname).filter(db_servers.idc_id != 1025).all()
        server_ids = {str(infos[0]): infos[1] for infos in server_infos}
        hosts = {str(infos[0]): infos[-1] for infos in server_infos}
        pool = ThreadPool(10)
        pool.map(check_online, redis_infos)
        pool.map(check_slave, Slaves)
        pool.close()
        pool.join()
    finally:
        db_idc.DB.session.remove()
        loging.write("%s complete !" %Redis_alarm_task.__name__)

@tools.proce_lock()
def rsync_comment_task():
    try:
        #获取服务器信息
        db_server = db_idc.idc_servers
        db_third = db_idc.third_resource
        db_project = db_op.project_list
        server_list = db_server.query.with_entities(db_server.ip,db_server.ssh_port,db_server.hostname,db_server.comment).all()
        for list in server_list:
            try:
                comment = list[-1]
                hostname = list[2]
                if not list[-1]:
                    ip,ssh_port = list[0:2]
                    third_info = db_third.query.with_entities(distinct(db_third.resource_type)).filter(and_(db_third.ip==ip,db_third.ssh_port==ssh_port)).all()
                    if third_info:
                        third_info = [info[0] for info in third_info]
                    project_info = db_project.query.with_entities(distinct(db_project.project)).filter(and_(db_project.ip == ip, db_project.ssh_port == ssh_port)).all()
                    if project_info:
                        project_info = [info[0] for info in project_info]
                    comment = ','.join(project_info+third_info)
                if comment:
                    tools.modify_jumpserver_comment(hostname,comment)
            except:
                continue
    except Exception as e:
        logging.error(e)
    finally:
        db_idc.DB.session.remove()
        db_op.DB.session.remove()

@tools.proce_lock()
def kafka_topic():
    try:
        db_kafka = db_idc.kafka_topic
        kafka_client = KafkaClient(hosts=KAFKA_HOSTS)
        for Topic in [str(t,encoding='utf8') for t in kafka_client.topics]:
            try:
                offsets_prv = 0.0
                TOPIC = kafka_client.topics[Topic]
                Key = 'op_kafka_topic_health'
                new_offsets = []
                for id in TOPIC.partitions:
                    try:
                        new_offsets.append(TOPIC.partitions[id].latest_available_offset())
                    except:
                        continue
                if new_offsets:
                    new_offsets = reduce(lambda x, y: x + y, new_offsets)
                    old_offsets = new_offsets
                    if RC.hexists(Key,Topic):
                        old_offsets = float(RC.hget(Key,Topic))
                    if new_offsets >0 and old_offsets >0:
                        offsets_prv = float(new_offsets-old_offsets)/old_offsets*100
                        RC.hset(Key, Topic, new_offsets)
            except Exception as e:
                logging.error(e)
            else:
                #删除相关topic
                v = db_kafka.query.filter(db_kafka.topic==Topic).all()
                if v:
                    db_kafka.query.filter(db_kafka.topic == Topic).update({db_kafka.partitions:len(TOPIC.partitions),
                                                                           db_kafka.offsets_prv:offsets_prv,
                                                                           db_kafka.update_time:time.strftime(
                        '%Y-%m-%d %H:%M:%S', time.localtime())})
                    db_idc.DB.session.commit()
                else:
                    #记录新的topic
                    c = db_kafka(topic=Topic,partitions=len(TOPIC.partitions),offsets_prv=offsets_prv,
                                 update_time=time.strftime('%Y-%m-%d %H:%M:%S',time.localtime()))
                    db_idc.DB.session.add(c)
                    db_idc.DB.session.commit()
    except Exception as e:
        logging.error(e)
    finally:
        db_idc.DB.session.remove()

@tools.proce_lock(Host='172.16.68.13')
def zabbix_network_get():
    db_zabbix = db_idc.zabbix_info
    zapi = ZabbixAPI(url=zabbix_url, user=zabbix_user, password=zabbix_pw)
    dt = datetime.datetime.now()
    now_time = time.mktime(dt.timetuple())
    old_time = dt - datetime.timedelta(days=1)
    old_time = time.mktime(old_time.timetuple())
    try:
        result = zapi.host.get(monitored_hosts=1, output='extend')
        results = {infos['hostid']:infos['host'] for infos in result}
        hostids = [infos['hostid'] for infos in result]
        items = zapi.item.get(hostids=hostids, output=["hostid", "itemid"], search={"key_": 'net.if.'})
        for item in items:
            key = "op_zabbix_network_hostid_%s" %item["hostid"]
            RC_CLUSTER.lpush(key,item["itemid"])
        itemids = [info['itemid'] for info in items]
        vals = zapi.trend.get(itemids=itemids, time_from=old_time, time_till=now_time, output=["itemid", "value_max"])
        for val in vals:
            key = "op_zabbix_network_itemid_%s" %val["itemid"]
            RC_CLUSTER.lpush(key,val["value_max"])
        for hostid in results:
            hostname = results[hostid]
            key = "op_zabbix_network_hostid_%s" %hostid
            if RC_CLUSTER.exists(key):
                max_val = []
                for itemid in RC_CLUSTER.lrange(key,0,-1):
                    key = "op_zabbix_network_itemid_%s" %itemid
                    if RC_CLUSTER.exists(key):
                        max_val.extend(RC_CLUSTER.lrange(key,0,-1))
                if max_val:
                   max_val = [int(val) for val in max_val]
                   db_zabbix.query.filter(db_zabbix.hostname==hostname).update({db_zabbix.network:max(max_val)})
                   db_idc.DB.session.commit()
        for hostid in hostids:
            key = "op_zabbix_network_hostid_%s" % hostid
            RC_CLUSTER.delete(key)
        for itemid in itemids:
            key = "op_zabbix_network_itemid_%s" % itemid
            RC_CLUSTER.delete(key)
    except Exception as e:
       logging.error(e)
    finally:
       zapi.user.logout()
       db_idc.DB.session.remove()

#-*- coding: utf-8 -*-
import redis
from module import loging,SSH,db_idc,db_op,tools
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_,or_,distinct
from influxdb import InfluxDBClient
from collections import defaultdict
import datetime
import time
from elasticsearch import Elasticsearch
from functools import reduce
from multiprocessing.dummy import Pool as ThreadPool
from tcpping import tcpping
from kubernetes import client
app = Flask(__name__)
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/sql.conf')
app.config.from_pyfile('../conf/es.conf')
app.config.from_pyfile('../conf/tokens.conf')
logging = loging.Error()
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
config,contexts,config_file = tools.k8s_conf()
@tools.proce_lock()
def task_run():
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

    #获取k8s的hpa副本数量
    try:
        td = time.strftime('%Y-%m-%d',time.localtime())
        th = time.strftime('%H:%M',time.localtime())
        v1 = client.AutoscalingV1Api()
        ret = v1.list_horizontal_pod_autoscaler_for_all_namespaces()
        Key = 'op_hpa_chart_%s' %td
        for i in ret.items:
            RC.hset(Key,'%s_%s'%(i.metadata.name,th),i.status.current_replicas)
    except Exception as e:
        logging.error(e)

@tools.proce_lock()
def get_other_info():
    db_project_other = db_op.project_other
    db_crontabs = db_idc.crontabs
    db_servers = db_idc.idc_servers
    db_hosts = db_idc.hosts
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
                        update_date = time.strftime('%Y-%m-%d', time.localtime())
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
                                    business = db_project_other.query.with_entities(db_project_other.business_id).filter(and_(db_project_other.project == val,db_project_other.business_id != 0)).all()
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
def get_redis_info():
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
            if tcpping(host=ip, port=app_port, timeout=3):
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
                                            conf_file = "/usr/local/moji/redis/etc/{}".format(result.split('/')[-1])
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
                                                                 db_redis.Master_Host: master_id,db_redis.Master_Port: app_port,db_redis.update_date: update_date})
                                                            db_idc.DB.session.commit()
                                                        else:
                                                            c = db_redis(server_id=server_id, port=slave_port, masterauth=masterauth,
                                                                         requirepass=requirepass, master='否',
                                                                         slave='是',cluster='否', Master_host=master_id,
                                                                         Master_Port=app_port, update_date=update_date)
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
                                                 db_redis.Master_Port: '', db_redis.update_date: update_date})
                                            db_idc.DB.session.commit()
                                        else:
                                            loging.write("add new redis %s  %s  ......" % (ip, app_port))
                                            c = db_redis(server_id=server_id, port=app_port, masterauth=masterauth,
                                                         requirepass=requirepass, master=redis_type['master'],
                                                         slave=redis_type['slave'], cluster=redis_type['cluster'],
                                                         Master_host='', Master_Port='',
                                                         update_date=update_date)
                                            db_idc.DB.session.add(c)
                                            db_idc.DB.session.commit()
                                except:
                                    db_idc.DB.session.rollback()
                finally:
                    Ssh.Close()
            else:
                loging.write("delete not exist redis %s  %s  ......" %(ip,app_port))
                v = db_redis.query.filter(and_(db_redis.server_id==server_ids['%s:%s' %(ip,ssh_port)],db_redis.port==app_port)).all()
                for c in v:
                    db_idc.DB.session.delete(c)
                    db_idc.DB.session.commit()
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

@tools.proce_lock()
def k8s_health_check():
    v1 = client.CoreV1Api()
    try:
        #nodes健康检测
        ret = v1.list_node(watch=False)
        for i in ret.items:
            if 'node-role.kubernetes.io/master' in i.metadata.labels:
                node_type = 'master'
            else:
                node_type = 'node'
            status = i.status.conditions[-1].type
            if status != 'Ready':
                text = ['**容器平台NODE报警:%s**' % i.metadata.name,'节点类型:%s' %node_type,'节点状态:%s' %status,'需及时处理!']
                tools.dingding_msg(text,token=ops_token)
    except Exception as e:
        logging.error(e)
    try:
        # endpoints健康检测
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
                                        text = ['**容器平台endpoints报警:**', 'IP:%s' % info.ip,
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

@tools.proce_lock()
def alarm_load():
    try:
        loging.write("start %s ......" %alarm_load.__name__)
        whitelist = []
        dict_load = defaultdict()
        db_server = db_idc.idc_servers
        db_zabbix = db_idc.zabbix_info
        db_project = db_op.project_list
        db_project_other = db_op.project_other
        Influx_cli = InfluxDBClient(influxdb_host, influxdb_port, influxdb_user, influxdb_pw, 'zabbix_infos')
        host_infos = db_zabbix.query.with_entities(db_zabbix.ip, db_zabbix.ssh_port,db_zabbix.hostname,db_zabbix.update_time).filter(and_(db_zabbix.cpu_load > 100, db_zabbix.icmpping == 1)).all()
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
                except Exception as e:
                    logging.error(e)
                    continue
        #进行重启操作
        if dict_load:
            for hostname in dict_load:
                host,ssh_port,cpu_load = dict_load[hostname]
                # 判断ssh是否可以登录
                try:
                    Ssh = SSH.ssh(ip=host,ssh_port=ssh_port)
                except Exception as e:
                    if not hostname.startswith('nj'):
                        Ssh_Key = "op_ssh_login_fail_%s" %hostname
                        RC.incr(Ssh_Key,1)
                        RC.expire(Ssh_Key,350)
                        if int(RC.get(Ssh_Key)) >5:
                            tools.dingding_msg(text,token=ops_token)
                        else:
                            tools.dingding_msg(text)
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
                                        if pro_jar in ['moji-location-rpc.jar']:
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
                                                ops_token = None

                                        else:
                                            # 判断是否是jar项目
                                            server_id = db_server.query.with_entities(db_server.id).filter(db_server.hostname==hostname).all()
                                            if server_id[0]:
                                                ret = db_project_other.query.filter(db_project_other.server_id == int(server_id[0][0])).all()
                                                if ret:
                                                    text = ['**线上服务器预警:%s**' % hostname, "CPU持续{0}分钟平均使用率:{1}%".format(ctime,cpu_load),
                                                    "相关进程:{0}".format(Project), '**请及时进行处理!**']
                                        if text and not hostname.startswith('nj'):
                                            tools.dingding_msg(text,ops_token)
                                    except Exception as e:
                                        logging.error(e)
                    finally:
                        Ssh.Close()
    finally:
        loging.write("%s complete!" % alarm_load.__name__)
        db_idc.DB.session.remove()
        db_op.DB.session.remove()

@tools.proce_lock()
def k8s_ingress_log():
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
    Domains = []
    def auto_delete_pod(pod_name,text):
        try:
            namespace = "default"
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
            text.append('**自动处理问题pod数量:{}**'.format(counts))
            return text
    try:
        loging.write('start %s ......' % k8s_ingress_log.__name__)
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
                stat_vals = 0.0
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
                    if stat_vals >0:
                        diff_vals = float(stat_vals)/float(total_vals)
                        rt_vals = RC.hget('%s_%s_%s' % (rt_key, domain, td), th)
                        if diff_vals < 0.99:
                            Key = 'op_k8s_project_alarm'
                            RC.incr(Key, 1)
                            RC.expire(Key, 180)
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
        loging.write('complete %s !' % k8s_ingress_log.__name__)

@tools.proce_lock()
def Redis_alarm():
    loging.write("start %s ......" %Redis_alarm.__name__)
    tm = time.strftime('%Y%m%d%H%M',time.localtime())
    Key = 'yw_check_master_slave'
    redis_m = []
    db_servers = db_idc.idc_servers
    db_redis = db_idc.redis_info
    try:
        #获取服务器信息
        blacklist = ('172.16.70.34','172.16.19.104')
        server_ids = db_servers.query.with_entities(db_servers.id, db_servers.ip).filter(db_servers.idc_id != 1025).all()
        server_ids = {str(infos[0]): infos[-1] for infos in server_ids}
        #获取主redis信息
        Masters = db_redis.query.with_entities(db_redis.server_id,db_redis.port,db_redis.requirepass).filter(db_redis.master=='是').all()
        S_Masters = db_redis.query.with_entities(db_redis.Master_Host, db_redis.Master_Port).filter(and_(db_redis.slave == '是',db_redis.Master_Host !='')).all()
        S_Masters = set(['%s:%s' %info for info in S_Masters])
        #主redis写入数据
        for Master in set(Masters):
            server_id, port, requirepass = Master
            try:
                mip = server_ids[str(server_id)]
            except:
                continue
            try:
                RC = redis.StrictRedis(mip, int(port), decode_responses=True)
                if requirepass:
                    RC = redis.StrictRedis(mip, int(port), password=requirepass, decode_responses=True)
            except:
                continue
            else:
                RC.set(Key, tm)
                RC.expire(Key, 360)
                redis_m.append((int(server_id),int(port)))
        def check_slave(info):
            #检查从reids是否同步
            server_id,port = info
            if int(port) not in [10080]:
                #获取从redis端口列表
                slave_ports = db_redis.query.with_entities(distinct(db_redis.port)).filter(and_(db_redis.Master_Host==server_id,db_redis.Master_Port==port)).all()
                if slave_ports:
                    slave_ports = [int(sport[0]) for sport in slave_ports]
                    for slave_port in slave_ports:
                        #获取从redis信息
                        redis_lists = db_redis.query.with_entities(db_redis.server_id,db_redis.port,db_redis.requirepass).filter(and_(db_redis.slave=='是',db_redis.port==slave_port)).all()
                        for info in redis_lists:
                            text = None
                            slave_lists = []
                            server_id,sport,requirepass = info
                            try:
                                sip = server_ids[str(server_id)]
                            except:
                                continue
                            else:
                                try:
                                    RC = redis.StrictRedis(sip, int(sport), decode_responses=True)
                                    if requirepass:
                                        RC = redis.StrictRedis(sip, int(sport), password=requirepass, decode_responses=True)
                                except:
                                    continue
                                else:
                                    #获取从redis时间戳
                                    mvals = db_redis.query.with_entities(db_redis.Master_Host, db_redis.Master_Port).filter(and_(db_redis.server_id == server_id, db_redis.port == sport)).all()
                                    mip,mport = mvals[0]
                                    mip = server_ids[str(mip)]
                                    val = RC.get(Key)
                                    try:
                                        RC = redis.StrictRedis(mip, int(mport), decode_responses=True)
                                        if requirepass:
                                            RC = redis.StrictRedis(mip, int(mport), password=requirepass,
                                                                   decode_responses=True)
                                    except:
                                        continue
                                    else:
                                        if sip not in blacklist:
                                            mval = RC.get(Key)
                                            if mval and not val:
                                                text = ['**线上Redis同步报警:**',
                                                        "同步Redis:%s:%s 验证数据:%s"%(mip,mport,mval),
                                                        "延时Redis:%s:%s 验证数据:%s" % (sip, sport,val),
                                                        "数据同步异常!",
                                                        '**请及时进行处理!**']
                            if text:
                                alarm_info = '%s:%s' % (server_id, sport)
                                #判断节点redis
                                if alarm_info in S_Masters:
                                    vals = db_redis.query.with_entities(db_redis.server_id,db_redis.port).filter(and_(db_redis.Master_Host==server_id,db_redis.Master_Port==sport)).all()
                                    if vals:
                                        slave_lists.extend(['%s:%s'%val for val in vals])
                                if alarm_info not in slave_lists:
                                    #redis异常报警
                                    token = ops_token
                                    if int(sport) in (8379,6387,17379):
                                        token = redis_token
                                    tools.dingding_msg(text,token=token)
        if redis_m:
            time.sleep(60)
            pool = ThreadPool(5)
            pool.map(check_slave,set(redis_m))
            pool.close()
            pool.join()
    finally:
        db_idc.DB.session.remove()
        loging.write("%s complete !" % Redis_alarm.__name__)

@tools.proce_lock()
def rsync_comment():
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
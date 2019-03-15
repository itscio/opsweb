#-*- coding: utf-8 -*-
import redis
from Modules import loging,Mysql,check,SSH,db_idc,db_op,tools
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_,or_,distinct
from influxdb import InfluxDBClient
from collections import defaultdict
import datetime
import time
from functools import reduce
from multiprocessing.dummy import Pool as ThreadPool
from tcpping import tcpping
from kubernetes import client
app = Flask(__name__)
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/sql.conf')
logging = loging.Error()
DB = SQLAlchemy(app)
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
RC = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
redis_data = app.config.get('REDIS_DATA')
RC_CLUSTER = redis.StrictRedis(host=redis_data, port=redis_port,decode_responses=True)
MYSQL_HOST = app.config.get('MYSQL_HOST')
MYSQL_PORT = app.config.get('MYSQL_PORT')
MYSQL_USER = app.config.get('MYSQL_USER')
MYSQL_PW = app.config.get('MYSQL_PASSWORD')
MYSQL_INFO_USER = app.config.get('MYSQL_INFO_USER')
MYSQL_INFO_PW = app.config.get('MYSQL_INFO_PASSWORD')
influxdb_host = app.config.get('INFLUXDB_HOST')
influxdb_port = app.config.get('INFLUXDB_PORT')
influxdb_user = app.config.get('INFLUXDB_USER')
influxdb_pw = app.config.get('INFLUXDB_PASSWORD')
influxdb_db = app.config.get('INFLUXDB_DB')
config,contexts,config_file = tools.k8s_conf()
@check.proce_lock
def get_mysqldb_info():
    try:
        db_third = db_idc.third_resource
        db_mysqldb = db_idc.idc_mysqldb
        IDC_MySql = Mysql.MYSQL(MYSQL_USER, MYSQL_PW, MYSQL_HOST, MYSQL_PORT, 'idc')
        IDC_MySql.Run("TRUNCATE TABLE tableinfo;")
        infos = IDC_MySql.Run("select ip,port from mysqldb where master = '是' or slave = '是';")
    except Exception as e:
        logging.error(e)
    else:
        for info in infos:
            ip,port = info
            try:
                INFO_MySql = Mysql.MYSQL(MYSQL_INFO_USER, MYSQL_INFO_PW, ip, port, 'mysql')
                exclude_db = ('mysql', 'test', 'information_schema', 'performance_schema')
                cmd = "show databases;"
                Lists = INFO_MySql.Run(cmd)
                Lists = [db[0] for db in Lists if db[0] not in exclude_db]
                db_lists = ','.join(Lists)
            except:
                continue
            else:
                try:
                    cmd = "SHOW SLAVE STATUS;"
                    result = INFO_MySql.Run(cmd)
                    if result:
                        result = list(result[0])
                        m_ip = result[1].strip()
                        m_user = result[2].strip()
                        m_port = result[3]
                        s_io = result[10].strip()
                        s_sql = result[11].strip()
                        #判断获取的master主机信息是否需要解析
                        if len(m_ip.split('.')) != 4:
                            ssh_port = db_third.query.with_entities(db_third.ssh_port).filter(and_(db_third.ip==ip,db_third.app_port==port)).all()
                            ssh_port = ssh_port[0][0]
                            Ssh = SSH.ssh(ip=ip, ssh_port=ssh_port)
                            ssh_cmd = "/bin/cat /etc/hosts|/bin/grep {0}".format(str(m_ip))
                            values = Ssh.Run(ssh_cmd)
                            if values['stdout']:
                                m_ip = values['stdout'][0].split()[0]
                            else:
                                m_ip = None
                        if m_ip:
                            if s_io == 'Yes' and s_sql == 'Yes':
                                #判断真实的主库服务器信息
                                values = db_mysqldb.query.with_entities(db_mysqldb.Master_Host,db_mysqldb.Master_Port).filter(
                                    and_(db_mysqldb.ip == m_ip, db_mysqldb.port == m_port,db_mysqldb.slave == '是')).all()
                                if values:
                                    m_ip,m_port = values[0]
                                cmd = "update mysqldb set slave='是',master='否',db='%s',Master_Host='%s',Master_Port='%s',Master_User='%s' where ip='%s' and port=%i;" % \
                                      (db_lists, m_ip, m_port, m_user, ip, int(port))
                            else:
                                check_cmd = "show slave hosts;"
                                check_result = IDC_MySql.Run(check_cmd)
                                if check_result:
                                    cmd = "update mysqldb set slave='否',master='是',db='%s',Master_Host='',Master_Port='',Master_User='' where ip='%s' and port=%i;" % (
                                    db_lists, ip, int(port))
                    else:
                        cmd = "update mysqldb set slave='否',master='是',db='%s',Master_Host='',Master_Port='',Master_User='' where ip='%s' and port=%i;" % (
                        db_lists, ip, int(port))
                    IDC_MySql.Run(cmd)
                except Exception as e:
                    INFO_MySql.Close()
                    logging.error(e)
                try:
                    version = INFO_MySql.Run("show variables like 'version';")
                    version = version[0][-1]
                    for db in Lists:
                        cmd = "SHOW TABLE STATUS from %s;" % db
                        results = INFO_MySql.Run(cmd)
                        if results:
                            for result in results:
                                table_name = result[0]
                                table_engine = result[1]
                                table_Rows = int(result[4])
                                table_size = int(result[6]) + int(result[8])
                                if len(str(table_size)) > 9:
                                    table_size = '%sGB' % (table_size / 1000 / 1000 / 1000)
                                elif len(str(table_size)) > 6:
                                    table_size = '%sMB' % (table_size / 1000 / 1000)
                                else:
                                    table_size = '%sKB' % (table_size / 1000)
                                table_charset = result[14]
                                cmd = "insert into tableinfo (ip, port, database_name, table_name, Engine_name, Rows,size,Charset, version,update_time) VALUES ('%s',%i,'%s','%s','%s',%i,'%s','%s','%s',now());" % \
                                      (ip, int(port), db, table_name, table_engine, table_Rows, table_size, table_charset, version)
                                IDC_MySql.Run(cmd)
                except Exception as e:
                    logging.error(e)
                INFO_MySql.Close()
    finally:
        IDC_MySql.Close()
        db_idc.DB.session.remove()

@check.proce_lock
def task_run():
    try:
        try:
            # 获取业务访问数据
            db_business = db_op.business
            db_project = db_op.project_list
            business = db_business.query.with_entities(db_business.id, db_business.business).all()
            business = {busi[0]: busi[1] for busi in business}
            year = time.strftime('%Y', time.localtime())
            ot = datetime.datetime.now() - datetime.timedelta(days=0)
            ot = ot.strftime('%Y-%m-%dT00:00:00Z')
            Key = 'op_business_pv_%s' % ot.split('T')[0]
            Influx_cli = InfluxDBClient(influxdb_host, influxdb_port, influxdb_user, influxdb_pw, 'analysis_logs')
            for id in business:
                business_domain = db_project.query.with_entities(distinct(db_project.domain)).filter(
                    db_project.business_id == int(id)).all()
                if business_domain:
                    hosts = [domain[0] for domain in business_domain]
                    pv_sum = []
                    for host in hosts:
                        if ',' in host:
                            hosts.extend(host.split(','))
                        else:
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
                    if pv_sum:
                        pv_sum = reduce(lambda x, y: x + y, pv_sum)
                        RC_CLUSTER.hset(Key, business[id], pv_sum)
        except Exception as e:
            logging.error(e)

        #获取数据库状态
        now_date = datetime.datetime.now()
        gd = now_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        influx_fields = defaultdict()
        db_mysqldb = db_idc.idc_mysqldb
        infos = db_mysqldb.query.with_entities(db_mysqldb.ip,db_mysqldb.port).filter(or_(db_mysqldb.master == '是',db_mysqldb.slave == '是')).all()
        Influx_cli = InfluxDBClient(influxdb_host, influxdb_port, influxdb_user, influxdb_pw,'mysqld_status')
        for info in infos:
            try:
                ip, port = info
                MySql = Mysql.MYSQL(MYSQL_INFO_USER, MYSQL_INFO_PW, ip, port, 'mysql')
                vals = MySql.Run("SHOW GLOBAL STATUS;")
            except:
                continue
            else:
                if vals:
                    vals = {val[0]: val[1] for val in vals}
                    #获取QPS
                    Key = 'op_mysqld_QPS_%s_%s' %(ip,port)
                    QPS = RC.getset(Key, int(vals['Questions']))
                    RC.expire(Key,3600)
                    if not QPS:
                        QPS = int(vals['Questions'])
                    influx_fields['QPS'] = float(int(vals['Questions']) - int(QPS)) / 3000
                    #获取TPS
                    Key = 'op_mysqld_TPS_%s_%s' % (ip, port)
                    TPS = RC.getset(Key, int(vals['Com_commit']) + int(vals['Com_rollback']))
                    RC.expire(Key,3600)
                    if not TPS:
                        TPS = int(vals['Com_commit']) + int(vals['Com_rollback'])
                    influx_fields['TPS'] = float(int(vals['Com_commit']) + int(vals['Com_rollback']) - int(TPS)) / 3000
                    #获取读写比
                    influx_fields['R/W'] = (int(vals['Com_select']) + int(vals['Qcache_hits'])) / (float(int(vals['Com_insert']) +int(vals['Com_update']) + int(vals['Com_delete']) + int(vals['Com_replace']))) * 100
                    #获取慢查询占比
                    influx_fields['S/Q'] = float(vals['Slow_queries']) / int(vals['Questions']) * 100
                    #获取接受流量
                    Key = 'op_mysqld_Bytes_received_%s_%s' % (ip, port)
                    Bytes_received =RC.getset(Key, int(vals['Bytes_received']))
                    RC.expire(Key,3600)
                    if not Bytes_received:
                        Bytes_received = int(vals['Bytes_received'])
                    influx_fields['Bytes_r'] = float((int(vals['Bytes_received']) - int(float(Bytes_received))))/1000
                    #获取发送流量
                    Key = 'op_mysqld_Bytes_sent_%s_%s' % (ip, port)
                    Bytes_sent =RC.getset(Key, float(vals['Bytes_sent']))
                    RC.expire(Key,3600)
                    if not Bytes_sent:
                        Bytes_sent = int(vals['Bytes_sent'])
                    influx_fields['Bytes_s'] = (int(vals['Bytes_sent']) - int(float(Bytes_sent)))/1000
                    #获取连接数
                    influx_fields['Connections'] = len(MySql.Run("SHOW processlist;"))
                    # 写入influxdb数据库
                    if influx_fields:
                        try:
                            json_body = [{"measurement": "performance", "tags": {"ip": ip, "port":port},
                                          "fields": influx_fields, "time": gd}]
                            Influx_cli.write_points(json_body)
                        except Exception as e:
                            logging.error(e)
                MySql.Close()
    except Exception as e:
        logging.error(e)
    finally:
        db_idc.DB.session.remove()
        db_op.DB.session.remove()
    #获取k8s的hpa副本数量
    try:
        td = time.strftime('%Y-%m-%d',time.localtime())
        th = time.strftime('%H:%M',time.localtime())
        v1 = client.AutoscalingV1Api()
        ret = v1.list_horizontal_pod_autoscaler_for_all_namespaces()
        Key = 'op_hpa_chart_%s' %td
        for i in ret.items:
            RC.hset(Key,'%s_%s'%(i.spec.scale_target_ref.name,th),i.status.current_replicas)
    except Exception as e:
        logging.error(e)
@check.proce_lock
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
                    update_date = time.strftime('%Y-%m-%d', time.localtime())
                    Ssh = SSH.ssh(ip=ip, ssh_port=ssh_port)
                    #收集crontab信息
                    results = Ssh.Run("cat /var/spool/cron/*")
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
                                c = db_crontabs(cron=cron,action=action,server_id=int(server_id),update_time=update_date)
                                db_idc.DB.session.add(c)
                                db_idc.DB.session.commit()
                    # 收集jar运行信息
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
                                c = db_project_other(lable='java', project=val, server_id=server_id,business_id=0, update_time=update_date)
                                db_op.DB.session.add(c)
                                db_op.DB.session.commit()
                    #收集hosts信息
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
                                            c = db_hosts(line[0],line[1],server_id=server_id,update_time=update_date)
                                            db_idc.DB.session.add(c)
                                            db_idc.DB.session.commit()
                                    if len(line) > 2:
                                        for hostname in line[1:]:
                                            if not hostname.startswith('#') and not 'localhost' in  hostname:
                                                c = db_hosts(line[0],hostname, server_id=server_id,
                                                             update_time=update_date)
                                                db_idc.DB.session.add(c)
                                                db_idc.DB.session.commit()
                    Ssh.Close()
                except Exception as e:
                    logging.error(e)
                    continue
    except Exception as e:
        logging.error(e)
    finally:
        db_idc.DB.session.remove()
        db_op.DB.session.remove()

@check.proce_lock
def get_redis_info():
    db_third = db_idc.third_resource
    db_redis = db_idc.redis_info
    db_servers = db_idc.idc_servers
    update_date = time.strftime('%Y-%m-%d', time.localtime())
    try:
        server_ids = db_servers.query.with_entities(db_servers.id,db_servers.ip,db_servers.ssh_port,db_servers.hostname).all()
        for infos in server_ids:
            RC_CLUSTER.hset('op_server_hostnames',infos[0],infos[-1])
        server_ids = {"%s:%s"%(infos[1],infos[2]):infos[0] for infos in server_ids}
        redis_list = db_third.query.with_entities(db_third.ip,db_third.ssh_port,db_third.app_port).filter(db_third.resource_type == 'redis').all()
        ssh_ports = {"%s:%s" %(infos[0],infos[2]):infos[1] for infos in redis_list}
        for ip,ssh_port,app_port in set(redis_list):
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
                                            conf_file = "/usr/local/redis/etc/{}".format(result.split('/')[-1])
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
                                        RC = redis.StrictRedis(ip,int(app_port),password=requirepass,decode_responses=True)
                                        Infos = RC.info()
                                        if Infos['role'] == 'master':
                                            redis_type['master'] = '是'
                                        if Infos['role'] == 'slave':
                                            redis_type['slave'] = '是'
                                        counts = int((Infos['connected_slaves']))
                                    except Exception as e:
                                        logging.error(e)
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
                                                        except:
                                                            server_id = slave_ip
                                                        else:
                                                            try:
                                                                server_id = server_ids['%s:%s' %(slave_ip,SSH_port)]
                                                            except:
                                                                server_id = slave_ip
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
                                        except Exception as e:
                                            db_idc.DB.session.rollback()
                                            logging.error(e)
                                try:
                                    #修改记录master或者cluster信息
                                    if redis_type['master'] == '是' or redis_type['cluster'] == '是':
                                        try:
                                            server_id = server_ids['%s:%s' % (ip, ssh_port)]
                                        except:
                                            server_id = ip
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
                                            c = db_redis(server_id=server_id, port=app_port, masterauth=masterauth,
                                                         requirepass=requirepass, master=redis_type['master'],
                                                         slave=redis_type['slave'], cluster=redis_type['cluster'],
                                                         Master_host='', Master_Port='',
                                                         update_date=update_date)
                                            db_idc.DB.session.add(c)
                                            db_idc.DB.session.commit()
                                except Exception as e:
                                    db_idc.DB.session.rollback()
                                    logging.error(e)
                except Exception as e:
                    logging.error(e)
                    continue
                finally:
                    Ssh.Close()
            else:
                loging.write("delete not exist redis %s  %s  ......" %(ip,app_port))
                v = db_redis.query.filter(and_(or_(db_redis.server_id==server_ids['%s:%s' %(ip,ssh_port)],
                                                   db_redis.server_id == ip),db_redis.port==app_port)).all()
                for c in v:
                    db_idc.DB.session.delete(c)
                    db_idc.DB.session.commit()
    except Exception as e:
        logging.error(e)
    finally:
        db_idc.DB.session.remove()

@check.proce_lock
def get_redis_status():
    db_redis = db_idc.redis_info
    db_servers = db_idc.idc_servers
    update_date = time.strftime('%Y-%m-%d', time.localtime())
    try:
        server_ids = db_servers.query.with_entities(db_servers.id,db_servers.ip,db_servers.hostname).all()
        redis_infos = db_redis.query.with_entities(db_redis.server_id,db_redis.port,db_redis.requirepass).filter(db_redis.cluster=='否').all()
        def redis_status(infos):
            try:
                ips = {int(infos[0]): infos[1] for infos in server_ids}
                hostnames = {int(infos[0]): infos[-1] for infos in server_ids}
                server_id,app_port,requirepass = infos
                host = ips[int(server_id)]
            except:
                pass
            else:
                try:
                    Key = 'op_redis_status_%s_%s_%s' % (hostnames[int(server_id)], app_port, update_date)
                    RC = redis.StrictRedis(host, int(app_port), password=requirepass,decode_responses=True)
                    Infos = RC.info()
                    clients = Infos['connected_clients']
                    r_clients = RC_CLUSTER.hget(Key,'clients')
                    if r_clients:
                        if int(r_clients) > int(clients):
                            clients = r_clients
                    keyspace_hits = Infos['keyspace_hits']
                    keyspace_misses = Infos['keyspace_misses']
                    hit_rate = "%.1f" %(float(keyspace_hits)/(int(keyspace_hits)+int(keyspace_misses))*100)
                    r_hit_rate = RC_CLUSTER.hget(Key,'hit_rate')
                    if r_hit_rate:
                        if int(r_hit_rate) > int(hit_rate):
                            hit_rate = r_hit_rate
                    ops = Infos['instantaneous_ops_per_sec']
                    r_ops = RC_CLUSTER.hget(Key,'ops')
                    if r_ops:
                        if int(r_ops) > int(ops):
                            ops = r_ops
                    used_memory = Infos['used_memory_human']
                    r_used_memory = RC_CLUSTER.hget(Key,'used_memory')
                    if r_used_memory:
                        if int(r_used_memory) > int(used_memory):
                            used_memory = r_used_memory
                    RC_CLUSTER.hmset(Key,{'clients':clients,'hit_rate':hit_rate,'ops':ops,'used_memory':used_memory})
                    RC_CLUSTER.expire(Key,604800)
                except:
                    pass
        pool = ThreadPool(5)
        pool.map(redis_status, redis_infos)
        pool.close()
        pool.join()
    except Exception as e:
        logging.error(e)

@check.proce_lock
def alarm_load():
    try:
        db_zabbix = db_idc.zabbix_info
        db_project = db_op.project_list
        zabi = tools.zabbix_api()
        redis_key = 'op_alarm_load_hosts'
        token = ""
        host_infos = db_zabbix.query.with_entities(db_zabbix.ip, db_zabbix.ssh_port,db_zabbix.hostname,db_zabbix.update_time).filter(and_(db_zabbix.cpu_load > 100, db_zabbix.icmpping == 1)).all()
        #循环监控疑似问题服务器
        for infos in host_infos:
            try:
                host,ssh_port,hostname,update_time=infos
                loads = []
                Projects = []
                Others = []
                #获取zabbix监控数据
                if time.strftime('%Y-%m-%d',time.localtime()) in update_time:
                    for key_ in ('system.cpu.load[all,avg5]', 'system.cpu.num'):
                        val = zabi.zabbix_history(hostname, key_)
                        if not val:
                            val = zabi.zabbix_history(host, key_)
                            if not val:
                                val = 0
                        loads.append(float(val))
                    if loads[0] > 0 and loads[1] > 0:
                        load = loads[0] / loads[1] * 100
                        if load >100:
                            Key = '%s:%s:%s' %(host,hostname,ssh_port)
                            RC.hincrby(redis_key,Key)
                            #符合条件后进行重启操作
                            if int(RC.hget(redis_key,Key)) >9:
                                #判断是否是java程序
                                ret = db_project.query.filter(and_(db_project.ip==host,db_project.ssh_port==ssh_port)).all()
                                if ret:
                                    try:
                                        Ssh = SSH.ssh(ip=host,ssh_port=ssh_port)
                                    except Exception as e:
                                        logging.error(e)
                                    else:
                                        #筛查可重启服务进程
                                        results = Ssh.Run("ps -aux | sort -k3nr |head -n 1")
                                        if results['stdout']:
                                            results = results['stdout'][0].strip().split()
                                            if results[-1].endswith('-rpc.jar'):
                                                pro_jar = results[-1]
                                                if pro_jar in ['moji-location-rpc.jar']:
                                                    Projects.append(pro_jar.split('.')[0])
                                                else:
                                                    Others.append(pro_jar.split('.')[0])
                                            else:
                                                for line in results:
                                                    if '-Dcatalina.home=' in line :
                                                        Projects.append(line.strip().split('/')[-1])
                                                        break
                                            if Projects:
                                                for project in Projects:
                                                    #重启问题tomcat
                                                    result = Ssh.Run("supervisorctl  restart  {0}".format(project))
                                                    if result['stderr']:
                                                        text = ['**线上服务重启:%s**' % host, "CPU持续使用率:{0}%".format(load),
                                                                "相关进程:{0}".format(project), '**服务重启失败,需手动处理!**']
                                                        tools.dingding_msg(text, alart_token=token)
                                                    else:
                                                        text = ['**线上服务重启:%s**' % host, "CPU持续使用率:{0}%".format(load),
                                                                "相关进程:{0}".format(project), '**服务重启成功!**']
                                                        tools.dingding_msg(text)
                                            else:
                                                project = ' '.join(results[10:])
                                                if Others:
                                                    project = Others[0]
                                                text = ['**线上服务器预警:%s**' % host, "CPU持续使用率:{0}%".format(load),
                                                            "相关进程:{0}".format(project), '**请及时进行处理!**']
                                                tools.dingding_msg(text,alart_token=token)
                                    finally:
                                        Ssh.Close()
            except Exception as e:
                logging.error(e)
        RC.hincrby(redis_key, 'count')
        if int(RC.hget(redis_key, 'count')) >9:
            RC.delete(redis_key, )
    except Exception as e:
        logging.error(e)
    finally:
        db_idc.DB.session.remove()
        db_op.DB.session.remove()

#-*- coding: utf-8 -*-
from random import choice
import string
import mysql_scheduler
from multiprocessing.dummy import Pool
import  Mysql
import urllib
import json
import socket
import loging
import pytz
from rediscluster import RedisCluster
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
import time,datetime
import Task
import check
import SSH
import redis
import __init__
app = __init__.app
HOST = socket.gethostbyname(socket.gethostname())
IPS = app.config.get('INIT_IPS')
CMDS = app.config.get('INIT_CMDS')
init_key = app.config.get('INIT_KEY')
INIT_USER = app.config.get('INIT_USER')
nodes = app.config.get('NODES_PRODUCE')
sms_url = app.config.get('SMS_URL')
task_servers = app.config.get('TASK_SERVERS')
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
Redis = redis.StrictRedis(host=redis_host, port=redis_port)
RC = RedisCluster(startup_nodes=nodes, decode_responses=True)
jobstores = {'default': SQLAlchemyJobStore(url=app.config.get('SQLALCHEMY_BINDS')['op'])}
scheduler = BackgroundScheduler({'apscheduler.job_defaults.max_instances': '5','apscheduler.job_defaults.coalesce': 'false'})
scheduler.configure(jobstores=jobstores,timezone=pytz.timezone('Asia/Shanghai'))
def Produce(length=8,chars=string.ascii_letters+string.digits):
    return ''.join([choice(chars) for i in range(length)])
def Async_log(user,url):
    if 'op.baihe.com' in url:
        mysql_op_log = Mysql.mysql_op(user, url)
        Proc = Pool()
        def Run():
            mysql_op_log.op_log()
        Proc.apply_async(Run)
        Proc.close()
        Proc.join()
@check.proce_lock
def auto_init_system():
    for ip in Redis.lpop(init_key):
        try:
            ssh = SSH.ssh(username=INIT_USER,ip=ip)
            for cmd in CMDS:
                results = ssh.Run(cmd)
                if not results['stderr']:
                    loging.write('init %s system start ......' % ip)
                    ip_list = ip.split('.')
                    hostname = 'S%s-%s.server.baihe' % (ip_list[2], ip_list[3])
                    for h in ('45', '46'):
                        Redis.lpush('clear%s_salt-minon' % h, hostname)
            ssh.Close()
        except:
            pass
def send_sms(mobile=None,content=None):
    t = time.strftime("%H:%M", time.localtime())
    if isinstance(mobile,str):
        Mobile = [mobile,]
    elif isinstance(mobile,list):
        Mobile = mobile
    else:
        return 'mobile type error!'
    for mobile in Mobile:
        params = {"content":"{0} {1}".format(content,t),"mobile":mobile,"appKey":"800"}
        params = json.dumps(params)
        params = urllib.quote(params)
        data = "traceID=123&systemID=123&serviceName=op.alarm.sms&params=%s" %params
        try:
            values = urllib.urlopen(sms_url,data)
            fd = values.read()
        except Exception as e:
            return e
    return json.loads(fd)
#定时任务执行
def scheduler_tasks():
    scheduler.add_job(check.scheduler_lock, 'cron', second='*/3', id='scheduler_lock', replace_existing=True)
    scheduler.add_job(Task.kafka_internet,'cron',second = '0',minute = '*',id='kafka_internet',replace_existing=True)
    scheduler.add_job(Task.kafka_intranet, 'cron', second='0', minute='*', id='kafka_intranet', replace_existing=True)
    scheduler.add_job(Task.task_tables_info, 'cron', second='0', minute='*/30',hour='8-20',id='task_tables_info', replace_existing=True)
    scheduler.add_job(mysql_scheduler.mysql_scheduler,'cron', second='0', minute='*/30',hour='1-6', id='mysql_scheduler', replace_existing=True)
    scheduler.add_job(Task.check_publish, 'cron', second='0', minute='*/5',hour='10-18',id='check_publish',replace_existing=True)
    scheduler.add_job(Task.clear_kestrel, 'cron', second='0', minute='0', hour='2', id='clear_kestrel',replace_existing=True)
    scheduler.add_job(Task.get_twemproxy_redis, 'cron', second='0', minute='*/3',hour='8-20', id='get_twemproxy_redis',replace_existing=True)
    scheduler.add_job(Task.zabbix_api_lvs, 'cron', second='0', minute='*',id='zabbix_api_lvs', replace_existing=True)
    scheduler.add_job(Task.zabbix_api_host, 'cron', second='0', minute='*/30',id='zabbix_api_host', replace_existing=True)
    scheduler.add_job(Task.kestel_info, 'cron', second='0', minute='0',hour='*',id='kestrel_info', replace_existing=True)
    scheduler.add_job(Task.haproxy_blacklist, 'cron', second='*/30', minute='*', id='haproxy_blacklist', replace_existing=True)
    scheduler.add_job(Task.vpn_conf, 'cron', second='0', minute='*', id='vpn_conf',replace_existing=True)
    scheduler.add_job(Task.WAF, 'cron', second='0', minute='*', id='WAF', replace_existing=True)
    scheduler.add_job(Task.WAF2, 'cron', second='0', minute='*', id='WAF2', replace_existing=True)
    scheduler.add_job(Task.WAF3, 'cron', second='0', minute='*', id='WAF3', replace_existing=True)
    scheduler.add_job(Task.mysql_backup, 'cron', second='0', minute='*/30',hour='20-23', id='mysql_backup', replace_existing=True)
    scheduler.add_job(auto_init_system, 'cron', second='0', minute='*/30',hour='8-18',id='auto_init_system', replace_existing=True)
    scheduler.add_job(Task.del_zabbix_events, 'cron', second='*/30',minute='*', id='del_zabbix_events', replace_existing=True)
    scheduler.add_job(Task.redis_cluster_info, 'cron', second='0', minute='*', id='redis_cluster_info',replace_existing=True)
    scheduler.start()
#上线执行
class Scheduler_publish(object):
    def __init__(self):
        self.run_date = datetime.datetime.now() + datetime.timedelta(seconds=3)
        self.run_date = self.run_date.strftime('%Y-%m-%d %H:%M:%S')
        self.tm = time.strftime('%Y%m%d%H%M',time.localtime())
        self.scheduler = BackgroundScheduler({'apscheduler.job_defaults.max_instances': '5'})
        self.scheduler.configure(timezone=pytz.timezone('Asia/Shanghai'))
    def Scheduler_mem(self,func,publish_key = 'None',taskKey = 'None'):
        self.scheduler.add_job(func,'date', run_date=self.run_date,args=[publish_key,taskKey],id='%s_%s'%(taskKey,self.tm),replace_existing=False)
        return self.scheduler
#后台执行
class Scheduler_backgroud(object):
    def __init__(self):
        self.run_date = datetime.datetime.now() + datetime.timedelta(seconds=3)
        self.run_date = self.run_date.strftime('%Y-%m-%d %H:%M:%S')
        self.scheduler = BackgroundScheduler({'apscheduler.job_defaults.max_instances': '15'})
        self.scheduler.configure(timezone=pytz.timezone('Asia/Shanghai'))
    def Run(self):
        if HOST in task_servers:
            self.scheduler.add_job(Task.analytics_internet_logs, 'date', run_date=self.run_date,id='analytics_internet_logs', replace_existing=True)
            self.scheduler.add_job(Task.analytics_internet2_logs, 'date', run_date=self.run_date,id='analytics_internet2_logs', replace_existing=True)
            self.scheduler.add_job(Task.analytics_internet3_logs, 'date', run_date=self.run_date,id='analytics_internet3_logs', replace_existing=True)
            self.scheduler.add_job(Task.analytics_intranet_logs, 'date', run_date=self.run_date,id='analytics_intranet_logs',replace_existing=True)
            self.scheduler.add_job(Task.analytics_intranet2_logs, 'date', run_date=self.run_date,id='analytics_intranet2_logs', replace_existing=True)
            self.scheduler.add_job(Task.WAF_logs, 'date', run_date=self.run_date,id='WAF_logs',replace_existing=True)
            self.scheduler.add_job(Task.httpry_logs,'date', run_date=self.run_date,id='httpry_logs', replace_existing=True)
            self.scheduler.start()
            loging.write('Scheduler_run start......')
        else:
            loging.write('%s not in task server list!' %HOST)
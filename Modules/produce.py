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
import time
import analytics_logs
import Task
import check
import __init__
app = __init__.app
HOST = socket.gethostbyname(socket.gethostname())
nodes = app.config.get('NODES_PRODUCE')
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
def send_sms(mobile=None,content=None):
    t = time.strftime("%H:%M", time.localtime())
    url = 'http://emg.baihe.com/inner/sms/send.json'
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
            values = urllib.urlopen(url,data)
            fd = values.read()
        except Exception as e:
            return e
    return json.loads(fd)
#定时任务执行
def scheduler_tasks():
    scheduler.add_job(check.scheduler_lock, 'cron', second='*/5', id='scheduler_lock', replace_existing=True)
    scheduler.add_job(analytics_logs.internet_topic,'cron',second = '0',minute = '*/5',id='internet_topic',replace_existing=True)
    scheduler.add_job(analytics_logs.intranet_topic,'cron',second = '0',minute = '*/5',id='intranet_topic',replace_existing=True)
    scheduler.add_job(analytics_logs.kafka_web,'cron',second = '0',minute = '*',id='kafka_web',replace_existing=True)
    scheduler.add_job(Task.task_tables_info, 'cron', second='0', minute='0',hour='*',id='task_tables_info', replace_existing=True)
    scheduler.add_job(mysql_scheduler.mysql_scheduler,'cron', second='0', minute='0',hour='2', id='mysql_scheduler', replace_existing=True)
    scheduler.add_job(Task.check_publish, 'cron', second='0', minute='*/5',hour='10-18',id='check_publish',replace_existing=True)
    scheduler.add_job(Task.clear_kestrel, 'cron', second='0', minute='0', hour='2', id='clear_kestrel',replace_existing=True)
    scheduler.add_job(Task.get_twemproxy_redis, 'cron', second='0', minute='*/30',hour='10-18', id='get_twemproxy_redis',replace_existing=True)
    scheduler.start()
#线上任务执行
class Scheduler_publish(object):
    def __init__(self):
        self.tm = time.strftime('%M',time.localtime())
        self.scheduler = BackgroundScheduler({'apscheduler.job_defaults.max_instances': '5'})
        self.scheduler.configure(timezone=pytz.timezone('Asia/Shanghai'))
    def Scheduler_mem(self,func,publish_key = 'None',taskKey = 'None',):
        self.scheduler.add_job(func,'cron', second='*/2',minute = self.tm,args=[publish_key,taskKey],id='%s_%s'%(taskKey,self.tm))
        return self.scheduler
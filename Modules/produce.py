#-*- coding: utf-8 -*-
from random import choice
import string
import datetime
from multiprocessing.dummy import Pool
import  Mysql
import urllib
import json
import socket
import loging
import pytz
import os
from rediscluster import RedisCluster
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
import time
import analytics_logs
import __init__
app = __init__.app
ip = socket.gethostbyname(socket.gethostname())
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
#分布式全局锁
def scheduler_lock():
    try:
        if RC.exists('scheduler_lock'):
            if ip != RC.get('scheduler_lock'):
                # 随机休眠
                time.sleep(choice([1,2,3,2,1]))
                raise AssertionError
        else:
            RC.set('scheduler_lock', ip)
            RC.expire('scheduler_lock',5)
    except Exception as e:
        loging.write(e)
def scheduler_tasks():
    scheduler.add_job(scheduler_lock, 'cron', second='*/3', id='scheduler_lock', replace_existing=True)
    scheduler.add_job(analytics_logs.internet_topic,'cron',second = '0',minute = '*/5',id='internet_topic',replace_existing=True)
    scheduler.add_job(analytics_logs.intranet_topic,'cron',second = '0',minute = '*/5',id='intranet_topic',replace_existing=True)
    scheduler.add_job(analytics_logs.kafka_web,'cron',second = '0',minute = '*',id='kafka_web',replace_existing=True)
    scheduler.start()
#sql定时执行
def mysql_scheduler():
    path = '%s/../Script/mysql_scheduler.py' % app.root_path
    os.system('/usr/bin/python %s' % path)
def Scheduler_sql_run():
    tt = datetime.datetime.now()+datetime.timedelta(days=1)
    tt = tt.strftime('%Y-%m-%d')
    scheduler.add_job(mysql_scheduler, 'date', run_date='%s 02:00:00' %tt,id='sql_run',replace_existing=True)
#线上任务执行
class Scheduler_publish(object):
    def __init__(self):
        self.tm = time.strftime('%M',time.localtime())
        self.scheduler = BackgroundScheduler({'apscheduler.job_defaults.max_instances': '5'})
        self.scheduler.configure(timezone=pytz.timezone('Asia/Shanghai'))
        self.path = app.root_path
    def job_update_java(self):
        path = '%s/../Script/java_update_script.py' % self.path
        os.system('/usr/bin/python %s' % path)

    def job_publish_java(self):
        path = '%s/../Script/java_publish_script.py' % self.path
        os.system('/usr/bin/python %s' % path)

    def job_update_php(self):
        path = '%s/../Script/php_update_script.py' % self.path
        os.system('/usr/bin/python %s' % path)

    def job_publish_php(self):
        path = '%s/../Script/php_publish_script.py' % self.path
        os.system('/usr/bin/python %s' % path)
    def Scheduler_mem(self,func):
        self.scheduler.add_job(func,'cron', second='*/2',minute = self.tm )
        return self.scheduler
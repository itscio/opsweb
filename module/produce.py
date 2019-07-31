#-*- coding: utf-8 -*-
import pytz
import time,datetime
from module import Task,Task2,loging
import redis
import socket
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
app = Flask(__name__)
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/sql.conf')
#logging.basicConfig()
#logging.getLogger('apscheduler').setLevel(logging.DEBUG)
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
RC = Redis = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
HOST = socket.gethostbyname(socket.gethostname())
jobstores = {'default': SQLAlchemyJobStore(url=app.config.get('SQLALCHEMY_BINDS')['op'])}
executors = {'default': ThreadPoolExecutor(30),'processpool': ProcessPoolExecutor(5)}
job_defaults = {'coalesce': False,'max_instances': 1,'misfire_grace_time':60}
scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors, job_defaults=job_defaults, timezone=pytz.timezone('Asia/Shanghai'))
#单点后台执行
def scheduler_tasks():
    run_date = datetime.datetime.now() + datetime.timedelta(minutes=1)
    run_date = run_date.strftime('%H:%M').split(':')
    #scheduler.add_job(Task.server_per, 'cron', second='0', minute=run_date[1], hour=run_date[0], id=Task.server_per.__name__, replace_existing=True)
    scheduler.add_job(Task2.Redis_clear, 'cron', second='0', minute=run_date[1], hour=run_date[0], id=Task2.Redis_clear.__name__,replace_existing=True)
    ################################################################################################################################################
    scheduler.add_job(Task.business_monitor, 'cron', second='0', minute='*', id=Task.business_monitor.__name__,replace_existing=True)
    scheduler.add_job(Task.es_get_log_status, 'cron', second='0', minute='*', id=Task.es_get_log_status.__name__,replace_existing=True)
    scheduler.add_job(Task.es_get_log_time, 'cron', second='0', minute='*', id=Task.es_get_log_time.__name__,replace_existing=True)
    scheduler.add_job(Task.es_get_data, 'cron', second='0', minute='*', id=Task.es_get_data.__name__, replace_existing=True)
    scheduler.add_job(Task.get_server_info, 'cron', second='0', minute='30',hour='4',id=Task.get_server_info.__name__,replace_existing=True)
    scheduler.add_job(Task.auto_discovery, 'cron', second='0', minute='0', hour='*/4',id=Task.auto_discovery.__name__,replace_existing=True)
    scheduler.add_job(Task.get_app_service, 'cron', second='0', minute='0', hour='*',id=Task.get_app_service.__name__, replace_existing=True)
    scheduler.add_job(Task.get_project_app, 'cron', second='0', minute='30', hour='*/8', id=Task.get_project_app.__name__,replace_existing=True)
    scheduler.add_job(Task.cron_run_task, 'cron', second='0', minute='0', hour='*/1',id=Task.cron_run_task.__name__, replace_existing=True)
    scheduler.add_job(Task.business_performance, 'cron', second='0', minute='*/3', id=Task.business_performance.__name__,replace_existing=True)
    scheduler.add_job(Task.reboot_tomcat, 'cron', second='0', minute='*/5', id=Task.reboot_tomcat.__name__,replace_existing=True)
    scheduler.add_job(Task.influxdb_counts, 'cron', second='0', minute='1',hour='*', id=Task.influxdb_counts.__name__,replace_existing=True)
    scheduler.add_job(Task.influxdb_alarm, 'cron', second='0', minute='15', hour='*/6', id=Task.influxdb_alarm.__name__,replace_existing=True)
    scheduler.add_job(Task.get_project_lists, 'cron', second='0', minute='30', hour='*',id=Task.get_project_lists.__name__, replace_existing=True)
    scheduler.add_job(Task.zabbix_counts, 'cron', second='0', minute='*/5', hour='*', id=Task.zabbix_counts.__name__,replace_existing=True)
    scheduler.add_job(Task2.task_run, 'cron', second='0', minute='*/5', hour='*', id=Task2.task_run.__name__,replace_existing=True)
    scheduler.add_job(Task2.get_other_info, 'cron', second='0', minute='0', hour='*/5', id=Task2.get_other_info.__name__,replace_existing=True)
    scheduler.add_job(Task2.get_redis_info, 'cron', second='0', minute='0', hour='6', id=Task2.get_redis_info.__name__,replace_existing=True)
    scheduler.add_job(Task2.k8s_health_check, 'cron', second='0', minute='*/5', id=Task2.k8s_health_check.__name__,replace_existing=True)
    scheduler.add_job(Task2.alarm_load, 'cron', second='0', minute='*/5', id=Task2.alarm_load.__name__,replace_existing=True)
    scheduler.add_job(Task2.k8s_ingress_log, 'cron', second='0', minute='*', id=Task2.k8s_ingress_log.__name__,replace_existing=True)
    scheduler.add_job(Task2.Redis_alarm, 'cron', second='0', minute='*/3', id=Task2.Redis_alarm.__name__,replace_existing=True)
    scheduler.add_job(Task2.rsync_comment, 'cron', second='0', minute='0',hour='3',id=Task2.rsync_comment.__name__,replace_existing=True)
    scheduler.start()
#实时后台执行
class SchedulerPublish(object):
    def __init__(self):
        self.run_date = datetime.datetime.now() + datetime.timedelta(seconds=3)
        self.run_date = self.run_date.strftime('%Y-%m-%d %H:%M:%S')
        self.tm = time.strftime('%Y%m%d%H%M%S',time.localtime())
        self.scheduler = BackgroundScheduler()
        self.executors = {'default': ThreadPoolExecutor(10), 'processpool': ProcessPoolExecutor(5)}
        self.job_defaults = {'coalesce': False, 'max_instances': 1}
        self.scheduler.configure(timezone=pytz.timezone('Asia/Shanghai'),job_defaults=self.job_defaults,executors=self.executors)
    def Scheduler_mem(self,func,args = []):
        self.scheduler.add_job(func,'date', run_date=self.run_date,args=[args],id=self.tm,replace_existing=True)
        return self.scheduler
#并发后台执行
class SchedulerBackgroud(object):
    def __init__(self):
        self.run_date = datetime.datetime.now() + datetime.timedelta(seconds=3)
        self.run_date = self.run_date.strftime('%Y-%m-%d %H:%M:%S')
        self.scheduler = BackgroundScheduler()
        self.executors = {'default': ThreadPoolExecutor(20), 'processpool': ProcessPoolExecutor(5)}
        self.job_defaults = {'coalesce': False, 'max_instances': 1}
        self.scheduler.configure(timezone=pytz.timezone('Asia/Shanghai'),job_defaults=self.job_defaults,executors=self.executors)
    def Run(self):
        self.scheduler.add_job(Task.count_es_logs,'cron', second='0', minute='*',id=Task.count_es_logs.__name__, replace_existing=True)
        self.scheduler.add_job(Task.server_per, 'cron', second='0', minute='*/5', id=Task.server_per.__name__,replace_existing=True)
        self.scheduler.start()
        loging.write("Scheduler backgroud start on %s ......" %HOST)
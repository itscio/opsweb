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
app.config.from_pyfile('../conf/task.conf')
logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.DEBUG)
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
task_hosts = app.config.get('TASK_HOSTS')
RC = Redis = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
HOST = socket.gethostbyname(socket.gethostname())
jobstores = {'default': SQLAlchemyJobStore(url=app.config.get('SQLALCHEMY_BINDS')['idc'])}
executors = {'default': ThreadPoolExecutor(50),'processpool': ProcessPoolExecutor(8)}
job_defaults = {'coalesce': False,'max_instances': 3,'misfire_grace_time':60}
scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors, job_defaults=job_defaults, timezone=pytz.timezone('Asia/Shanghai'))
#单点后台执行
def scheduler_tasks():
    date_time = datetime.datetime.now() + datetime.timedelta(minutes=1)
    run_date = date_time.strftime('%H:%M').split(':')
    scheduler.remove_all_jobs()
    ################################################################################################################################################
    #scheduler.add_job(Task.zabbix_counts_task, 'cron', second='0', minute=run_date[1], hour=run_date[0],id=Task.zabbix_counts_task.__name__, replace_existing=True)
    scheduler.add_job(Task.business_monitor_task, 'cron', second='0', minute='*', id=Task.business_monitor_task.__name__,replace_existing=True)
    scheduler.add_job(Task.es_log_status, 'cron', second='0', minute='*', id=Task.es_log_status.__name__,replace_existing=True)
    scheduler.add_job(Task.es_log_time, 'cron', second='0', minute='*', id=Task.es_log_time.__name__,replace_existing=True)
    scheduler.add_job(Task.business_data, 'cron', second='0', minute='*', id=Task.business_data.__name__, replace_existing=True)
    scheduler.add_job(Task.assets_infos, 'cron', second='0', minute='30',hour='4',id=Task.assets_infos.__name__,replace_existing=True)
    scheduler.add_job(Task.auto_discovery_task, 'cron', second='0', minute='0', hour='*/4',id=Task.auto_discovery_task.__name__,replace_existing=True)
    scheduler.add_job(Task.app_service_task, 'cron', second='0', minute='0', hour='*',id=Task.app_service_task.__name__, replace_existing=True)
    scheduler.add_job(Task.project_app_task, 'cron', second='0', minute='30', hour='*/8', id=Task.project_app_task.__name__,replace_existing=True)
    scheduler.add_job(Task.cron_task_run, 'cron', second='0', minute='0', hour='*',id=Task.cron_task_run.__name__, replace_existing=True)
    scheduler.add_job(Task.business_performance_task, 'cron', second='0', minute='*/3', id=Task.business_performance_task.__name__,replace_existing=True)
    scheduler.add_job(Task.reboot_tomcat_task, 'cron', second='0', minute='*/5', id=Task.reboot_tomcat_task.__name__,replace_existing=True)
    scheduler.add_job(Task.influxdb_counts_task, 'cron', second='0', minute='1',hour='*', id=Task.influxdb_counts_task.__name__,replace_existing=True)
    scheduler.add_job(Task.influxdb_alarm_task, 'cron', second='0', minute='15', hour='*/6', id=Task.influxdb_alarm_task.__name__,replace_existing=True)
    scheduler.add_job(Task.project_lists_task, 'cron', second='0', minute='30', hour='*',id=Task.project_lists_task.__name__, replace_existing=True)
    scheduler.add_job(Task.zabbix_counts_task, 'cron', second='0', minute='0', hour='*', id=Task.zabbix_counts_task.__name__,replace_existing=True)
    ################################################################################################################################################
    #scheduler.add_job(Task2.zabbix_network_get, 'cron', second='0', minute=run_date[1], hour=run_date[0], id=Task2.zabbix_network_get.__name__,replace_existing=True)
    scheduler.add_job(Task2.task_cron_run, 'cron', second='0', minute='*/5', hour='*', id=Task2.task_cron_run.__name__,replace_existing=True)
    scheduler.add_job(Task2.other_info_task, 'cron', second='0', minute='0', hour='*/5', id=Task2.other_info_task.__name__,replace_existing=True)
    scheduler.add_job(Task2.redis_info_task, 'cron', second='0', minute='45', hour='*/3', id=Task2.redis_info_task.__name__,replace_existing=True)
    scheduler.add_job(Task2.k8s_check_task, 'cron', second='0', minute='*/3', id=Task2.k8s_check_task.__name__,replace_existing=True)
    scheduler.add_job(Task2.alarm_load_task, 'cron', second='0', minute='*/5', id=Task2.alarm_load_task.__name__,replace_existing=True)
    scheduler.add_job(Task2.ingress_log, 'cron', second='0', minute='*', id=Task2.ingress_log.__name__,replace_existing=True)
    scheduler.add_job(Task2.Redis_alarm_task, 'cron', second='0', minute='*/3', id=Task2.Redis_alarm_task.__name__,replace_existing=True)
    scheduler.add_job(Task2.rsync_comment_task, 'cron', second='0', minute='0',hour='3',id=Task2.rsync_comment_task.__name__,replace_existing=True)
    scheduler.add_job(Task2.zabbix_network_get, 'cron', second='0', minute='0',hour='*/4', id=Task2.zabbix_network_get.__name__,replace_existing=True)
    #scheduler.add_job(Task2.kafka_topic, 'cron', second='0', minute='*/5', id=Task2.kafka_topic.__name__,replace_existing=True)
    if HOST in task_hosts:
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
    def Scheduler_mem(self,func,args = None):
        self.scheduler.add_job(func,'date', run_date=self.run_date,args=[args],id=self.tm,replace_existing=True)
        return self.scheduler
#并发后台执行
class SchedulerBackgroud(object):
    def __init__(self):
        self.run_date = datetime.datetime.now() + datetime.timedelta(seconds=3)
        self.run_date = self.run_date.strftime('%Y-%m-%d %H:%M:%S')
        self.tt = time.strftime('%Y%m%d%H%M', time.localtime())
        self.scheduler = BackgroundScheduler()
        self.executors = {'default': ThreadPoolExecutor(20), 'processpool': ProcessPoolExecutor(5)}
        self.job_defaults = {'coalesce': False, 'max_instances': 3}
        self.scheduler.configure(timezone=pytz.timezone('Asia/Shanghai'),job_defaults=self.job_defaults,executors=self.executors)
    def Run(self):
        self.scheduler.add_job(Task.query_es_logs,'cron', second='0', minute='*',id=Task.query_es_logs.__name__, replace_existing=True)
        self.scheduler.add_job(Task.get_server_per, 'cron', second='0', minute='*/5', id=Task.get_server_per.__name__,replace_existing=True)
        if HOST in task_hosts:
            self.scheduler.start()
            loging.write("Scheduler backgroud start on %s ......" %HOST)
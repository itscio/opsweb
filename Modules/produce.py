#-*- coding: utf-8 -*-
from flask import Flask,session
import pytz
import time,datetime
from Modules import Task,Task2,loging,db_op
import redis
import socket
import logging as Logging
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
app = Flask(__name__)
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/sql.conf')
app.config.from_pyfile('../conf/task.conf')
logging = loging.Error()
DB = SQLAlchemy(app)
#Logging.basicConfig()
#Logging.getLogger('apscheduler').setLevel(logging.DEBUG)
task_servers = app.config.get('TASK_SERVERS')
TASK_BACKGROUD = app.config.get('TASK_BACKGROUD')
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
RC = Redis = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
HOST = socket.gethostbyname(socket.gethostname())
jobstores = {'default': SQLAlchemyJobStore(url=app.config.get('SQLALCHEMY_BINDS')['op'])}
scheduler = BackgroundScheduler({'apscheduler.job_defaults.max_instances': '500','apscheduler.job_defaults.coalesce': 'false'})
scheduler.configure(jobstores=jobstores,timezone=pytz.timezone('Asia/Shanghai'))
def Async_log(user,url):
    db_op_log = db_op.op_log
    url = url.replace('op_servers', 'op.moji.com')
    if 'op.moji.com' in url and not url.endswith('/index'):
        try:
            ip = session['remote_ip']
            v = db_op_log(date=time.strftime('%Y-%m-%d',time.localtime()),time = time.strftime('%H:%M:%S',time.localtime()),ip=ip,user=user,access=url)
            db_op.DB.session.add(v)
            db_op.DB.session.commit()
        except Exception as e:
            logging.error(e)
        finally:
            db_op.DB.session.remove()
#单点后台执行
def scheduler_tasks():
    try:
        run_date = datetime.datetime.now() + datetime.timedelta(minutes=1)
        run_date = run_date.strftime('%H:%M').split(':')
        #scheduler.add_job(Task.zabbix_counts, 'cron', second='0', minute=run_date[1], hour=run_date[0], id=Task.zabbix_counts.__name__, replace_existing=True)
        #scheduler.add_job(Task2.get_redis_info, 'cron', second='0', minute=run_date[1], hour=run_date[0], id=Task2.get_redis_info.__name__,replace_existing=True)
        ################################################################################################################################################
        scheduler.add_job(Task.business_monitor, 'cron', second='0', minute='*', id=Task.business_monitor.__name__,replace_existing=True)
        scheduler.add_job(Task.es_get_log_status, 'cron', second='0', minute='*', id=Task.es_get_log_status.__name__,replace_existing=True)
        scheduler.add_job(Task.es_get_log_time, 'cron', second='0', minute='*', id=Task.es_get_log_time.__name__,replace_existing=True)
        scheduler.add_job(Task.es_get_data, 'cron', second='0', minute='*', id=Task.es_get_data.__name__, replace_existing=True)
        scheduler.add_job(Task.server_per, 'cron', second='0', minute='*/15',id=Task.server_per.__name__, replace_existing=True)
        scheduler.add_job(Task.zabbix_triggers, 'cron', second='0', minute='*', id=Task.zabbix_triggers.__name__, replace_existing=True)
        scheduler.add_job(Task.get_server_info, 'cron', second='0', minute='30',hour='4',id=Task.get_server_info.__name__,replace_existing=True)
        scheduler.add_job(Task.auto_discovery, 'cron', second='0', minute='0', hour='*/4',id=Task.auto_discovery.__name__,replace_existing=True)
        scheduler.add_job(Task.get_app_service, 'cron', second='0', minute='0', hour='*/5',id=Task.get_app_service.__name__, replace_existing=True)
        scheduler.add_job(Task.get_project_app, 'cron', second='0', minute='30', hour='*/8', id=Task.get_project_app.__name__,replace_existing=True)
        scheduler.add_job(Task.zabbix_disk_network, 'cron', second='0', minute='0',hour='7',id=Task.zabbix_disk_network.__name__,replace_existing=True)
        scheduler.add_job(Task.cron_run_task, 'cron', second='0', minute='0', hour='*/1',id=Task.cron_run_task.__name__, replace_existing=True)
        scheduler.add_job(Task.business_alarm, 'cron', second='0', minute='*/3', id=Task.business_alarm.__name__,replace_existing=True)
        scheduler.add_job(Task.reboot_tomcat, 'cron', second='0', minute='*/15', id=Task.reboot_tomcat.__name__,replace_existing=True)
        scheduler.add_job(Task.influxdb_counts, 'cron', second='0', minute='1',hour='*', id=Task.influxdb_counts.__name__,replace_existing=True)
        scheduler.add_job(Task.influxdb_alarm, 'cron', second='0', minute='0', hour='2', id=Task.influxdb_alarm.__name__,replace_existing=True)
        scheduler.add_job(Task.Get_project_lists, 'cron', second='0', minute='0', hour='*',id=Task.Get_project_lists.__name__, replace_existing=True)
        scheduler.add_job(Task.zabbix_counts, 'cron', second='0', minute='*/15', hour='*', id=Task.zabbix_counts.__name__,replace_existing=True)
        scheduler.add_job(Task2.get_mysqldb_info, 'cron', second='0', minute='0', hour='3', id=Task2.get_mysqldb_info.__name__,replace_existing=True)
        scheduler.add_job(Task2.task_run, 'cron', second='0', minute='*/5', hour='*', id=Task2.task_run.__name__,replace_existing=True)
        scheduler.add_job(Task2.get_other_info, 'cron', second='0', minute='0', hour='5', id=Task2.get_other_info.__name__,replace_existing=True)
        scheduler.add_job(Task.check_host_exist, 'cron', second='0', minute='*/15', id=Task.check_host_exist.__name__,replace_existing=True)
        scheduler.add_job(Task2.get_redis_info, 'cron', second='0', minute='0', hour='6', id=Task2.get_redis_info.__name__,replace_existing=True)
        scheduler.add_job(Task2.get_redis_status, 'cron', second='0', minute='8',hour='*', id=Task2.get_redis_status.__name__,replace_existing=True)
        scheduler.add_job(Task2.alarm_load, 'cron', second='0', minute='*', id=Task2.alarm_load.__name__,replace_existing=True)
        scheduler.start()
    except Exception as e:
        logging.error(e)
#实时后台执行
class Scheduler_publish(object):
    def __init__(self):
        self.run_date = datetime.datetime.now() + datetime.timedelta(seconds=3)
        self.run_date = self.run_date.strftime('%Y-%m-%d %H:%M:%S')
        self.tm = time.strftime('%Y%m%d%H%M%S',time.localtime())
        self.scheduler = BackgroundScheduler({'apscheduler.job_defaults.max_instances': '50','apscheduler.job_defaults.coalesce': 'false'})
        self.scheduler.configure(timezone=pytz.timezone('Asia/Shanghai'))
    def Scheduler_mem(self,func,args = []):
        self.scheduler.add_job(func,'date', run_date=self.run_date,args=[args],id=self.tm,replace_existing=True)
        return self.scheduler
#并发后台执行
class Scheduler_backgroud(object):
    def __init__(self):
        self.run_date = datetime.datetime.now() + datetime.timedelta(seconds=3)
        self.run_date = self.run_date.strftime('%Y-%m-%d %H:%M:%S')
        self.scheduler = BackgroundScheduler({'apscheduler.job_defaults.max_instances': '50','apscheduler.job_defaults.coalesce': 'false'})
        self.scheduler.configure(timezone=pytz.timezone('Asia/Shanghai'))
    def Run(self):
        if HOST in TASK_BACKGROUD:
            self.scheduler.add_job(Task.count_es_logs,'cron', second='0', minute='*',id=Task.count_es_logs.__name__, replace_existing=True)
            self.scheduler.start()
            loging.write("Scheduler backgroud start on %s ......" %HOST)
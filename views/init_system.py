#-*- coding: utf-8 -*-
from flask import Blueprint,request,render_template,g,flash
import paramiko
import redis
import datetime
import pytz
from Modules import loging, MyForm,check,produce
from apscheduler.schedulers.background import BackgroundScheduler
import __init__
app = __init__.app
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
username = app.config.get('INIT_USER')
passwd = app.config.get('INIT_PASSWORD')
Redis = redis.StrictRedis(host=redis_host, port=redis_port)
scheduler = BackgroundScheduler({'apscheduler.job_defaults.max_instances': '5'})
scheduler.configure(timezone=pytz.timezone('Asia/Shanghai'))
page_init_system = Blueprint('init_system', __name__)
@page_init_system.route('/init',methods = ['GET', 'POST'])
def init_system():
    form = MyForm.MyForm_input()
    try:
        if form.submit.data:
            ips = form.text.data.strip().splitlines()
            ips = set(ips)
            if len(ips) >10:
                raise flash('一次初始化服务器数量不能超过10个!')
            for ip in ips:
                ip_list = ip.split('.')
                hostname = 'S%s-%s.server.baihe' %(ip_list[2],ip_list[3])
                for i in ('45','46'):
                    Redis.lpush('clear%s_salt-minon' %i,hostname)
                def remote_run(ip):
                    def ssh2(ip, username, passwd,cmd):
                        try:
                            ssh = paramiko.SSHClient()
                            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                            ssh.connect(ip, 22, username, passwd, timeout=30)
                            loging.write('%s     %s'%(ip,cmd))
                            ssh.exec_command(cmd)
                            ssh.close()
                        except Exception as e:
                            loging.write(e)
                    cmds = ['/sbin/service iptables stop && /sbin/chkconfig iptables off','rm -f /tmp/mod_host.sh','/usr/bin/yum -y install wget','/usr/bin/wget -P /tmp/ http://172.16.16.160/dw/shell/mod_host.sh','/bin/bash /tmp/mod_host.sh']
                    for cmd in cmds:
                        ssh2(ip,username,passwd,cmd)
                tm = datetime.datetime.now()+datetime.timedelta(minutes=1)
                tm = tm.strftime('%Y-%m-%d %H:%M:%S')
                flash('初始化 %s完成,后台需要运行60分钟......' % ip)
                scheduler.add_job(remote_run, 'date', run_date=tm,args=[ip],id=ip)
                scheduler.start()
    except Exception as e:
        loging.write(e)
    return render_template('init_system.html',form=form)
@page_init_system.before_request
@check.login_required(grade=0)
def check_login(error=None):
    produce.Async_log(g.user, request.url)
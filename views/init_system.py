#-*- coding: utf-8 -*-
from flask import Blueprint,request,render_template,g,flash
import paramiko
import redis
from Modules import loging, MyForm,check,produce
import __init__
app = __init__.app
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
Redis = redis.StrictRedis(host=redis_host, port=redis_port)
page_init_system = Blueprint('init_system', __name__)
@page_init_system.route('/init',methods = ['GET', 'POST'])
def init_system():
    form = MyForm.MyForm_input()
    def ssh2(ip,username,passwd,cmds):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip,22,username,passwd,timeout=30)
            for cmd in cmds:
                stdin, stdout, stderr = ssh.exec_command(cmd)
                if stderr.read():
                    flash(stderr.read())
            ssh.close()
        except Exception as e:
            loging.write(e)
            flash('初始化失败!')
    if form.submit.data:
        ips = form.text.data.strip().splitlines()
        ips = set(ips)
        for ip in ips:
            flash('初始化 %s 后台需要运行60分钟......' %ip)
            username = app.config.get('INIT_USER')
            passwd = app.config.get('INIT_PASSWORD')
            ip_list = ip.split('.')
            hostname = 'S%s-%s.server.baihe' %(ip_list[2],ip_list[3])
            for i in ('45','46'):
                Redis.lpush('clear%s_salt-minon' %i,hostname)
            cmds = ['rm -f /tmp/mod_host.sh',
                   '/usr/bin/wget -P /tmp/ http://172.16.16.160/dw/shell/mod_host.sh ',
                   'echo "* * * * * /bin/bash /tmp/mod_host.sh" >/var/spool/cron/root']
            ssh2(ip,username,passwd,cmds)
            Redis.lpush('init_server_list',ip)
    return render_template('init_system.html',form=form)
@page_init_system.before_request
@check.login_required(grade=0)
def check_login(error=None):
    produce.Async_log(g.user, request.url)
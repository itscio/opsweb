#-*- coding: utf-8 -*-
from flask import Blueprint,request,render_template,g,flash
import redis
from Modules import loging, MyForm,check,produce,main_info
import __init__
app = __init__.app
init_key = app.config.get('INIT_KEY')
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
Redis = redis.StrictRedis(host=redis_host, port=redis_port)
page_init_system = Blueprint('init_system', __name__)
@page_init_system.route('/init',methods = ['GET', 'POST'])
@main_info.main_info
def init_system():
    form = MyForm.MyForm_input()
    if form.submit.data:
        ips = form.text.data.strip().splitlines()
        ips = set(ips)
        for ip in ips:
            Redis.lpush(init_key,ip)
            flash('已将%s加入初始化处理队列......' % ip)
    return render_template('init_system.html',Main_Infos=g.main_infos,form=form)
@page_init_system.before_request
@check.login_required(grade=0)
def check_login(error=None):
    produce.Async_log(g.user, request.url)
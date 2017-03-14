#-*- coding: utf-8 -*-
from flask import Blueprint,render_template,g,flash,request
from Modules import check ,MyForm,produce
from rediscluster import RedisCluster
from flask_mail import Message
from flask_mail import Mail
import re
import __init__
app = __init__.app
mail = Mail(app)
page_vpn_admin=Blueprint('vpn_admin',__name__)
nodes = app.config.get('NODES')
Redis = RedisCluster(startup_nodes=nodes,decode_responses=True,)
@page_vpn_admin.route('/vpn_admin',methods = ['GET', 'POST'])
def vpn_admin():
    form = MyForm.MyForm_vpn()
    if form.submit.data:
        users = form.text.data.strip().splitlines()
        users = set(users)
        for i,name in enumerate(users):
            if not re.search('.*@baihe.com$',name):
                flash('%s格式错误,用户名应为百合个人邮箱账号!'%name)
                i=-1
        if i < 0:
            return render_template('Message.html')
        action = form.select_action.data
        key = 'vpn2_list'
        sender = "alarm@baihe.com"
        if action == 'query':
            List = []
            user_list = Redis.hgetall(key)
            for user in users:
                try:
                    if user_list[user]:
                        List.append((user,user_list[user]))
                except:
                    continue
            if List:
                return render_template('vpn_admin_show.html',user_list = List)
            else:
                flash('%s 账号不存在!' %user)
        elif action == 'add':
            for user in users:
                pw = produce.Produce(13)
                val = [K for K in Redis.hgetall(key)]
                if user in val:
                    flash('%s 账号已存在'%user)
                    continue
                msg = Message("VPN账号信息",sender=sender,recipients=[user])
                msg.html = '<p>用户名:%s</p><p> 密码:%s</p><p><font color="red">账号5分钟后开通,请妥善保管此封邮件,勿邮件回复!</font></p>' %(user,pw)
                with app.open_resource("%s/../doc/vpn_conf.docx" %page_vpn_admin.root_path) as f:
                    msg.attach("vpn_conf.docx", "text/docx", f.read())
                try:
                    with app.app_context():
                        mail.send(msg)
                        Redis.hset(key,user,pw)
                except Exception as e:
                    flash(e)
                else:
                    flash('%s 账号开通完毕,通知邮件已发送.' %user)
        elif action == 'del':
            for user in users:
                Redis.hdel(key,user)
                Redis.hdel('vpn_list', user)
                flash('%s 账号已关闭!' %user)
        return render_template('Message.html')
    return render_template('vpn_admin.html',form=form)

@page_vpn_admin.before_request
@check.login_required(grade=0)
def check_login(error=None):
    produce.Async_log(g.user, request.url)
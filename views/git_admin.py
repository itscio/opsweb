#-*- coding: utf-8 -*-
from flask import Blueprint,render_template,g,flash,request
from Modules import check,MyForm,produce,main_info
from flask_mail import Mail
from flask_mail import Message
import requests
import __init__
app = __init__.app
git_url = app.config.get('GIT_URL')
mail = Mail(app)
page_git_admin = Blueprint('git_admin',__name__)
@page_git_admin.route('/git_admin',methods = ['GET', 'POST'])
@main_info.main_info
def git_admin():
    params = {'private_token':app.config.get('GIT_TOKEN')}
    URL = "http://%s/api/v3/users?" %git_url
    def Get_user(user):
        username = user.split('@')[0]
        params['search'] = username
        r = requests.request('get',URL,timeout=3,params=params)
        return r.json()

    def Add_user(user,pw):
        username = user.split('@')[0]
        params['username'] = username
        params['name'] = username
        params['email'] = user
        params['password'] = pw
        params['projects_limit'] = 50
        params['can_create_group'] = 'true'
        params['confirm']  = 'false'
        r = requests.request('post',URL,timeout=3,params=params)
        return r.json()

    def Del_user(id):
        URL = "http://%s/api/v3/users/%s/block" %(git_url,id)
        requests.request('put', URL, timeout=3, params=params)
        URL = "http://%s/api/v3/users/%s" % (git_url,id)
        r = requests.request('delete',URL,timeout=3,params=params)
        return r.json()

    form = MyForm.MyForm_git_admin()
    if form.submit.data:
        sender = app.config.get('MAIL_DEFAULT_SENDER')
        names = form.text.data.strip().splitlines()
        action = form.select_action.data
        for name in names:
            name = name.strip()
            if '@' in name:
                if action == 'query':
                    INFOS = ('id','username','name','email','state','projects_limit','can_create_group','web_url','current_sign_in_at','created_at')
                    user_info =Get_user(name)
                    if user_info:
                        user_info = user_info[0]
                        flash('账号:%s信息如下:' %name)
                        for info in INFOS:
                            flash('%s: %s' %(info,user_info[info]))
                        flash('--- '*16)
                    else:
                        flash('%s 不存在!' %name)
                elif action == 'add':
                    if Get_user(name):
                        flash('%s 账号已存在!' %name)
                    else:
                        pw = produce.Produce(13)
                        if Add_user(name,pw):
                                #开通成功后再发送邮件
                                msg = Message("GIT账号信息",sender=sender,recipients=[name])
                                msg.html = '<p>用户名:%s</p><p> 密码:%s</p><p>GIT访问地址:http://%s/</p><p><font color="red">勿邮件回复!</font></p>' %(name,pw,git_url)
                                with app.app_context():
                                    try:
                                        mail.send(msg)
                                    except Exception as e:
                                        flash(e)
                                        flash('%s 邮件发送失败!' %name)
                                    else:
                                        flash('%s 账号开通成功,通知邮件已发送.' %name)
                        else:
                            flash('%s 账号开通失败!' %name)
                elif action == 'del':
                    user = Get_user(name)
                    if user:
                        id = user[0]['id']
                        if Del_user(id):
                            flash('%s 账号已删除!' %name)
                    else:
                        flash('%s 账号不存在!' %name)
            else:
                flash('%s 账号格式错误,应该为邮箱地址!' %name)
        return render_template('Message_static.html',Main_Infos=g.main_infos)
    return render_template('git_admin.html',Main_Infos=g.main_infos,form=form)
@page_git_admin.before_request
@check.login_required(grade=0)
def check_login(error=None):
    produce.Async_log(g.user, request.url)
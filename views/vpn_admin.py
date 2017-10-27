#-*- coding: utf-8 -*-
from flask import Blueprint,render_template,g,flash,request
from Modules import check ,MyForm,produce,db_op,loging,Md5,main_info
from flask_mail import Message
from flask_mail import Mail
from sqlalchemy import and_
import re
import __init__
app = __init__.app
mail = Mail(app)
crypto_key = app.config.get('CRYPTO_KEY')
page_vpn_admin=Blueprint('vpn_admin',__name__)
@page_vpn_admin.route('/vpn_admin',methods = ['GET', 'POST'])
@main_info.main_info
def vpn_admin():
    form = MyForm.MyForm_vpn()
    db = db_op.vpn_users
    if form.submit.data:
        users = form.text.data.strip().splitlines()
        vpn_type = form.select_type.data
        users = set(users)
        crypto = Md5.crypto(crypto_key)
        for i,name in enumerate(users):
            if not re.search('.*@baihe.com$',name):
                flash('%s格式错误,用户名应为百合个人邮箱账号!'%name)
                i=-1
        if i < 0:
            return render_template('Message_static.html',Main_Infos=g.main_infos)
        action = form.select_action.data
        sender = app.config.get('MAIL_DEFAULT_SENDER')
        if vpn_type == 'intranet':
            vpn_servers = app.config.get('VPN_INTRA')
        if vpn_type == 'internet':
            vpn_servers = app.config.get('VPN_INTER')
        if action == 'query':
            List = []
            for user in users:
                val = db.query.with_entities(db.user,db.password).filter( and_(db.user == user,db.vpn_type == 'intranet')).all()
                if val:
                    List.append([va for va in val[0]])
                else:
                    flash('%s 账号不存在!' %user)
            if List:
                List = [(list[0],crypto.decrypt(list[1])) for list in List]
                return render_template('vpn_admin_show.html',Main_Infos=g.main_infos, user_list=List)
        elif action == 'add':
            for user in users:
                pw = produce.Produce(13)
                if db.query.filter(db.user == user).all():
                    flash('%s 账号已存在'%user)
                    continue
                msg = Message("VPN账号信息",sender=sender,recipients=[user])
                msg.html = '<p>用户名:%s</p><p> 密码:%s</p><p> VPN地址:%s</p><p><font color="red">账号5分钟后开通,请妥善保管此封邮件,勿邮件回复!</font></p>' %(user,pw,vpn_servers)
                with app.open_resource("%s/../doc/vpn_conf.docx" %page_vpn_admin.root_path) as f:
                    msg.attach("vpn_conf.docx", "text/docx", f.read())
                try:
                    with app.app_context():
                        mail.send(msg)
                        db_op.DB.session.add(db(user=user, password=crypto.encrypt(pw), status=1,vpn_type=vpn_type))
                        db_op.DB.session.commit()
                except Exception as e:
                    flash(e)
                else:
                    flash('%s 账号开通完毕,通知邮件已发送.' %user)
        elif action == 'del':
            for user in users:
                db.query.filter(db.user == user).update({db.status:2})
                db_op.DB.session.commit()
                flash('%s 账号已关闭!' %user)
        elif action == 'change':
            for user in users:
                db.query.filter(db.user == user).update({db.status:1,db.vpn_type:vpn_type})
                db_op.DB.session.commit()
                flash(('%s vpn类型已变更!' %user))
        return render_template('Message_static.html',Main_Infos=g.main_infos)
    return render_template('vpn_admin.html',Main_Infos=g.main_infos,form=form)

@page_vpn_admin.before_request
@check.login_required(grade=0)
def check_login(error=None):
    produce.Async_log(g.user, request.url)
@page_vpn_admin.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
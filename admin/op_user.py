#-*- coding: utf-8 -*-
from flask import Blueprint,render_template,flash,g,request
from sqlalchemy import and_
from Modules import db_op,MyForm, Md5,check,produce,main_info
from flask_mail import Mail
from flask_mail import Message
import redis
import __init__
app = __init__.app
mail = Mail(app)
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
Redis = redis.StrictRedis(host=redis_host, port=redis_port)
page_op_user = Blueprint('op_user',__name__)
@page_op_user.route('/op_user',methods = ['GET', 'POST'])
@main_info.main_info
def op_user():
    form = MyForm.Myform_op_user()
    db = db_op.idc_users
    sender = app.config.get('MAIL_DEFAULT_SENDER')
    if form.submit.data:
        users = form.text.data.splitlines()
        action  = form.select.data
        for user in users:
            if '@baihe.com' in user:
                if action == 'unlock':
                    Redis.delete('%s_lock' %user)
                    flash('{0}账号已解锁!'.format(user))
                val = db.query.with_entities(db.name).filter(and_(db.name == user)).all()
                if action == 'query':
                    if val:
                        flash('{0}账号已存在!'.format(user))
                    else:
                        flash('{0}账号不存在!'.format(user))
                if action == 'add':
                    if val:
                        flash('{0}账号已存在!'.format(user))
                    else:
                        PW = Md5.Md5_make(produce.Produce())
                        pw = Md5.Md5_make(PW)
                        # 开通成功后再发送邮件
                        msg = Message("OP账号信息", sender=sender, recipients=[user])
                        msg.html = '<p>用户名:%s</p><p> 密码:%s</p><p>访问地址:https://op.baihe.com/</p><p><font color="red">勿邮件回复!</font></p>' % (
                        user, PW)
                        with app.app_context():
                            try:
                                mail.send(msg)
                            except Exception as e:
                                flash(e)
                                flash('%s 邮件发送失败!' % user)
                            else:
                                db_op.DB.session.add(db(name=user, passwd=pw, grade=10))
                                db_op.DB.session.commit()
                                flash('%s 账号开通成功,通知邮件已发送.' % user)
                if action == 'del':
                    try:
                        val = db.query.filter(and_(db.name == user)).all()
                        if val:
                            for c in val:
                                db_op.DB.session.delete(c)
                                db_op.DB.session.commit()
                            flash('{0}账号删除成功!'.format(user))
                        else:
                            flash('{0}账号不存在!'.format(user))
                    except Exception as e:
                        flash(e)
                if action == 'init':
                    if val:
                        init_pw = app.config.get('INIT_OP_PASSWORD')
                        pw = Md5.Md5_make(init_pw)
                        db.query.filter(and_(db.name == user)).update({db.passwd:pw})
                        db_op.DB.session.commit()
                        flash('{0}账号初始化成功,初始化密码:{1}'.format(user,init_pw))
                    else:
                        flash('{0}账号不存在!'.format(user))
            else:
                flash('{0}账号格式不正确,账号应为个人邮箱!'.format(user))
        return render_template('Message_static.html',Main_Infos=g.main_infos)
    return render_template('op_user.html',form=form,Main_Infos=g.main_infos)

@page_op_user.before_request
@check.login_required(grade=0)
def check_login(error=None):
    produce.Async_log(g.user, request.url)

@page_op_user.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
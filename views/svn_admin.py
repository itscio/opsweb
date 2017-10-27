#-*- coding: utf-8 -*-
from imp import reload
from flask import Blueprint,render_template,g,flash,request
from Modules import check,loging,MyForm,db_op,produce,main_info
from flask_mail import Mail
from flask_mail import Message
from sqlalchemy import and_,distinct
import re
import __init__
app = __init__.app
svn_url = app.config.get('SVN_URL')
mail = Mail(app)
logging = loging.Error()
page_svn_admin = Blueprint('svn_admin',__name__)
@page_svn_admin.route('/svn_admin',methods = ['GET', 'POST'])
@main_info.main_info
def svn_admin():
    reload(MyForm)
    form = MyForm.MyForm_svn_admin()
    if form.submit.data:
        sender = app.config.get('MAIL_DEFAULT_SENDER')
        db  = db_op.svn_users
        db_groups = db_op.svn_groups
        ts = form.text.data.strip().splitlines()
        ts = set(ts)
        for i,name in enumerate(ts):
            if not re.search('.*@.*\.com$',name):
                flash('%s格式错误,用户名应为个人邮箱账号!'%name)
                i=-1
        if i < 0:
            return render_template('Message_static.html',Main_Infos=g.main_infos)
        Action = form.select_action.data
        def Query(db,*ts):
            #生成用户列表
            user_list = []
            for name in ts[0]:
                try:
                    val = db.query.with_entities(db.user,db.password).filter(db.user == name).all()
                    if val:
                        val = [v for v in val[0]]
                        groups = [group[0] for group in db_groups.query.with_entities(distinct(db_groups.groups)).filter(db_groups.users == name).all()]
                        for group in groups:
                                val.append(group)
                        user_list.append(val)
                except Exception as e:
                    logging.error(e)
                    flash('获取数据错误!')
                    return render_template('Message_static.html', Main_Infos=g.main_infos)
            return user_list
        if Action == 'query':
            user_list = Query(db,ts)
            if user_list :
                return render_template('svn_admin_show.html',Main_Infos=g.main_infos,user_list = user_list)
            else:
                flash('账号不存在!')
        elif Action == 'add':
            groups_list = form.select_groups.data
            if groups_list:
                for name in ts:
                    if Query(db,(name,)):
                        flash('%s 账号已存在!' %name)
                        continue
                    else:
                        try:
                            #数据库插入账户
                            pw = produce.Produce(13)
                            db_op.DB.session.add(db(user = name,password = pw,status = 1))
                            db_op.DB.session.commit()
                            #数据库插入用户组
                            for group in groups_list:
                                db_op.DB.session.add(db_groups(groups=group,users=name))
                                db_op.DB.session.commit()
                        except Exception as e:
                            flash(e)
                            flash('%s 账号开通失败!' %name)
                        else:
                            #开通成功后再发送邮件
                            msg = Message("SVN账号信息",sender=sender,recipients=[name])
                            msg.html = '<p>用户名:%s</p><p> 密码:%s</p><p>SVN根路径%s/svn/,具体项目路径请咨询各自组内同事.</p><p><font color="red">账号5分钟后开通,请妥善保管此封邮件,勿邮件回复!</font></p>' %(name,pw,svn_url)
                            with app.app_context():
                                try:
                                    mail.send(msg)
                                except Exception as e:
                                    flash(e)
                                    flash('%s 邮件发送失败!' %name)
                                else:
                                    flash('%s 账号开通成功,通知邮件已发送.' %name)
            else:
                flash('开通账户需选择账号对应的用户组')
        elif Action == 'add_group'or Action == 'del_group':
            svn_users = db.query.filter(db.user == name)
            groups_list = form.select_groups.data
            if groups_list:
                for name in ts:
                    if Query(db,(name,)):
                        try:
                            #修改用户组列表
                            for group in groups_list:
                                if 'add' in Action:
                                    db_op.DB.session.add(db_groups(groups=group, users=name))
                                    db_op.DB.session.commit()
                                    flash('%s 账号已添加到用户组%s' %(name,group))
                                if 'del' in Action:
                                    Info = db_groups.query.filter(and_(db_groups.groups == group,db_groups.users == name)).all()
                                    for c in Info:
                                        db_op.DB.session.delete(c)
                                        db_op.DB.session.commit()
                                    flash('%s 账号已从用户组%s移除.' %(name,group))
                            #修改用户状态
                            svn_users.update({db.status:4})
                            db_op.DB.session.commit()
                        except Exception as e:
                            logging.error(e)
                            flash('获取数据错误!')
                            return render_template('Message_static.html', Main_Infos=g.main_infos)
                    else:
                        flash('%s 账号不存在!' %name)
            else:
                flash('变更账户所属用户组,需先选择要变更的用户组')
        else:
            if Query(db,ts):
                for name in ts:
                    try:
                        #数据库删除账号
                        svn_users = db.query.filter(db.user == name)
                        if Action == 'del':
                            Str = '关闭'
                            #用户组内删除账号
                            Info = db_groups.query.filter(db_groups.users == name).all()
                            for c in Info:
                                db_op.DB.session.delete(c)
                                db_op.DB.session.commit()
                            svn_users.update({db.status:2})
                        elif Action == 'lock':
                            Str = '锁定'
                            svn_users.update({db.status:3})
                        elif Action == 'unlock':
                            Str = '解锁'
                            svn_users.update({db.status:4})
                        db_op.DB.session.commit()
                    except Exception as e:
                        logging.error(e)
                        flash('获取数据错误!')
                        return render_template('Message_static.html', Main_Infos=g.main_infos)
                    else:
                        flash('%s 账号%s成功!'%(name,Str))
            else:
                flash('账号不存在!')
        return render_template('Message_static.html',Main_Infos=g.main_infos)
    return render_template('svn_admin.html',Main_Infos=g.main_infos,form=form)
@page_svn_admin.before_request
@check.login_required(grade=0)
def check_login(error=None):
    produce.Async_log(g.user, request.url)

@page_svn_admin.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
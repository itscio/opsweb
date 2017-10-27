#-*- coding: utf-8 -*-
from flask_mail import Mail
from flask_mail import Message
from flask import Blueprint,render_template,g,flash,request
from Modules import MyForm,check,db_op,produce,main_info
import __init__
app = __init__.app
mail = Mail(app)
page_publish_apply = Blueprint('publish_apply',__name__)
@page_publish_apply.route('/publish_apply',methods = ['GET', 'POST'])
@main_info.main_info
def publish_apply():
    form = MyForm.MyForm_publish_apply()
    levels = []
    mails = app.config.get('LEADER_MAILS')
    sender = app.config.get('MAIL_DEFAULT_SENDER')
    types = {'new':'新增项目','bug': 'BUG修复'}
    if form.submit.data:
        Project_types = form.Project_types.data
        Project_describe = form.Project_describe.data
        Project_content = form.Project_content.data
        Front = form.Front.data
        Rollback_version = form.Rollback_version.data
        Project_config = form.Project_config.data
        db_project = db_op.project_level
        if Project_describe and Project_content and Rollback_version:
            try:
                for line in Project_content.splitlines():
                    if line.startswith('/'):
                        project = line.split('/')[2]
                        project_type = 'php'
                    elif line.endswith('.war.zip'):
                        project = line.split('-')[:-1]
                        project = '-'.join(project) + '.war'
                        project_type = 'java'
                    else:
                        raise flash('无效的项目版本路径!')
                    project_val = db_project.query.with_entities(db_project.level).filter(db_project.project == project).all()
                    if project_val:
                        levels.append(project_val[0][0])
                    else:
                        raise flash('没有找到%s该项目的等级记录!' %project_val[0][0])
                if len(set(levels))> 1:
                    raise flash('不同等级的项目需分批提交上线申请!')
                Project_level = levels[0]
                if Project_level < 7:
                        Leader = mails[project_type]
                if Project_level >=7:
                        Leader = mails['total']
                msg = Message("%s项目上线申请" %project, sender=sender, recipients=[Leader],cc=[sender,g.user])
                msg.html = '<p>1、项目等级:%s</p>' \
                           '<p>2、项目类型:%s</p>' \
                           '<p>3、项目变更描述:%s</p>' \
                           '<p>4、项目内容:</p>' \
                           '<p>%s</p>' \
                           '<p>5、前端相关项目是否上线?:%s</p>' \
                           '<p>6、回滚版本:</p>'\
                           '<p>%s</p>'\
                           '<p>7、线上资源配置及使用确认是否正确?:%s</p>' \
                           '<p>8、申请人:%s</p>' % (Project_level,types[Project_types],Project_describe,Project_content,Front,Rollback_version,Project_config,g.user)
                with app.app_context():
                    try:
                        mail.send(msg)
                    except Exception as e:
                        flash(e)
                        flash('上线申请邮件发送失败!')
                    else:
                        flash('上线申请邮件已发送给%s' %Leader)
                        db = db_op.project_apply
                        db_op.DB.session.add(db(project = project,types=types[Project_types],describe=Project_describe,content=Project_content,Rollback=Rollback_version,sender=g.user))
                        db_op.DB.session.commit()
            except Exception as e:
                flash(e)
            return render_template('Message_static.html',Main_Infos=g.main_infos)
    return render_template('publish_apply.html',Main_Infos=g.main_infos,form=form)
@page_publish_apply.before_request
@check.login_required(grade=10)
def check_login(error=None):
    produce.Async_log(g.user, request.url)
@page_publish_apply.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
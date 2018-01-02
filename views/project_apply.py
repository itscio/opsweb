#-*- coding: utf-8 -*-
from flask_mail import Mail
from flask_mail import Message
from flask import Blueprint,render_template,g,flash,request
from Modules import MyForm,check,db_op,produce,main_info,loging,Md5,php_publish
from sqlalchemy import and_
import time
import redis
import __init__
app = __init__.app
mail = Mail(app)
page_project_apply = Blueprint('project_apply',__name__)
mails = app.config.get('MAILS')
sender = app.config.get('MAIL_DEFAULT_SENDER')
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
Redis = redis.StrictRedis(host=redis_host, port=redis_port,password=redis_password,)
@page_project_apply.route('/project_apply',methods = ['GET', 'POST'])
@check.login_required(grade=10)
@main_info.main_info
def project_apply():
    form = MyForm.MyForm_project_apply()
    types = {'new':u'新增需求','bug':u'bug修复'}
    if form.submit.data:
        Project_types = form.Project_types.data
        Project_describe = form.Project_describe.data.strip()
        Project_content = form.Project_content.data.strip()
        Publish_conf = form.Publish_conf.data
        Front = form.Front.data
        Rollback_version = form.Rollback_version.data.strip()
        proposer = g.user
        if Project_describe and Project_content and Rollback_version:
            try:
                if Publish_conf == 'no':
                    raise flash('请确认资源配置是否正确?')
                if Project_content == Rollback_version:
                    raise flash('上线版本和回滚版本内容不能相同!')
                Projects = Project_content.splitlines()
                Rollback_version = Rollback_version.splitlines()
                if len(Projects) == 2 and len(Rollback_version) == 2:
                    Project = Projects[0].strip()
                    tag = Projects[1].strip()
                    if Project.endswith('git') or tag.startswith('tag'):
                        project = Project.split('/')[-1]
                        project = project.split('.')[0]
                    else:
                        raise flash('无效的路径格式!')
                else:
                    raise flash('无效的内容格式!')
                db_project_apply = db_op.project_apply
                VALS = db_project_apply.query.filter(and_(db_project_apply.content.like('{0};%'.format(Project)),db_project_apply.status <> '2')).all()
                if VALS:
                    raise flash('该项目已经提测，请勿重复提交!')
                db_project = db_op.project_level
                project_val = db_project.query.with_entities(db_project.level).filter(db_project.project == project).all()
                if project_val:
                    Project_level = int(project_val[0][0])
                else:
                    raise flash('没有找到%s项目的等级记录!' %project_val[0][0])
                Receiver = mails['test']
                msg = Message("%s项目提测申请" %project, sender=sender, recipients=[Receiver],cc=[sender])
                msg.html = '<p>1、项目等级:<strong>%s</strong></p>' \
                           '<p>2、项目类型:<strong>%s</strong></p>' \
                           '<p>3、项目描述:</p>'\
                           '<p><strong>%s</strong></p>' \
                           '<p>4、提测版本:</p>' \
                           '<p><strong>%s</strong></p>' \
                           '<p><strong>%s</strong></p>' \
                           '<p>5、前端相关项目是否上线?:<strong>%s</strong></p>' \
                           '<p>6、线上资源配置是否正确?:<strong>%s</strong></p>' \
                           '<p>7、回滚版本:</p>'\
                           '<p><strong>%s</strong></p>' \
                           '<p><strong>%s</strong></p>' \
                           '<p>8、申请人:<strong>%s</strong></p>' % (Project_level,types[Project_types],Project_describe,Projects[0].strip(),Projects[1].strip(),Front,Publish_conf,Rollback_version[0].strip(),Rollback_version[1].strip(),proposer)
                with app.app_context():
                    try:
                        mail.send(msg)
                    except Exception as e:
                        flash(e)
                        raise flash('提测申请邮件发送失败!')
                #执行预发布上线
                K = '%s_%s' % (g.user, g.secret_key)
                Key = '%s_publish_php' % K
                publish_key = '%s_publish_key' % K
                action = 'publish'
                Redis.lpush(Key, 'check security policy......')
                Redis.expire(Key, 30)
                Path = ';'.join(Projects).replace('http://', '')
                sip = ['172.16.1.246',]
                Gray = '0'
                Info = {}
                Info['action'] = action
                Info['path'] = Path
                Info['app'] = project
                Info['sip'] = sip
                Info['gray'] = Gray
                Redis.lpush(publish_key, Info)
                #记入数据库
                db = db_op.project_apply
                db_op.DB.session.add(db(project = project,types=types[Project_types],describe=Project_describe,content='%s;%s'%(Projects[0].strip(),Projects[1].strip()),Rollback='%s;%s'%(Rollback_version[0].strip(),Rollback_version[1].strip()),sender=proposer,status='0'))
                db_op.DB.session.commit()
                # 项目提测记录上线时间
                db_project = db_op.project_show
                tm = time.strftime('%Y%m%d', time.localtime())
                db_project.query.filter(db_project.project == project).update({db_project.test_time: tm})
                db_op.DB.session.commit()
                # 后台执行
                Scheduler = produce.Scheduler_publish()
                Scheduler = Scheduler.Scheduler_mem(php_publish.php_publish, publish_key, Key)
                Scheduler.start()
                Redis.lpush(Key, '    --->check pass!')
                Redis.lpush(Key, '-' * 80 + '\n')
                return render_template('php_publish_show.html', Main_Infos=g.main_infos)
            except Exception as e:
                loging.write(e)
                if 'old'not in str(e):
                    flash(e)
            return render_template('Message_static.html',Main_Infos=g.main_infos)
    return render_template('project_apply.html',Main_Infos=g.main_infos,form=form)
@page_project_apply.route('/project_apply_show')
@page_project_apply.route('/project_apply_show/<ID>')
@check.login_required(grade=10)
@main_info.main_info
def project_apply_show(ID=None):
    crypto_key = app.config.get('CRYPTO_KEY')
    crypto = Md5.crypto(crypto_key)
    db = db_op.project_apply
    if ID:
        if '&' in ID:
            id = crypto.decrypt(ID.split('&')[0])
            action = ID.split('&')[1].split('=')[-1]
            if action == 'fail':
                Infos = db.query.with_entities(db.project, db.describe, db.content, db.sender).filter(db.id == id).all()
                if Infos:
                    Infos = Infos[0]
                    Receiver = Infos[-1]
                    if '@' not in  Receiver:
                        Receiver = '%s@baihe.com' %Receiver
                    Content = Infos[2].split(';')
                    msg = Message("提测项目%s被退回" % Infos[0], sender=sender, recipients=[Receiver], cc=[sender])
                    msg.html = '<p>1、项目描述:</p>' \
                               '<p><strong>%s</strong></p>' \
                               '<p>2、提测版本:</p>' \
                               '<p><strong>%s</strong></p>' \
                               '<p><strong>%s</strong></p>'  % (Infos[1],Content[0],Content[1])
                    with app.app_context():
                        try:
                            mail.send(msg)
                        except Exception as e:
                            loging.write(e)
                        else:
                            db.query.filter(db.id == int(id)).update({db.status:'2'})
                            db_op.DB.session.commit()
        else:
            ID = crypto.decrypt(ID)
            Infos = db.query.with_entities(db.project, db.describe, db.content, db.Rollback).filter(db.id == ID).all()
            if Infos:
                Infos = Infos[0]
                Content = Infos[2].split(';')
                Rollback = Infos[-1].split(';')
                msg = Message("%s项目申请上线" % Infos[0], sender=sender, recipients=[sender], cc=[mails['leader']])
                msg.html = '<p>1、项目描述:</p>' \
                           '<p><strong>%s</strong></p>' \
                           '<p>2、上线版本:</p>' \
                           '<p><strong>%s</strong></p>' \
                           '<p><strong>%s</strong></p>' \
                           '<p>3、回滚版本:</p>' \
                           '<p><strong>%s</strong></p>' \
                           '<p><strong>%s</strong></p>' % (Infos[1], Content[0], Content[1],Rollback[0],Rollback[1])
                with app.app_context():
                    try:
                        mail.send(msg)
                    except Exception as e:
                        loging.write(e)
                    else:
                        db.query.filter(db.id == int(ID)).update({db.status: '1'})
                        db_op.DB.session.commit()
    tables = ('提测项目', '类别', '项目描述', '提测版本', '发起人', '后续操作')
    Vals = db.query.with_entities(db.id,db.project,db.types,db.describe,db.content,db.sender).filter(db.status == '0').order_by(db.id).all()
    projects =[]
    for info in [list(info) for info in Vals]:
        info[0]= (crypto.encrypt(info[0]),'%s&result=fail'%crypto.encrypt(info[0]))
        projects.append(info)
    return render_template('project_apply_show.html',Main_Infos=g.main_infos,projects = projects,tables=tables)
@page_project_apply.before_request
@check.login_required(grade=10)
def check_login(error=None):
    produce.Async_log(g.user, request.url)
@page_project_apply.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
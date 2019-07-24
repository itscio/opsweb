#-*- coding: utf-8 -*-
import importlib
from flask import Blueprint,render_template,g,flash,request
from module import user_auth,MyForm,loging,db_op,tools,db_idc
from sqlalchemy import and_
import time
import json
import conf
from flask_sqlalchemy import SQLAlchemy
app = conf.app
DB = SQLAlchemy(app)
logging = loging.Error()
page_deploy = Blueprint('deploy',__name__)
@page_deploy.route('/deploy',methods = ['GET', 'POST'])
def deploy():
    db_project = db_op.project_list
    form = MyForm.MyForm_deploy()
    #判断自有资源
    if form.submit.data:
        project = form.project.data
        domain = form.domain.data
        business_id = form.select_busi.data
        resource = form.select_resource.data
        dev = form.select_dev.data
        if project and resource and domain:
            try:
                    val = db_project.query.filter(db_project.project == project.strip()).all()
                    if val:
                        raise flash("%s项目已存在，如需修改项目部署列表，请在'资源变更'菜单下操作." %project, 'error')
                    else:
                        for source in resource:
                            #修改自有资源表
                            source = source.split(':')
                            db_project.query.filter(and_(db_project.resource==source[0],db_project.ip==source[1],db_project.ssh_port==source[2],db_project.app_port==source[3])).update({
                                db_project.project:project.strip(),db_project.domain:domain.strip(),db_project.business_id:int(business_id),db_project.sys_args:dev,db_project.env:'生产',db_project.gray:'0',db_project.status:'使用中',
                            db_project.update_date:time.strftime('%Y-%m-%d',time.localtime())})
                            db_op.DB.session.commit()
                            # 开始部署环境
                            # 配置负载均衡
                            # 配置dns解析
                            flash('%s:%s:%s:%s添加到项目部署列表成功!' % tuple(source))
            except Exception as e:
                flash(e)
        else:
            flash('所有输入框均为必填项!')
        return render_template('Message.html')
    #判断第三方资源
    if form.submit_third.data:
        db_third = db_idc.third_resource
        department = form.department.data
        person = form.person.data
        contact = form.contact.data
        thirds = form.select_third.data
        if thirds and department and contact and person:
            department = department.strip()
            contact = contact.strip()
            person = person.strip()
            for third in thirds:
                third = third.split(':')
                try:
                    #写入第三方资源表
                    db_third.query.filter(and_(db_third.resource_type==third[0],db_third.ip==third[1],db_third.ssh_port==third[2],db_third.app_port==third[3])).update({db_third.cluster_type:'',db_third.department:department,db_third.person:person,
                                                                                                                                                                        db_third.contact:contact,db_third.status:'使用中',db_third.busi_id:0,
                                                                                                                                                                        db_third.update_date:time.strftime('%Y-%m-%d',time.localtime())})
                    db_idc.DB.session.commit()
                except Exception as e:
                    logging.error(e)
                else:
                    flash('%s:%s:%s:%s环境分配录入完成' % tuple(third))
    importlib.reload(MyForm)
    form = MyForm.MyForm_deploy()
    return render_template('deploy.html',form=form)

@page_deploy.route('/new_business',methods = ['GET', 'POST'])
def new_business():
    db_business = db_op.business
    db_project = db_op.project_list
    db_project_other = db_op.project_other
    db_servers = db_idc.idc_servers
    form = MyForm.MyForm_deploy()
    Error = []
    Info = []
    BUSI = db_business.query.with_entities(db_business.id,db_business.business).all()
    BUSI = json.dumps([{"id": str(info[0]), "text": str(info[1])} for info in BUSI])
    if form.submit.data:
        business = form.business.data
        describe = form.describe.data
        person = form.person.data
        contact = form.contact.data
        resource = form.area_resource.data
        dev_type = form.select_dev.data
        project = form.project.data
        domain = form.domain.data
        try:
            if not business:
                raise Error.append("业务信息为不能为空!")
            business_id = db_business.query.with_entities(db_business.id).filter(db_business.business == business.strip()).all()
            if not business_id:
                if project:
                   if not project.endswith('.jar'):
                       if not resource or not describe:
                           raise Error.append("带*输入框均为必填项!")
                else:
                    raise Error.append("项目名称为不能为空!")
            #判断主机信息输入格式
            if ',' in  resource:
                infos = resource.split(',')
            else:
                infos = resource.splitlines()
            for info in infos:
                #判断是否带应用端口
                if ':' in info:
                    host,app_port = info.split(':')
                else:
                    host = info
                    app_port = None
                #判断是ip还是hostname
                if len(host.split('.')) > 3:
                    ips = db_servers.query.with_entities(db_servers.id,db_servers.ip, db_servers.ssh_port).filter(
                        db_servers.ip == host).all()
                else:
                    ips = db_servers.query.with_entities(db_servers.id,db_servers.ip, db_servers.ssh_port).filter(
                    db_servers.hostname == host).all()
                if ips:
                    server_id,ip, ssh_port = ips[0]
                    if not business_id:
                        #写入业务信息
                        c = db_business(business=business.strip(), describe=describe.strip(), person=person,contact=contact)
                        db_op.DB.session.add(c)
                        db_op.DB.session.commit()
                    #查询业务ID
                    new_id = db_business.query.with_entities(db_business.id).filter(db_business.business == business.strip()).all()
                    new_id = new_id[0][0]
                    update_date = time.strftime('%Y-%m-%d', time.localtime())
                    #判断是否正式项目
                    if app_port:
                        if dev_type == 'java':
                            sys_args = dev_type
                            dev_type = 'tomcat'
                        #写入正式项目数据库
                        exist_project = db_project.query.filter(db_project.project==project).all()
                        if exist_project:
                            Error.append("%s项目信息已存在!" %project)
                        else:
                            #判断域名信息
                            if domain:
                                c = db_project(resource=dev_type, project=project, domain=domain, ip=ip, ssh_port=ssh_port,
                                               app_port=app_port, business_id=new_id, sys_args=sys_args, env='生产', gray=0,
                                               status='使用中', update_date=update_date)
                                db_op.DB.session.add(c)
                                db_op.DB.session.commit
                            else:
                                Error.append("%s新项目需提供域名信息!" % project)
                    else:
                        exist_other = db_project_other.query.filter(db_project_other.project==project).all()
                        if exist_other:
                            db_project_other.query.filter(db_project_other.project==project).update({db_project_other.business_id:new_id})
                            db_op.DB.session.commit()
                        else:
                            #写入非正式项目数据库
                            c = db_project_other(lable=dev_type,project=project,server_id=server_id,business_id=new_id,update_time=update_date)
                            db_op.DB.session.add(c)
                            db_op.DB.session.commit()
                else:
                    Error.append("%s主机信息没有找到!" %host)
        except Exception as e:
            if 'old-style' not in str(e):
                logging.error(e)
        else:
            Info.append("%s业务相关信息录入完成." % business.strip())
    return render_template('new_business.html',form=form,Error=Error,Info=Info,BUSI=BUSI)
@page_deploy.before_request
@user_auth.login_required(grade=1)
def check_login(error=None):
    tools.Async_log(g.user, request.url)
    importlib.reload(MyForm)
@page_deploy.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
    db_idc.DB.session.remove()
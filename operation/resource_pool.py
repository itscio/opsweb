#-*- coding: utf-8 -*-
import importlib
from flask import Flask,Blueprint,render_template,g,flash,request
from module import MyForm,user_auth,loging,db_op,db_idc,tools
from sqlalchemy import distinct,and_,or_
from flask_sqlalchemy import SQLAlchemy
import redis
import time
app = Flask(__name__)
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/redis.conf')
logging = loging.Error()
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
Redis = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
page_resource_pool = Blueprint('resource_pool',__name__)
@page_resource_pool.route('/resource_pool',methods = ['GET', 'POST'])
@page_resource_pool.route('/resource_pool/<action>/<int:id>',methods = ['GET', 'POST'])
def resource_pool(action=None,id=None):
    importlib.reload(MyForm)
    form = MyForm.MyFromResourcePool()
    form_third = MyForm.MyFromThirdResource()
    db_project = db_op.project_list
    db_server = db_idc.idc_servers
    db_third = db_idc.third_resource
    db_project_third = db_op.project_third
    source_type = 'self'
    def recyle_resource(ip,ssh_port,app_port):
        try:
            project_id = db_project.query.with_entities(db_project.id).filter(and_(db_project.ip==ip,db_project.ssh_port==ssh_port,db_project.app_port==app_port)).all()
            third_id = db_third.query.with_entities(db_third.id).filter(and_(db_third.ip == ip, db_third.ssh_port == ssh_port, db_third.app_port == app_port)).all()
            if project_id or third_id:
                # 删除自有资源表信息
                v = db_project.query.filter(and_(db_project.ip==ip,db_project.ssh_port==ssh_port,db_project.app_port==app_port)).all()
                for c in v:
                    db_op.DB.session.delete(c)
                    db_op.DB.session.commit()
                # 删除第三方资源表信息
                v = db_third.query.filter(
                    and_(db_third.ip == ip, db_third.ssh_port == ssh_port, db_third.app_port == app_port)).all()
                for c in v:
                    db_idc.DB.session.delete(c)
                    db_idc.DB.session.commit()
                # 删除项目资源表信息
                if third_id:
                    third_id = third_id[0][0]
                    v = db_project_third.query.filter(db_project_third.third_id == third_id).all()
                    for c in v:
                        db_op.DB.session.delete(c)
                        db_op.DB.session.commit()
                if project_id:
                    project_id = project_id[0][0]
                    v = db_project_third.query.filter(db_project_third.project_id == project_id).all()
                    for c in v:
                        db_op.DB.session.delete(c)
                        db_op.DB.session.commit()
            # 判断该服务器资源不再被使用
            project_vals = db_project.query.filter(and_(db_project.ip == ip, db_project.ssh_port == ssh_port)).all()
            third_vals = db_third.query.filter(and_(db_third.ip == ip, db_third.ssh_port == ssh_port)).all()
            if not project_vals and not third_vals:
                # 资源自动回收
                db_server.query.filter(db_server.ip == ip, db_server.ssh_port == ssh_port).update({db_server.status: "未使用"})
                db_idc.DB.session.commit()
        except Exception as e:
            logging.error(e)
    tables = ['项目','域名','主机名','应用服务','应用端口','开发语言','部署环境','操作']
    third_tables = ['项目','应用服务', '集群类型', '主机名', '应用端口','操作']
    #默认项目列表展示
    project = db_project.query.with_entities(distinct(db_project.project)).limit(1)
    project = project[0][0]
    values = db_project.query.with_entities(db_project.id,db_project.project,db_project.domain,db_project.ip,
                                                        db_project.ssh_port, db_project.resource,db_project.app_port, db_project.sys_args,
                                                        db_project.env).filter(db_project.project == project).all()
    third_values = []
    third_indexs = []
    # 按照项目查找
    if tools.http_args(request,'project'):
        project = tools.http_args(request,'project')
        servers = db_server.query.with_entities(db_server.ip,db_server.ssh_port,db_server.hostname).all()
        servers = {'%s:%s'%(info[0],info[1]):info[2] for info in servers}
        values = db_project.query.with_entities(db_project.id,db_project.ip,
                                                db_project.ssh_port, db_project.resource, db_project.app_port,
                                                db_project.sys_args, db_project.env).filter(
            db_project.project == project).order_by(db_project.ip).all()
        if values:
            values = [list(val) for val in values if '%s:%s'%(val[1],val[2]) in servers ]
            for val in values:
                val.insert(3,servers['%s:%s'%(val[1],val[2])])
            values.insert(0, tables[1:])
        third_id = db_project_third.query.with_entities(db_project_third.third_id).filter(
            db_project_third.project == project).all()
        if third_id:
            third_id = tuple([val[0] for val in third_id])
            third_values = db_third.query.with_entities(db_third.id, db_third.resource_type, db_third.cluster_type,
                                                        db_third.ip, db_third.ssh_port, db_third.app_port).filter(
                db_third.id.in_(third_id)).order_by(db_third.resource_type).all()
            if third_values:
                third_values = [list(val) for val in third_values]
                for val in third_values:
                    val.insert(5, servers['%s:%s'%(val[3],val[4])])
                third_values.insert(0, third_tables[1:])
        return render_template('resource_info.html', values=values, third_values=third_values, project=project, third_indexs=third_indexs,form=form)
    # 按照应用服务查找
    if tools.http_args(request,'application'):
        app = tools.http_args(request,'application')
        app_id = tools.http_args(request,'application-id')
        tables = ['应用服务', '集群类型', '主机名', '应用端口']
        host_info = None
        values = []
        servers = db_server.query.with_entities(db_server.ip, db_server.ssh_port, db_server.hostname).all()
        servers = {'%s:%s' % (info[0], info[1]): info[2] for info in servers}
        if app_id:
            if app in ('tomcat', 'python','php'):
                host_info = db_project.query.with_entities(db_project.ip,db_project.ssh_port,db_project.app_port).filter(
                    db_project.id == app_id).all()
                if host_info:
                    host_info = [servers['%s:%s'%(host_info[0][0],host_info[0][1])],host_info[0][-1]]
                    third_id = db_project_third.query.with_entities(db_project_third.third_id).filter(
                        and_(db_project_third.project_id == app_id)).all()
                    if third_id:
                        third_id = [val[0] for val in third_id]
                        values = db_third.query.with_entities(db_third.id, db_third.resource_type, db_third.cluster_type,
                                                          db_third.ip, db_third.ssh_port, db_third.app_port).filter(
                        db_third.id.in_(tuple(third_id))).order_by(db_third.resource_type).all()
                        if values:
                            values = [list(val) for val in values]
            else:
                host_info = db_third.query.with_entities(db_third.ip,db_third.ssh_port, db_third.app_port).filter(
                    db_third.id == app_id).all()
                if host_info:
                    host_info = [servers['%s:%s' % (host_info[0][0], host_info[0][1])], host_info[0][-1]]
                    project_id = db_project_third.query.with_entities(db_project_third.project_id).filter(
                    and_(db_project_third.third_id == app_id)).all()
                    if project_id:
                        project_id = [val[0] for val in project_id]
                        values = db_project.query.with_entities(db_project.id, db_project.resource, db_project.ip,
                                                        db_project.ssh_port, db_project.app_port).filter(
                    db_project.id.in_(tuple(project_id))).order_by(db_project.resource).all()
                        if values:
                            values = [list(val) for val in values]
                            for i, vals in enumerate(values):
                                vals.insert(2, '非集群')
                                values[i] = vals
        else:
            if app in ('php', 'tomcat', 'python'):
                values = db_project.query.with_entities(db_project.id, db_project.resource, db_project.ip,
                                                        db_project.ssh_port, db_project.app_port).filter(
                    db_project.resource == app).order_by(db_project.ip).all()
                if values:
                    values = [list(val) for val in values]
                    for i, vals in enumerate(values):
                        vals.insert(2, '非集群')
                        values[i] = vals
            else:
                values = db_third.query.with_entities(db_third.id, db_third.resource_type, db_third.cluster_type,
                                                      db_third.ip, db_third.ssh_port, db_third.app_port).filter(
                    db_third.resource_type == app).order_by(db_third.ip).all()
                if values:
                    values = [list(val) for val in values]
        if values:
            for val in values:
                val.insert(5,servers['%s:%s'%(val[3],val[4])])
        return render_template('application_list.html', values=values, app=app, tables=tables, host_info=host_info,form=form)
    # 第三方资源回收接口
    if tools.http_args(request,'action') == 'recyle' and tools.http_args(request,'ip') and tools.http_args(request,'ssh_port') and tools.http_args(request,'app_port'):
        ip = tools.http_args(request,'ip')
        ssh_port = tools.http_args(request,'ssh_port')
        app_port = tools.http_args(request,'app_port')
        result = recyle_resource(ip, ssh_port, app_port)
        if result:
            flash(result)
        else:
            flash('%s %s %s 资源回收完成!' % (ip, ssh_port, app_port))
        return render_template('Message.html')
    #修改项目列表
    if action == 'del' and id:
        try:
            source_type = tools.http_args(request,'resource_type')
            if tools.http_args(request,'resource_type') == 'self':
                #修改自有资源列表
                db_project.query.filter(db_project.id == id).update({db_project.project: '', db_project.domain: '', db_project.sys_args: '',
                                                                     db_project.env: '', db_project.gray: '',
                                                                     db_project.status: '未分配',db_project.update_date:time.strftime('%Y-%m-%d',time.localtime())})
                db_op.DB.session.commit()
                # 删除项目资源表信息
                v = db_project_third.query.filter(db_project_third.project_id == id).all()
                for c in v:
                    db_op.DB.session.delete(c)
                    db_op.DB.session.commit()
                project = db_project.query.with_entities(db_project.project).filter(db_project.id == id).all()
                project= project[0][0]
            if tools.http_args(request,'resource_type') == 'third':
                #删除项目资源表信息
                v = db_project_third.query.filter(db_project_third.third_id == id).all()
                for c in v:
                    db_op.DB.session.delete(c)
                    db_op.DB.session.commit()
                project = db_project_third.query.with_entities(db_project_third.project).filter(db_project_third.third_id == id).all()
                project= project[0][0]
        except Exception as e:
            logging.error(e)
    #资源池预分配
    if form.submit_allot.data:
        servers = form.servers.data
        ip,ssh_port = servers.split(":")
        resource = form.resource.data
        app_port = form.app_port.data.strip()
        if app_port:
            #写入资源表
            if resource in ('php','tomcat','python','java'):
                c= db_project(resource=resource,project='',domain='',ip=ip,ssh_port=ssh_port,app_port=app_port,business_id='',sys_args='',env='',gray='',status='未分配',update_date=time.strftime('%Y-%m-%d',time.localtime()))
                db_op.DB.session.add(c)
                db_op.DB.session.commit()
            else:
                c= db_third(resource_type=resource,cluster_type='',ip=ip,ssh_port=ssh_port,app_port=app_port,busi_id=0,department='',person='',contact='',status='未分配',update_date=time.strftime('%Y-%m-%d',time.localtime()))
                db_idc.DB.session.add(c)
                db_idc.DB.session.commit()
            flash('%s应用资源预配成功!' %servers)
    #资源池资源加锁
    if form.submit_lcok.data:
        try:
            servers = form.servers.data
            ip,ssh_port = servers.split(":")
            project_vals = db_project.query.filter(and_(db_project.ip==ip,db_project.ssh_port == ssh_port)).all()
            third_vals = db_third.query.filter(and_(db_third.ip == ip, db_third.ssh_port == ssh_port)).all()
            if project_vals or third_vals:
                db_server.query.filter(and_(db_server.ip==ip,db_server.ssh_port==ssh_port)).update({db_server.status:'使用中'})
                db_idc.DB.session.commit()
            else:
                raise flash('%s该资源还未分配应用资源，不能锁定!' % servers)
        except Exception as e:
            logging.error(e)
        else:
            flash('%s资源将不能在分配应用服务!' %servers)
    #第三方资源回收
    if form_third.submit_recucle.data:
        hosts = form_third.hosts.data
        if hosts:
            hosts = hosts.splitlines()
            for host in hosts:
                if len(host.split(':')) == 3:
                    ip,ssh_port,app_port = host.split(':')
                    result = recyle_resource(ip, ssh_port, app_port)
                    if result:
                       flash(result)
                    else:
                        flash('%s %s %s 资源回收完成!' %(ip,ssh_port,app_port))
                else:
                    flash('%s格式不符合要求!' %host)
    #项目列表增加主机
    if form.submit_add.data:
        try:
            resource_val = form.hosts_add.data
            project = form.Project.data
            resource_val = resource_val.split(':')
            resource,app_port,ip,ssh_port = resource_val
            vals = db_project.query.with_entities(db_project.domain,db_project.sys_args).filter(and_(db_project.project==project,db_project.env=='生产')).limit(1)
            domain,sys_args = vals[0]
            #写入自有资源表
            db_project.query.filter(and_(db_project.resource==resource,db_project.ip==ip,db_project.ssh_port==ssh_port,db_project.app_port==app_port).update({db_project.project:project,
                                                                                                                                                              db_project.domain:domain,db_project.sys_args:sys_args,db_project.env:'生产',
                                                                                                                                                              db_project.gray:'0',db_project.status:'使用中',
                                                                                                                                                              db_project.update_date:time.strftime('%Y-%m-%d',time.localtime())}))
            db_op.DB.session.commit()
            #重新加载数据
            values = db_project.query.with_entities(db_project.id,db_project.project, db_project.domain, db_project.ip,
                                                    db_project.ssh_port, db_project.resource,db_project.app_port, db_project.sys_args,
                                                    db_project.env).filter(db_project.project == project).all()
        except Exception as e:
            logging.error(e)
    #项目列表查询
    if form.submit_query.data:
        source_type = form.source_type.data
        project = form.Project.data
        #数据初始化
        values = []
        try:
            #判断是否需要条件查找
            if source_type == 'self':
                values = db_project.query.with_entities(db_project.id, db_project.project, db_project.domain,
                                                        db_project.ip,
                                                        db_project.ssh_port, db_project.resource,
                                                        db_project.app_port, db_project.sys_args,
                                                        db_project.env).filter(db_project.project == project).all()
            if source_type == 'third':
                third_id = db_project_third.query.with_entities(db_project_third.third_id).filter(db_project_third.project == project).all()
                if third_id:
                    third_id = [id[0] for id in third_id]
                    third_values = db_third.query.with_entities(db_third.id,db_third.resource_type, db_third.cluster_type,
                                                            db_third.ip, db_third.ssh_port,db_third.app_port).filter(db_third.id.in_(tuple(third_id))).order_by(db_third.resource_type).all()
            if third_values:
                for i,t_val in enumerate(third_values):
                    t_val = list(t_val)
                    t_val.insert(1,project)
                    third_values[i] = t_val
        except Exception as e:
            flash(e)
    return render_template('resource_pool.html', form=form, form_third=form_third, tables=tables,third_tables=third_tables, values=values, third_values=third_values,source_type=source_type,project=project)

@page_resource_pool.route('/resource_modify',methods = ['GET', 'POST'])
def resource_modify():
    importlib.reload(MyForm)
    form = MyForm.FormResourceModify()
    INFOS = []
    if form.submit.data:
        try:
            resource = form.resource.data
            source_type = form.source_type.data
            action = form.action.data
            hosts = form.hosts.data
            app_port = form.app_port.data
            business = form.select_busi.data
            actions = {'add':'新增','del':'删除'}
            if resource and hosts and app_port:
                db_server = db_idc.idc_servers
                db_third = db_idc.third_resource
                db_business = db_op.business
                # 判断是否为第三方资源服务
                if resource.strip() in ('tomcat','php','python'):
                    raise INFOS.append('录入仅限于第三方资源服务!')
                # 获取业务相关信息
                busi = db_business.query.with_entities(db_business.person,db_business.contact).filter(db_business.id==int(business)).all()
                if busi:
                    person,contact = busi[0]
                else:
                    person=contact = None
                for host in hosts.splitlines():
                    # 判断主机是否存在
                    host = host.strip()
                    infos = db_server.query.with_entities(db_server.ip,db_server.ssh_port).filter(or_(db_server.hostname==host,db_server.ip==host)).all()
                    if infos:
                        ip,ssh_port = infos[0]
                        try:
                            # 增加资源信息操作
                            if action == 'add':
                                c = db_third(resource_type=resource, cluster_type=source_type, ip=ip,ssh_port=ssh_port,app_port=int(app_port.strip()),
                                             busi_id=int(business),department='', person=person, contact=contact, status='使用中', update_date='0000-00-00')
                                db_idc.DB.session.add(c)
                                db_idc.DB.session.commit()
                            # 删除资源信息操作
                            if action == 'del':
                                v = db_third.query.filter(and_(db_third.resource_type==resource,db_third.ip==ip,db_third.ssh_port==ssh_port,db_third.app_port==int(app_port.strip()))).all()
                                if v:
                                    for c in v:
                                        db_idc.DB.session.delete(c)
                                        db_idc.DB.session.commit()
                                else:
                                    raise INFOS.append("%s 没有找到相关资源服务信息" %host)
                        except Exception as e:
                            if 'old-style' not in str(e):
                                logging.error(e)
                            if not INFOS:
                                INFOS.append('执行操作发生异常!')
                        else:
                            INFOS.append("%s %s操作执行成功!" %(host,actions[action]))
                    else:
                        raise INFOS.append('%s 没有找到服务器信息!' %host)
            else:
                INFOS.append('输入框均需要填写信息!')
        except Exception as e:
            if 'old-style' not in str(e):
                logging.error(e)
            if not INFOS:
                INFOS.append('执行操作异常!')
    return render_template('resource_modify.html',form=form,INFOS=INFOS)

@page_resource_pool.route('/resource_query/<busi>/<app>')
def resource_query(busi=None,app=None):
    db_busi = db_op.business
    db_third = db_idc.third_resource
    db_project = db_op.project_list
    db_project_third = db_op.project_third
    db_server = db_idc.idc_servers
    db_idc_id =db_idc.idc_id
    idcs = db_idc_id.query.with_entities(db_idc_id.id,db_idc_id.aid).all()
    idcs = {int(val[0]):val[1] for val in idcs}
    busi_id = db_busi.query.with_entities(db_busi.id).filter(db_busi.business==busi).all()
    busi_id = busi_id[0][0]
    host_type = {'physical':'物理机','vm':'虚拟机'}
    tables = ['应用服务','应用端口','主机名','机房','主机类型','CPU核数','内存大小']
    try:
        if app in ('tomcat','php','python'):
            vals = db_project.query.with_entities(db_project.ip,db_project.app_port).filter(and_(db_project.resource==app,db_project.business_id==busi_id)).all()
        else:
            self_ids = db_project.query.with_entities(db_project.id).filter(db_project.business_id==busi_id).all()
            self_ids = tuple([int(id[0]) for id in self_ids])
            third_ids = db_project_third.query.with_entities(db_project_third.third_id).filter(db_project_third.project_id.in_(self_ids)).all()
            third_ids = tuple([int(id[0]) for id in third_ids])
            vals = db_third.query.with_entities(db_third.ip,db_third.app_port).filter(and_(db_third.id.in_(third_ids),db_third.resource_type==app)).all()
    except Exception as e:
        logging.error(e)
    try:
        values = [list(val) for val in vals]
        ips = tuple([ip[0] for ip in vals])
        servers = db_server.query.with_entities(db_server.ip,db_server.hostname,db_server.idc_id,db_server.host_type,db_server.cpu_core,db_server.mem).filter(db_server.ip.in_(ips)).all()
        servers = [list(val) for val in servers]
        for i,val in enumerate(servers):
            servers[i][2] = idcs[int(val[2])]
            servers[i][3] = host_type[val[3]]
        servers = {info[0]:info[1:] for info in servers}
    except Exception as e:
        logging.error(e)
    return render_template('resource_query.html',values=values,servers=servers,busi=busi,app=app,tables=tables)
@page_resource_pool.before_request
@user_auth.login_required(grade=1)
def check_login(error=None):
    tools.Async_log(g.user, request.url)
@page_resource_pool.teardown_request
def db_remove(error=None):
    db_idc.DB.session.remove()
    db_op.DB.session.remove()
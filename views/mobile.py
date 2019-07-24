#-*- coding: utf-8 -*-
from flask import Blueprint,render_template,request,g,redirect,url_for,make_response
from module import user_auth,db_op,loging,db_idc,MyForm,k8s_resource,tools,produce,Md5
import redis
import time
import conf
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func,and_,or_
from collections import defaultdict
from importlib import reload
app = conf.app
DB = SQLAlchemy(app)
logging = loging.Error()
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
webssh_url = app.config.get('WEBSSH_URL')
docker_registry = app.config.get('REGISTRY')
RC = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
redis_data = app.config.get('REDIS_DATA')
RC_CLUSTER = redis.StrictRedis(host=redis_data, port=redis_port,decode_responses=True)
page_mobile=Blueprint('mobile',__name__)
@page_mobile.route('/mobile/login',methods = ['GET', 'POST'])
def m_login():
    try:
        form = MyForm.MyForm_input()
        if form.submit.data:
            username = form.input.data
            password = form.passwd.data
            token = tools.Produce(24)
            db_sso = db_op.user_sso
            val = db_sso.query.with_entities(db_sso.realName,db_sso.dingunionid,db_sso.ticket).filter(db_sso.userName == username).all()
            if val and password == '%sok' %username:
                realName, dingunionid, ticket = val[0]
                app_resp = make_response(redirect(url_for('mobile.mobile')))
                app_resp.set_cookie('user', Md5.Md5_make(realName), path='/')
                app_resp.set_cookie('dingId', Md5.Md5_make(dingunionid), path='/')
                app_resp.set_cookie('ticket', Md5.Md5_make(ticket), path='/')
                app_resp.set_cookie('token', token, path='/')
                RC.set('OP_dingId_%s' % Md5.Md5_make(dingunionid), dingunionid)
                RC.set('OP_user_%s' % Md5.Md5_make(realName), realName)
                RC.set('OP_token_%s' % dingunionid, token)
                RC.set('OP_ticket_%s' % Md5.Md5_make(ticket), ticket)
                RC.set('OP_logout_ticket_%s' % ticket, ticket)
                return app_resp
    except Exception as e:
        logging.error(e)
    return render_template('mobile/m_login.html',form=form)

@page_mobile.route('/mobile')
@user_auth.login_required(grade=1)
def mobile():
    return render_template('mobile/m_index.html')

@page_mobile.route('/m_webssh')
@user_auth.login_required(grade=1)
def m_webssh():
    return render_template('mobile/m_webssh.html',url=webssh_url)

@page_mobile.route('/m_assets')
@user_auth.login_required(grade=1)
def m_assets():
    idcs = defaultdict()
    # 获取机房机柜信息
    db_idc_id = db_idc.idc_id
    db_hosts = db_idc.idc_servers
    values = db_idc_id.query.with_entities(db_idc_id.aid, func.count(db_idc_id.cid)).filter(db_idc_id.cid !='oss').group_by(db_idc_id.aid).all()
    values = [list(val) for val in values]
    keys = [val[0] for val in values]
    for val in values:
        try:
            # 获取指定机房机柜的服务器信息
            idc_id = db_idc_id.query.with_entities(db_idc_id.id).filter(db_idc_id.aid == val[0]).all()
            idc_id = tuple([id[0] for id in idc_id])
            # 统计物理服务器数量
            phost_count = db_hosts.query.with_entities(func.count(db_hosts.ip)).filter(
                and_(db_hosts.host_type == 'physical', db_hosts.idc_id.in_(idc_id))).all()
            # 获取虚拟机数量
            vhost_count = db_hosts.query.with_entities(func.count(db_hosts.ip)).filter(
                and_(db_hosts.host_type == 'vm', db_hosts.idc_id.in_(idc_id))).all()
            if phost_count or vhost_count:
                idcs[val[0]] = (int(val[-1])-1,vhost_count[0][0],phost_count[0][0])
        except Exception as e:
            logging.error(e)
    return render_template('mobile/m_assets.html',idcs=idcs,keys=keys)

@page_mobile.route('/m_assets_info/<host>')
@user_auth.login_required(grade=1)
def m_assets_info(host=None):
    Infos = defaultdict()
    if host:
        try:
            # 获取服务器硬件信息
            db_server = db_idc.idc_servers
            server_info = db_server.query.with_entities(db_server.ip,db_server.ssh_port,db_server.hostname,
                                                        db_server.host_type,db_server.cpu_core,
                                                        db_server.mem,db_server.disk_size,db_server.comment).filter(
                or_(db_server.ip == host,db_server.hostname == host)).all()
        except Exception as e:
            logging.error(e)
        else:
            if server_info:
                ip = server_info[0][0]
                ssh_port = int(server_info[0][1])
                table_info = ['主机名','类型','CPU', '内存', '磁盘','管理']
                Infos['server_info'] = [table_info, server_info[0]]
                try:
                    # 获取第三方资源信息
                    third_table = ['应用服务', '应用端口', '所属项目']
                    project_table = ['应用服务', '应用端口', '所属项目']
                    db_third = db_idc.third_resource
                    db_project = db_op.project_list
                    db_busi = db_op.business
                    db_project_third = db_op.project_third
                    busis = db_busi.query.with_entities(db_busi.id, db_busi.business).all()
                    busis = {int(busi[0]): busi[1] for busi in busis}
                    busis[0] = '未知业务'
                    project_third = db_project_third.query.with_entities(db_project_third.third_id,
                                                                         db_project_third.project).all()
                    if project_third:
                        project_third = {info[0]: info[1] for info in project_third}
                    third_info = db_third.query.with_entities(db_third.id, db_third.resource_type, db_third.app_port).filter(
                        and_(db_third.ip == ip, db_third.ssh_port == ssh_port, )).all()
                    if third_info:
                        third_info = [list(info) for info in third_info]
                        third_id = [info[0] for info in third_info]
                        for info in third_info:
                            if project_third:
                                if info[0] in project_third.keys():
                                    info.append(project_third[third_id[info[0]]])
                                else:
                                    info.append('')
                            else:
                                info.append('')
                            info.pop(0)
                        third_info.insert(0, third_table)
                        Infos['third_info'] = third_info
                except Exception as e:
                    logging.error(e)
                try:
                    # 获取自有资源信息
                    project_info = db_project.query.with_entities(db_project.resource, db_project.app_port,
                                                                  db_project.project).filter(
                        and_(db_project.ip == ip, db_project.ssh_port == ssh_port)).all()
                    if project_info:
                        project_info = [list(info) for info in project_info]
                        project_info.insert(0, project_table)
                        Infos['project_info'] = project_info
                except Exception as e:
                    logging.error(e)
    return render_template('mobile/m_assets_info.html',Infos=Infos)

@page_mobile.route('/m_alarm')
@user_auth.login_required(grade=1)
def m_alarm():
    try:
        whitelist = []
        Key = "op_alarm_load_whitelist"
        if RC_CLUSTER.exists(Key):
            whitelist = RC_CLUSTER.smembers(Key)
        infos = None
        if RC_CLUSTER.exists('op_zabbix_server_load_top'):
            infos = eval(RC_CLUSTER.get('op_zabbix_server_load_top'))
            if infos:
                infos = [info for info in infos if info[-1] >100]
    except Exception as e:
        logging.error(e)
    return render_template('mobile/m_alarm.html', infos=infos,whitelist=whitelist)

@page_mobile.route('/m_image_update')
@user_auth.login_required(grade=1)
def m_image_update():
    try:
        tools.Async_log(g.user, request.url)
        reload(MyForm)
        form = MyForm.Form_k8s_update()
        if form.submit.data:
            deployment = form.deployment.data
            version = form.version.data
            if version:
                new_image = "%s/%s:%s" % (docker_registry, deployment, version)
                new_replicas = form.replicas.data
                redis_key = 'op_k8s_update_%s' % time.strftime('%Y%m%d%H%M%S', time.localtime())
                Scheduler = produce.Scheduler_publish()
                Scheduler = Scheduler.Scheduler_mem(k8s_resource.object_update,
                                                    [new_image, new_replicas, version, redis_key, 'web'])
                Scheduler.start()
                return render_template('mobile/m_deploy_show.html', redis_key=redis_key)
    except Exception as e:
        logging.error(e)
    return render_template('mobile/m_k8s_update.html', form=form)

@page_mobile.before_request
def check_login(exception = None):
    try:
        tools.Async_log(g.user, request.url)
    except:
        pass

@page_mobile.teardown_request
def db_remove(exception):
    db_op.DB.session.remove()
    db_idc.DB.session.remove()
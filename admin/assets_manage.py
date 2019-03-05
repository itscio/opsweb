#-*- coding: utf-8 -*-
from flask import Blueprint,render_template,g,request,flash,redirect,url_for
from Modules import check,db_idc,loging,MyForm,produce,db_op,tools
from sqlalchemy import and_
import pyexcel
from tcpping import tcpping
import redis
import os
import importlib
from collections import defaultdict
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/sql.conf')
DB = SQLAlchemy(app)
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
Redis = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
logging = loging.Error()
page_assets_manage = Blueprint('assets_manage',__name__)
@page_assets_manage.route('/assets_manage',methods = ['GET', 'POST'])
def assets_manage():
    form = MyForm.MyForm_assets_manage()
    db_idc_id = db_idc.idc_id
    db_server = db_idc.idc_servers
    db_network = db_idc.idc_networks
    db_store = db_idc.idc_store
    db_third = db_idc.third_resource
    db_project = db_op.project_list
    db_zabbix = db_idc.zabbix_info
    db_project_third = db_op.project_third
    change_infos = defaultdict()
    #确认问题服务器已修复
    if tools.http_args(request,'key') and tools.http_args(request,'infos'):
        try:
            Redis.hdel(tools.http_args(request,'key'),tools.http_args(request,'infos'))
            Redis.sadd('server_ensure',tools.http_args(request,'infos'))
        except Exception as e:
            logging.error(e)
        finally:
            return redirect(url_for('index.index'))
    if tools.http_args(request,'mid') == 'assets_manage':
        if tools.http_args(request,'aid') and tools.http_args(request,'sid') and tools.http_args(request,'action'):
            if ':' in tools.http_args(request,'sid'):
                js_ip,js_ssh_port = tools.http_args(request,'sid').split(':')
                vals = db_server.query.with_entities(db_server.idc_id,db_server.idrac,db_server.purch_date,db_server.expird_date).filter(and_(db_server.ip==js_ip,db_server.ssh_port==js_ssh_port)).all()
                if vals:
                    idc_id,idrac,purch_date,expird_date = vals[0]
                    cids = db_idc_id.query.with_entities(db_idc_id.aid,db_idc_id.cid).filter(db_idc_id.id==idc_id).all()
                    if cids:
                        aid,cid = cids[0]
                        change_infos['aid'] = aid
                        change_infos['cid'] = cid
                        change_infos['idrac'] = idrac
                        change_infos['purch_date'] = purch_date
                        change_infos['expird_date'] = expird_date
                        change_infos['sid'] = tools.http_args(request,'sid')
            else:
                change_infos['aid'] = tools.http_args(request,'aid')
                change_infos['sid'] = tools.http_args(request,'sid')
            change_infos['action'] = tools.http_args(request,'action')
    if form.submit.data:
        try:
            aid = form.select_aid.data
            ips = form.text.data.strip()
            ips = set(ips.splitlines())
            rack = form.rack.data.strip()
            if rack:
                if not rack.endswith('机柜') and rack != 'KVM':
                    rack = '%s机柜' %rack
                rack.upper()
            action = form.select_action.data
            purch = form.purch.data
            expird = form.expird.data
            device = form.select_device.data
            idrac = form.idrac.data.strip()
            device_type = form.device_type.data.strip()
            fault = form.fault.data
            old_host = form.old_host.data
            #新增设备
            if action == 'add':
                if ips:
                    for info in ips:
                        if info:
                            if rack and purch and expird:
                                host_type = 'physical'
                                if rack == 'KVM':
                                    host_type = 'vm'
                                # 获取机房机柜信息
                                idc_id = db_idc_id.query.with_entities(db_idc_id.id).filter(and_(db_idc_id.aid == aid, db_idc_id.cid == rack)).all()
                                if not idc_id:
                                    c = db_idc_id(aid=aid, cid=rack)
                                    db_idc.DB.session.add(c)
                                    db_idc.DB.session.commit()
                                    idc_id = db_idc_id.query.with_entities(db_idc_id.id).filter(and_(db_idc_id.aid == aid, db_idc_id.cid == rack)).all()
                                idc_id = int(idc_id[0][0])
                                #判断是否为服务器
                                if device == 'server':
                                    if ':' in info:
                                        if len(info.split(':')) == 2:
                                            ip,ssh_port = info.split(':')
                                        else:
                                            raise flash('%s格式不符合要求!' %info)
                                    else:
                                        ip,ssh_port = (info.strip(),20443)
                                    #查询资产信息
                                    values = db_server.query.filter(and_(db_server.ip == ip,db_server.ssh_port == ssh_port)).all()
                                    if values:
                                        #获取自动发现信息
                                        discovery_values = db_server.query.filter(and_(db_server.ip == ip, db_server.ssh_port == ssh_port,db_server.status == '新发现')).all()
                                        #修改自动发现信息
                                        if discovery_values:
                                            if idc_id:
                                                db_server.query.filter(and_(db_server.ip == ip, db_server.ssh_port == ssh_port,db_server.status == '新发现')).update({db_server.idc_id:idc_id,db_server.status:'未使用',db_server.host_type:host_type,db_server.purch_date:purch,db_server.expird_date:expird,db_server.idrac:idrac})
                                                db_idc.DB.session.commit()
                                            flash('%s服务器上架成功!' % info)
                                        else:
                                            flash('%s服务器已存在!' % info)
                                    else:
                                        #添加资产信息
                                        if tcpping(host=ip, port=ssh_port, timeout=3):
                                            s = db_server(idc_id=idc_id,ip=ip,ssh_port=ssh_port,idrac=idrac,purch_date=purch,expird_date=expird,status='未使用',s_ip=None,host_type=host_type,hostname='',sn='',manufacturer='',productname='',system='',cpu_info='',cpu_core='',mem='',disk_count=0,disk_size='',comment='',)
                                            db_idc.DB.session.add(s)
                                            db_idc.DB.session.commit()
                                            flash('%s服务器上架成功!' %info)
                                        else:
                                            flash('运维平台尝试登录{0}的ssh端口失败,服务器不能上架!'.format(info))
                                #判断是否为网络设备
                                if device == 'network':
                                    if device_type and purch and expird:
                                        ip = info
                                        #查询资产信息
                                        values = db_network.query.filter(and_(db_network.ip == ip, db_network.idc_id == idc_id)).all()
                                        if values:
                                            raise flash('%s网络设备资产已存在!' % info)
                                        #添加资产信息
                                        v = db_network(idc_id=idc_id,type=device_type,ip=ip,redundance='是',purch_date=purch,expird_date=expird,status='使用中',comment='')
                                        db_idc.DB.session.add(v)
                                        db_idc.DB.session.commit()
                                        flash('%s网络设备上架成功!' % ip)
                                    else:
                                        raise flash('上架网络设备，设备型号不能为空!')
                                #判断是否为存储设备
                                if device == 'store':
                                    if device_type:
                                        ip = info
                                        #获取资产信息
                                        values = db_store.query.filter(and_(db_store.ip == ip,db_store.idc_id==idc_id)).all()
                                        if values:
                                            raise flash('%s存储设备资产已存在!' % info)
                                        #添加资产信息
                                        v = db_store(idc_id=idc_id,type=device_type,ip=ip,purch_date=purch,expird_date=expird,status='使用中',comment='')
                                        db_idc.DB.session.add(v)
                                        db_idc.DB.session.commit()
                                        flash('%s存储设备上架成功!' % ip)
                                    else:
                                        raise flash('上架存储设备，设备型号不能为空!')
                            else:
                                raise flash('必填项目不能为空!', 'error')
            #下架设备
            if action == 'down':
                if ips:
                    for info in ips:
                        if info:
                            idc_id =db_idc_id.query.with_entities(db_idc_id.id).filter(db_idc_id.aid == aid).all()
                            idc_id = tuple([id[0] for id in idc_id])
                            #判断为服务器删除
                            if device == 'server':
                                if ':' in info:
                                    if len(info.split(':')) == 2:
                                        ip, ssh_port = info.split(':')
                                    else:
                                        raise flash('%s格式不符合要求!' %info)
                                else:
                                    ip, ssh_port = (info, 20443)
                                server_values = db_server.query.filter(and_(db_server.ip == ip, db_server.ssh_port == ssh_port,db_server.idc_id.in_(idc_id))).all()
                                if server_values:
                                    #判断服务器是否在使用
                                    project_values = db_project.query.filter(and_(db_project.ip == ip,db_project.ssh_port == ssh_port,db_project.status=='使用中')).all()
                                    third_values = db_third.query.filter(and_(db_third.ip == ip, db_third.ssh_port == ssh_port,db_third.status=='使用中')).all()
                                    if project_values or third_values:
                                        raise flash('%s分配有应用资源,不能下架!' %info)
                                    #删除自有资源信息
                                    v = db_project.query.filter(and_(db_project.ip == ip, db_project.ssh_port == ssh_port)).all()
                                    for c in v:
                                        db_op.DB.session.delete(c)
                                        db_op.DB.session.commit()
                                    # 删除第三方资源信息
                                    v = db_third.query.filter(and_(db_third.ip == ip, db_third.ssh_port == ssh_port)).all()
                                    for c in v:
                                        db_idc.DB.session.delete(c)
                                        db_idc.DB.session.commit()
                                    # 删除zabbix信息
                                    v = db_zabbix.query.filter(and_(db_zabbix.ip == ip, db_zabbix.ssh_port == ssh_port)).all()
                                    for c in v:
                                        db_idc.DB.session.delete(c)
                                        db_idc.DB.session.commit()
                                    # 删除服务器信息
                                    v = db_server.query.filter(and_(db_server.ip == ip, db_server.ssh_port == ssh_port,db_server.idc_id.in_(idc_id))).all()
                                    for c in v:
                                        db_idc.DB.session.delete(c)
                                        db_idc.DB.session.commit()
                                    flash('%s服务器下架成功!' %info)
                                else:
                                    flash('%s资产没有找到!' %info)
                            else:
                                ip = info
                                #查询是否为网络设备
                                v_network = db_network.query.filter(and_(db_network.ip == ip,db_network.idc_id.in_(idc_id))).all()
                                v_store = db_store.query.filter(and_(db_store.ip == ip,db_store.idc_id.in_(idc_id))).all()
                                if v_network:
                                    for c in v_network:
                                        db_idc.DB.session.delete(c)
                                        db_idc.DB.session.commit()
                                    flash('%s网络设备下架成功!' %info)
                                #查询是否为存储设备
                                elif v_store:
                                    for c in v_store:
                                        db_idc.DB.session.delete(c)
                                        db_idc.DB.session.commit()
                                    flash('%s存储设备下架成功!' %info)
                                else:
                                    flash('%s资产没有找到!' %info)
            #修改设备信息
            if action == 'modify':
                if ips:
                    for info in ips:
                        if info:
                            #修改服务器信息
                            if device == 'server':
                                if ':' in info:
                                    if len(info.split(':')) == 2:
                                        ip, ssh_port = info.split(':')
                                    else:
                                        raise flash('%s格式不符合要求!' %info)
                                else:
                                    ip, ssh_port = (info, 20443)
                                #修改IP信息
                                if old_host:
                                    if ':' in old_host.strip():
                                        if len(old_host.split(':')) == 2:
                                            old_ip, old_ssh_port = old_host.split(':')
                                        else:
                                            raise flash('%s格式不符合要求!' % info)
                                    else:
                                        old_ip = old_host.strip()
                                        old_ssh_port = 20443
                                    if len(ips) == 1:
                                        if tcpping(host=ip, port=ssh_port, timeout=5):
                                            # 获取third_id
                                            third_id = db_third.query.with_entities(db_third.id).filter(and_(db_third.ip == ip, db_third.ssh_port == ssh_port)).all()
                                            # 清除项目资源表
                                            if third_id:
                                                v = db_project_third.query.filter(db_project_third.third_id == int(third_id[0][0])).all()
                                                if v:
                                                    for c in v:
                                                        db_op.DB.session.delete(c)
                                                        db_op.DB.session.commit()
                                            # 删除第三方资源信息
                                            v = db_third.query.filter(and_(db_third.ip == ip, db_third.ssh_port == ssh_port)).all()
                                            if v:
                                                for c in v:
                                                    db_idc.DB.session.delete(c)
                                                    db_idc.DB.session.commit()
                                            # 删除zabbix信息
                                            v = db_zabbix.query.filter(and_(db_zabbix.ip == ip, db_zabbix.ssh_port == ssh_port)).all()
                                            if v:
                                                for c in v:
                                                    db_idc.DB.session.delete(c)
                                                    db_idc.DB.session.commit()
                                            #修改自有资源信息
                                            db_project.query.filter(and_(db_project.ip == old_ip, db_project.ssh_port == old_ssh_port)).update({db_project.ip: ip, db_project.ssh_port: ssh_port})
                                            db_op.DB.session.commit()
                                            #删除新发现服务器信息
                                            v = db_server.query.filter(and_(db_server.ip == ip,db_server.ssh_port == ssh_port)).all()
                                            if v:
                                                for c in v:
                                                    db_idc.DB.session.delete(c)
                                                    db_idc.DB.session.commit()
                                            #修改服务器信息
                                            db_server.query.filter(and_(db_server.ip == old_ip,db_server.ssh_port == old_ssh_port)).update({db_server.ip: ip, db_server.ssh_port: ssh_port})
                                            db_idc.DB.session.commit()
                                        else:
                                            raise flash('运维平台尝试登录新IP{0}的ssh端口失败,服务器IP不能修改!'.format(ip))
                                    else:
                                        raise flash('修改服务器IP,新IP信息只能填写一行!', 'error')
                                values = db_server.query.filter(and_(db_server.ip == ip, db_server.ssh_port == ssh_port)).all()
                                if values:
                                    db_infos = {}
                                    if idrac:
                                        db_infos[db_server.idrac] = idrac
                                    if purch:
                                        db_infos[db_server.purch_date] = purch
                                    if expird:
                                        db_infos[db_server.expird_date] = expird
                                    if fault:
                                        db_infos[db_server.status] = '维护中'
                                    if db_infos:
                                        db_server.query.filter(and_(db_server.ip == ip, db_server.ssh_port == ssh_port)).update(db_infos)
                                    if rack:
                                        val = db_idc_id.query.filter(and_(db_idc_id.aid == aid,db_idc_id.cid == rack)).all()
                                        if not val:
                                            v = db_idc_id(aid=aid,cid=rack)
                                            db_idc.DB.session.add(v)
                                            db_idc.DB.session.commit()
                                        idc_id = db_idc_id.query.with_entities(db_idc_id.id).filter(and_(db_idc_id.aid == aid,db_idc_id.cid == rack)).all()
                                        idc_id =  int(idc_id[0][0])
                                        db_server.query.filter(and_(db_server.ip == ip, db_server.ssh_port == ssh_port)).update({db_server.idc_id:idc_id})

                                    try:
                                        db_idc.DB.session.commit()
                                    except Exception as e:
                                        flash(e,'error')
                                    else:
                                        flash('%s服务器信息修改成功!' % info)
                                else:
                                    flash('%s资产没有找到!' % info)
                            else:
                                #修改网络或者存储设备信息
                                ip = info
                                network_infos = {}
                                store_infos = {}
                                v_network = db_network.query.filter(and_(db_network.ip == ip)).all()
                                v_store = db_store.query.filter(and_(db_store.ip == ip)).all()
                                if v_network or v_store:
                                    if device_type:
                                        network_infos[db_network.type] = device_type
                                        store_infos[db_store.type] = device_type
                                    if purch:
                                        network_infos[db_network.purch_date] = purch
                                        store_infos[db_store.purch_date] = purch
                                    if expird:
                                        network_infos[db_network.expird_date] = expird
                                        store_infos[db_store.expird_date] = expird
                                    if network_infos and store_infos:
                                        db_network.query.filter(and_(db_network.aid == aid, db_network.ip == ip)).update(network_infos)
                                        db_store.query.filter(db_store.ip == ip).update(store_infos)
                                    if rack:
                                        val = db_idc_id.query.filter(and_(db_idc_id.aid == aid, db_idc_id.cid == rack)).all()
                                        if not val:
                                            v = db_idc_id(aid=aid, cid=rack)
                                            db_idc.DB.session.add(v)
                                            db_idc.DB.session.commit()
                                        idc_id = db_idc_id.query.with_entities(db_idc_id.id).filter(and_(db_idc_id.aid == aid, db_idc_id.cid == rack)).all()
                                        idc_id = int(idc_id[0][0])
                                        db_network.query.filter(and_(db_network.ip == ip)).update({db_network.idc_id:idc_id})
                                        db_store.query.filter(and_(db_store.ip == ip)).update({db_store.idc_id:idc_id})
                                    else:
                                        flash('%设备修改信息为空' %info)
                                    try:
                                        db_idc.DB.session.commit()
                                    except Exception as e:
                                        flash(e, 'error')
                                    else:
                                        flash('%s服务器信息修改成功!' %info)
                                else:
                                    raise flash('%s资产没有找到!' %info)
        except Exception as e:
            db_idc.DB.session.rollback()
            db_op.DB.session.rollback()
            if 'old' not in str(e):
                logging.error(e)
                flash(e)
        finally:
            return render_template('Message.html')
    return render_template('assets_manage.html',form=form,change_infos=change_infos)
@page_assets_manage.route('/assets_manage/upload',methods = ['POST'])
def upload():
    try:
        if request.files['File']:
            db_idc_id = db_idc.idc_id
            db_server = db_idc.idc_servers
            File = request.files['File']
            if File:
                if File.filename.endswith('.xlsx') or File.filename.endswith('.xls'):
                    file_path = "/tmp/%s" %File.filename
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    File.save(file_path)
                    records = pyexcel.iget_records(file_name=file_path)
                    for record in records:
                        try:
                            aid = record['idc']
                            rack = record['rack']
                            if not rack.endswith('机柜'):
                                rack = '%s机柜' % rack
                            rack.upper()
                            ip = record['ip']
                            ssh_port = record['ssh_port']
                            host_type = 'physical'
                            idrac = record['idrac']
                            purch = tools.format_day_date(record['purch_date'])
                            expird = tools.format_day_date(record['expird_date'])
                            if aid and rack and ip and purch and expird:
                                if not ssh_port:
                                    ssh_port = 20443
                                # 获取机房机柜信息
                                idc_id = db_idc_id.query.with_entities(db_idc_id.id).filter(
                                    and_(db_idc_id.aid == aid, db_idc_id.cid == rack)).all()
                                if not idc_id:
                                    c = db_idc_id(aid=aid, cid=rack)
                                    db_idc.DB.session.add(c)
                                    db_idc.DB.session.commit()
                                    idc_id = db_idc_id.query.with_entities(db_idc_id.id).filter(and_(db_idc_id.aid == aid, db_idc_id.cid == rack)).all()
                                idc_id = int(idc_id[0][0])
                                # 查询资产信息
                                values = db_server.query.filter(and_(db_server.ip == ip, db_server.ssh_port == ssh_port)).all()
                                if values:
                                    # 获取自动发现信息
                                    discovery_values = db_server.query.filter(
                                        and_(db_server.ip == ip, db_server.ssh_port == ssh_port,db_server.status == '新发现')).all()
                                    # 修改自动发现信息
                                    if discovery_values:
                                        if idc_id:
                                            db_server.query.filter(and_(db_server.ip == ip, db_server.ssh_port == ssh_port,
                                                                        db_server.status == '新发现')).update(
                                                {db_server.idc_id: idc_id, db_server.status: '未使用',
                                                 db_server.host_type: host_type, db_server.purch_date: purch,
                                                 db_server.expird_date: expird, db_server.idrac: idrac})
                                            db_idc.DB.session.commit()
                                        flash('%s:%s服务器上架成功!' %(ip,ssh_port))
                                    else:
                                        flash('%s:%s服务器已存在,录入失败!' %(ip,ssh_port))
                                else:
                                    # 添加资产信息
                                    if tcpping(host=ip, port=ssh_port, timeout=3):
                                        s = db_server(idc_id=idc_id, ip=ip, ssh_port=ssh_port, idrac=idrac, purch_date=purch,
                                                      expird_date=expird, status='未使用', s_ip=None, host_type=host_type,
                                                      hostname='', sn='', manufacturer='', productname='', system='',
                                                      cpu_info='', cpu_core='', mem='', disk_count=0, disk_size='',
                                                      comment='', )
                                        db_idc.DB.session.add(s)
                                        db_idc.DB.session.commit()
                                        flash('%s:%s服务器上架成功!' %(ip,ssh_port))
                                    else:
                                        flash('运维平台尝试登录%s的ssh端口%s失败,录入失败!'%(ip,ssh_port))
                            else:
                                flash("%s:%s相关录入信息不完整,录入失败!" %(ip,ssh_port),'error')
                        except Exception as e:
                            logging.error(e)
                            continue
                else:
                    flash("文件应为Excel格式文件!")
        else:
            return redirect(url_for('assets_manage.assets_manage'))
    except Exception as e:
        flash(e)
    finally:
        return render_template('Message.html')
@page_assets_manage.before_request
@check.login_required(grade=1)
def check_login(error=None):
    produce.Async_log(g.user, request.url)
    importlib.reload(MyForm)
@page_assets_manage.teardown_request
def db_remove(error=None):
    db_idc.DB.session.remove()
    db_op.DB.session.remove()
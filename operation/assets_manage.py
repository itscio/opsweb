#-*- coding: utf-8 -*-
from flask import Flask,Blueprint,render_template,g,request,flash,redirect,url_for
from module import user_auth,db_idc,loging,MyForm,db_op,tools
from sqlalchemy import and_
import pyexcel
from tcpping import tcpping
import redis
import os
import importlib
from collections import defaultdict
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/redis.conf')
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
Redis = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
logging = loging.Error()
page_assets_manage = Blueprint('assets_manage',__name__)
@page_assets_manage.route('/assets_manage',methods = ['GET', 'POST'])
def assets_manage():
    form = MyForm.MyFormAssetsManage()
    db_idc_id = db_idc.idc_id
    db_server = db_idc.idc_servers
    db_network = db_idc.idc_networks
    db_store = db_idc.idc_store
    db_third = db_idc.third_resource
    db_project = db_op.project_list
    db_zabbix = db_idc.zabbix_info
    db_project_third = db_op.project_third
    change_infos = defaultdict()
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
                if not rack.endswith('??????') and rack != 'KVM':
                    rack = '%s??????' %rack
                rack.upper()
            action = form.select_action.data
            purch = form.purch.data
            expird = form.expird.data
            device = form.select_device.data
            idrac = form.idrac.data.strip()
            device_type = form.device_type.data.strip()
            fault = form.fault.data
            old_host = form.old_host.data
            #????????????
            if action == 'add':
                if ips:
                    for info in ips:
                        if info:
                            if rack and purch and expird:
                                host_type = 'physical'
                                if rack == 'KVM':
                                    host_type = 'vm'
                                # ????????????????????????
                                idc_id = db_idc_id.query.with_entities(db_idc_id.id).filter(and_(db_idc_id.aid == aid, db_idc_id.cid == rack)).all()
                                if not idc_id:
                                    c = db_idc_id(aid=aid, cid=rack)
                                    db_idc.DB.session.add(c)
                                    db_idc.DB.session.commit()
                                    idc_id = db_idc_id.query.with_entities(db_idc_id.id).filter(and_(db_idc_id.aid == aid, db_idc_id.cid == rack)).all()
                                idc_id = int(idc_id[0][0])
                                #????????????????????????
                                if device == 'server':
                                    if ':' in info:
                                        if len(info.split(':')) == 2:
                                            ip,ssh_port = info.split(':')
                                        else:
                                            raise flash('%s?????????????????????!' %info)
                                    else:
                                        ip,ssh_port = (info.strip(),20443)
                                    #??????????????????
                                    values = db_server.query.filter(and_(db_server.ip == ip,db_server.ssh_port == ssh_port)).all()
                                    if values:
                                        #????????????????????????
                                        discovery_values = db_server.query.filter(and_(db_server.ip == ip, db_server.ssh_port == ssh_port,db_server.status == '?????????')).all()
                                        #????????????????????????
                                        if discovery_values:
                                            if idc_id:
                                                db_server.query.filter(and_(db_server.ip == ip, db_server.ssh_port == ssh_port,db_server.status == '?????????')).update({db_server.idc_id:idc_id,db_server.status:'?????????',db_server.host_type:host_type,db_server.purch_date:purch,db_server.expird_date:expird,db_server.idrac:idrac})
                                                db_idc.DB.session.commit()
                                            flash('%s?????????????????????!' % info)
                                        else:
                                            flash('%s??????????????????!' % info)
                                    else:
                                        #??????????????????
                                        if tcpping(host=ip, port=ssh_port, timeout=3):
                                            s = db_server(idc_id=idc_id,ip=ip,ssh_port=ssh_port,idrac=idrac,purch_date=purch,expird_date=expird,status='?????????',s_ip=None,host_type=host_type,hostname='',sn='',manufacturer='',productname='',system='',cpu_info='',cpu_core='',mem='',disk_count=0,disk_size='',comment='',)
                                            db_idc.DB.session.add(s)
                                            db_idc.DB.session.commit()
                                            flash('%s?????????????????????!' %info)
                                        else:
                                            flash('????????????????????????{0}???ssh????????????,?????????????????????!'.format(info))
                                #???????????????????????????
                                if device == 'network':
                                    if device_type and purch and expird:
                                        ip = info
                                        #??????????????????
                                        values = db_network.query.filter(and_(db_network.ip == ip, db_network.idc_id == idc_id)).all()
                                        if values:
                                            raise flash('%s???????????????????????????!' % info)
                                        #??????????????????
                                        v = db_network(idc_id=idc_id,type=device_type,ip=ip,redundance='???',purch_date=purch,expird_date=expird,status='?????????',comment='')
                                        db_idc.DB.session.add(v)
                                        db_idc.DB.session.commit()
                                        flash('%s????????????????????????!' % ip)
                                    else:
                                        raise flash('?????????????????????????????????????????????!')
                                #???????????????????????????
                                if device == 'store':
                                    if device_type:
                                        ip = info
                                        #??????????????????
                                        values = db_store.query.filter(and_(db_store.ip == ip,db_store.idc_id==idc_id)).all()
                                        if values:
                                            raise flash('%s???????????????????????????!' % info)
                                        #??????????????????
                                        v = db_store(idc_id=idc_id,type=device_type,ip=ip,purch_date=purch,expird_date=expird,status='?????????',comment='')
                                        db_idc.DB.session.add(v)
                                        db_idc.DB.session.commit()
                                        flash('%s????????????????????????!' % ip)
                                    else:
                                        raise flash('?????????????????????????????????????????????!')
                            else:
                                raise flash('????????????????????????!', 'error')
            #????????????
            if action == 'down':
                if ips:
                    for info in ips:
                        if info:
                            idc_id =db_idc_id.query.with_entities(db_idc_id.id).filter(db_idc_id.aid == aid).all()
                            idc_id = tuple([id[0] for id in idc_id])
                            #????????????????????????
                            if device == 'server':
                                if ':' in info:
                                    if len(info.split(':')) == 2:
                                        ip, ssh_port = info.split(':')
                                    else:
                                        raise flash('%s?????????????????????!' %info)
                                else:
                                    ip, ssh_port = (info, 20443)
                                server_values = db_server.query.filter(and_(db_server.ip == ip, db_server.ssh_port == ssh_port,db_server.idc_id.in_(idc_id))).all()
                                if server_values:
                                    #??????????????????????????????
                                    project_values = db_project.query.filter(and_(db_project.ip == ip,db_project.ssh_port == ssh_port,db_project.status=='?????????')).all()
                                    third_values = db_third.query.filter(and_(db_third.ip == ip, db_third.ssh_port == ssh_port,db_third.status=='?????????')).all()
                                    if project_values or third_values:
                                        raise flash('%s?????????????????????,????????????!' %info)
                                    #????????????????????????
                                    v = db_project.query.filter(and_(db_project.ip == ip, db_project.ssh_port == ssh_port)).all()
                                    for c in v:
                                        db_op.DB.session.delete(c)
                                        db_op.DB.session.commit()
                                    # ???????????????????????????
                                    v = db_third.query.filter(and_(db_third.ip == ip, db_third.ssh_port == ssh_port)).all()
                                    for c in v:
                                        db_idc.DB.session.delete(c)
                                        db_idc.DB.session.commit()
                                    # ??????zabbix??????
                                    v = db_zabbix.query.filter(and_(db_zabbix.ip == ip, db_zabbix.ssh_port == ssh_port)).all()
                                    for c in v:
                                        db_idc.DB.session.delete(c)
                                        db_idc.DB.session.commit()
                                    # ?????????????????????
                                    v = db_server.query.filter(and_(db_server.ip == ip, db_server.ssh_port == ssh_port,db_server.idc_id.in_(idc_id))).all()
                                    for c in v:
                                        db_idc.DB.session.delete(c)
                                        db_idc.DB.session.commit()
                                    flash('%s?????????????????????!' %info)
                                else:
                                    flash('%s??????????????????!' %info)
                            else:
                                ip = info
                                #???????????????????????????
                                v_network = db_network.query.filter(and_(db_network.ip == ip,db_network.idc_id.in_(idc_id))).all()
                                v_store = db_store.query.filter(and_(db_store.ip == ip,db_store.idc_id.in_(idc_id))).all()
                                if v_network:
                                    for c in v_network:
                                        db_idc.DB.session.delete(c)
                                        db_idc.DB.session.commit()
                                    flash('%s????????????????????????!' %info)
                                #???????????????????????????
                                elif v_store:
                                    for c in v_store:
                                        db_idc.DB.session.delete(c)
                                        db_idc.DB.session.commit()
                                    flash('%s????????????????????????!' %info)
                                else:
                                    flash('%s??????????????????!' %info)
            #??????????????????
            if action == 'modify':
                if ips:
                    for info in ips:
                        if info:
                            #?????????????????????
                            if device == 'server':
                                if ':' in info:
                                    if len(info.split(':')) == 2:
                                        ip, ssh_port = info.split(':')
                                    else:
                                        raise flash('%s?????????????????????!' %info)
                                else:
                                    ip, ssh_port = (info, 20443)
                                #??????IP??????
                                if old_host:
                                    if ':' in old_host.strip():
                                        if len(old_host.split(':')) == 2:
                                            old_ip, old_ssh_port = old_host.split(':')
                                        else:
                                            raise flash('%s?????????????????????!' % info)
                                    else:
                                        old_ip = old_host.strip()
                                        old_ssh_port = 20443
                                    if len(ips) == 1:
                                        if tcpping(host=ip, port=ssh_port, timeout=5):
                                            # ??????third_id
                                            third_id = db_third.query.with_entities(db_third.id).filter(and_(db_third.ip == ip, db_third.ssh_port == ssh_port)).all()
                                            # ?????????????????????
                                            if third_id:
                                                v = db_project_third.query.filter(db_project_third.third_id == int(third_id[0][0])).all()
                                                if v:
                                                    for c in v:
                                                        db_op.DB.session.delete(c)
                                                        db_op.DB.session.commit()
                                            # ???????????????????????????
                                            v = db_third.query.filter(and_(db_third.ip == ip, db_third.ssh_port == ssh_port)).all()
                                            if v:
                                                for c in v:
                                                    db_idc.DB.session.delete(c)
                                                    db_idc.DB.session.commit()
                                            # ??????zabbix??????
                                            v = db_zabbix.query.filter(and_(db_zabbix.ip == ip, db_zabbix.ssh_port == ssh_port)).all()
                                            if v:
                                                for c in v:
                                                    db_idc.DB.session.delete(c)
                                                    db_idc.DB.session.commit()
                                            #????????????????????????
                                            db_project.query.filter(and_(db_project.ip == old_ip, db_project.ssh_port == old_ssh_port)).update({db_project.ip: ip, db_project.ssh_port: ssh_port})
                                            db_op.DB.session.commit()
                                            #??????????????????????????????
                                            v = db_server.query.filter(and_(db_server.ip == ip,db_server.ssh_port == ssh_port)).all()
                                            if v:
                                                for c in v:
                                                    db_idc.DB.session.delete(c)
                                                    db_idc.DB.session.commit()
                                            #?????????????????????
                                            db_server.query.filter(and_(db_server.ip == old_ip,db_server.ssh_port == old_ssh_port)).update({db_server.ip: ip, db_server.ssh_port: ssh_port})
                                            db_idc.DB.session.commit()
                                        else:
                                            raise flash('???????????????????????????IP{0}???ssh????????????,?????????IP????????????!'.format(ip))
                                    else:
                                        raise flash('???????????????IP,???IP????????????????????????!', 'error')
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
                                        db_infos[db_server.status] = '?????????'
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
                                        flash('%s???????????????????????????!' % info)
                                else:
                                    flash('%s??????????????????!' % info)
                            else:
                                #????????????????????????????????????
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
                                        flash('%????????????????????????' %info)
                                    try:
                                        db_idc.DB.session.commit()
                                    except Exception as e:
                                        flash(e, 'error')
                                    else:
                                        flash('%s???????????????????????????!' %info)
                                else:
                                    raise flash('%s??????????????????!' %info)
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
                            if not rack.endswith('??????'):
                                rack = '%s??????' % rack
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
                                # ????????????????????????
                                idc_id = db_idc_id.query.with_entities(db_idc_id.id).filter(
                                    and_(db_idc_id.aid == aid, db_idc_id.cid == rack)).all()
                                if not idc_id:
                                    c = db_idc_id(aid=aid, cid=rack)
                                    db_idc.DB.session.add(c)
                                    db_idc.DB.session.commit()
                                    idc_id = db_idc_id.query.with_entities(db_idc_id.id).filter(and_(db_idc_id.aid == aid, db_idc_id.cid == rack)).all()
                                idc_id = int(idc_id[0][0])
                                # ??????????????????
                                values = db_server.query.filter(and_(db_server.ip == ip, db_server.ssh_port == ssh_port)).all()
                                if values:
                                    # ????????????????????????
                                    discovery_values = db_server.query.filter(
                                        and_(db_server.ip == ip, db_server.ssh_port == ssh_port,db_server.status == '?????????')).all()
                                    # ????????????????????????
                                    if discovery_values:
                                        if idc_id:
                                            db_server.query.filter(and_(db_server.ip == ip, db_server.ssh_port == ssh_port,
                                                                        db_server.status == '?????????')).update(
                                                {db_server.idc_id: idc_id, db_server.status: '?????????',
                                                 db_server.host_type: host_type, db_server.purch_date: purch,
                                                 db_server.expird_date: expird, db_server.idrac: idrac})
                                            db_idc.DB.session.commit()
                                        flash('%s:%s?????????????????????!' %(ip,ssh_port))
                                    else:
                                        flash('%s:%s??????????????????,????????????!' %(ip,ssh_port))
                                else:
                                    # ??????????????????
                                    if tcpping(host=ip, port=ssh_port, timeout=3):
                                        s = db_server(idc_id=idc_id, ip=ip, ssh_port=ssh_port, idrac=idrac, purch_date=purch,
                                                      expird_date=expird, status='?????????', s_ip=None, host_type=host_type,
                                                      hostname='', sn='', manufacturer='', productname='', system='',
                                                      cpu_info='', cpu_core='', mem='', disk_count=0, disk_size='',
                                                      comment='', )
                                        db_idc.DB.session.add(s)
                                        db_idc.DB.session.commit()
                                        flash('%s:%s?????????????????????!' %(ip,ssh_port))
                                    else:
                                        flash('????????????????????????%s???ssh??????%s??????,????????????!'%(ip,ssh_port))
                            else:
                                flash("%s:%s???????????????????????????,????????????!" %(ip,ssh_port),'error')
                        except Exception as e:
                            logging.error(e)
                            continue
                else:
                    flash("????????????Excel????????????!")
        else:
            return redirect(url_for('assets_manage.assets_manage'))
    except Exception as e:
        flash(e)
    finally:
        return render_template('Message.html')
@page_assets_manage.before_request
@user_auth.login_required(grade=1)
def check_login(error=None):
    tools.Async_log(g.user, request.url)
    importlib.reload(MyForm)
@page_assets_manage.teardown_request
def db_remove(error=None):
    db_idc.DB.session.remove()
    db_op.DB.session.remove()
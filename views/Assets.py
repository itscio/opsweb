#-*- coding: utf-8 -*-
from flask import Blueprint,render_template,g,request,flash,redirect,session,send_file
from sqlalchemy import func
import redis
from Modules import check,db_idc,db_op,loging,MyForm,produce,tools
from sqlalchemy import distinct,and_
from collections import defaultdict
import time,datetime
from pyecharts import Bar
from flask import Flask
import pyexcel
import os
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)
app.config.from_pyfile('../conf/sql.conf')
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/redis.conf')
logging = loging.Error()
page_Assets = Blueprint('Assets',__name__)
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
Redis = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
tt = time.strftime('%Y-%m-%d', time.localtime())
dt = datetime.datetime.now() + datetime.timedelta(days=30)
dt = dt.strftime('%Y-%m-%d')
@page_Assets.route('/assets_get',methods = ['GET', 'POST'])
@page_Assets.route('/assets_get/<action>',methods = ['GET', 'POST'])
@check.login_required(grade=4)
def assets_get(action=None):
    #公共参数
    Args = {info:tools.http_args(request,info) for info in ('aid','ip','port','type','host_type','action','page','hostname')}
    search_key = 'search_results_%s' % g.token
    form = MyForm.MyForm_server()
    db = db_idc.idc_servers
    db_idc_id = db_idc.idc_id
    db_zabbix = db_idc.zabbix_info
    idc_vals = db_idc_id.query.with_entities(db_idc_id.id, db_idc_id.aid,db_idc_id.cid).all()
    idc_val = {val[0]: val[1] for val in idc_vals}
    cid_val = {val[0]: val[-1] for val in idc_vals}
    values = []
    tables = ['机房','机柜','IP', 'ssh端口', '主机名', '服务器型号', '操作系统', 'CPU', '内存', '磁盘数', '磁盘总量', '远程管理IP','购买日期','状态']
    try:
        # 导出数据功能
        if action:
            if action == 'export':
                try:
                    file_name = "/tmp/export_assets.xlsx"
                    values = [list(val) for val in eval(Redis.get(search_key))]
                    if os.path.exists(file_name):
                        os.remove(file_name)
                    pyexcel.save_as(array=values, dest_file_name=file_name,sheet_name='export_assets')
                except Exception as e:
                    logging.error(e)
                else:
                    return send_file(file_name, as_attachment=True)
        # 判断是否查询
        if form.submit.data:
            ts = form.text.data.strip()
            Infos = {'ip': db.ip, 'sn': db.sn, 'hostname': db.hostname, 'status': db.status}
            if ts:
                try:
                    if form.select.data == 'cid':
                        cid = ts.strip()
                        if not ts.endswith('机柜') and cid != 'KVM':
                            cid = '%s机柜'%ts.strip()
                        # 优先进行精确匹配
                        idc_id = db_idc_id.query.with_entities(db_idc_id.id).filter(db_idc_id.cid == cid).all()
                        if not idc_id:
                            # 精确匹配不到结果后进行模糊匹配
                            idc_id = db_idc_id.query.with_entities(db_idc_id.id).filter(db_idc_id.cid.like('%{0}%'.format(cid))).all()
                        idc_id = tuple([id[0] for id in idc_id])
                        values = db.query.with_entities(db.idc_id, db.ip, db.ssh_port, db.hostname,
                                                        db.productname, db.system, db.cpu_core, db.mem, db.disk_count,
                                                        db.disk_size, db.idrac,db.purch_date, db.status).filter(db.idc_id.in_(idc_id)).all()
                    if form.select.data == 'buy_date':
                        start_time = ts.split('to')[0].strip()
                        end_time = ts.split('to')[-1].strip()
                        values = db.query.with_entities(db.idc_id, db.ip, db.ssh_port, db.hostname,
                                                            db.productname, db.system, db.cpu_core, db.mem,
                                                            db.disk_count, db.disk_size, db.idrac, db.purch_date,db.status).filter(and_(db.purch_date>=start_time,db.purch_date <= end_time,db.host_type=='physical')).all()
                    if form.select.data in ('sn','hostname','ip','status'):
                        val = db.query.with_entities(db.ip,db.ssh_port).filter(Infos[form.select.data] == ts).all()
                        #优先进行精确匹配
                        if val and len(val) == 1:
                            ip,ssh_port = val[0]
                            return redirect("assets_get?type=server&ip=%s&port=%s"%(ip,ssh_port))
                        else:
                            #精确匹配不到结果后进行模糊匹配
                            values = db.query.with_entities(db.idc_id, db.ip, db.ssh_port, db.hostname,
                                                                db.productname, db.system, db.cpu_core, db.mem,
                                                                db.disk_count, db.disk_size, db.idrac,db.purch_date, db.status).filter(Infos[form.select.data].like('%{0}%'.format(ts))).all()
                except Exception as e:
                    logging.error(e)
                else:
                    try:
                    #获取服务器信息
                        if values:
                            values = [list(val) for val in values]
                            for val in values:
                                id = val[0]
                                val[0] = idc_val[id]
                                val.insert(1,cid_val[id])
                            export_values = values
                            export_values.insert(0, tables)
                            Redis.set(search_key, export_values)
                    except Exception as e:
                        logging.error(e)
                    return render_template('server_list.html', values=values, tables=tables,form=form,export=True,assets_type = 'server')
        #获取API接口参数
        if Args:
            try:
                if Args['aid']:
                    aid = Args['aid']
                    idc_ids = db_idc_id.query.with_entities(db_idc_id.id).filter(db_idc_id.aid == aid).all()
                    if idc_ids:
                        idc_ids = tuple([val[0] for val in idc_ids])
                else:
                    idc_ids = db_idc_id.query.with_entities(db_idc_id.id).all()
                    if idc_ids:
                        idc_ids = tuple([val[0] for val in idc_ids])
            except Exception as e:
                logging.error(e)
            #判断是否为服务器
            if Args['type']=='server':
                if Args['action']:
                    try:
                        action = Args['action']
                        if action == 'all_list':
                            if Args['host_type']:
                                host_type = Args['host_type']
                                if idc_ids:
                                    values = db.query.with_entities(db.idc_id,db.ip, db.ssh_port, db.hostname, db.productname,db.system, db.cpu_core, db.mem,db.disk_count,db.disk_size,db.idrac,db.purch_date,db.status).filter(and_(db.idc_id.in_(idc_ids), db.host_type == host_type)).all()
                        if action == 'expire':
                            values = db.query.with_entities(db.idc_id,db.ip, db.ssh_port, db.hostname, db.productname,
                                                            db.system, db.cpu_core, db.mem, db.disk_count,db.disk_size, db.idrac,db.purch_date,
                                                            db.status).filter(
                                and_(db.host_type == 'physical', db.expird_date < tt,db.idc_id !=0)).order_by(db.idc_id).all()
                        if action == 'about_to':
                            values = db.query.with_entities(db.idc_id,db.ip, db.ssh_port, db.hostname, db.productname,
                                                            db.system, db.cpu_core, db.mem, db.disk_count,db.disk_size, db.idrac,db.purch_date,
                                                            db.status).filter(
                                and_(db.host_type == 'physical', db.expird_date >= tt,db.expird_date <= dt,db.idc_id !=0)).order_by(db.idc_id).all()
                        if action == 'search':
                            if Redis.exists(search_key):
                                values = eval(Redis.get(search_key))
                        if values:
                            Redis.set(search_key, values)
                            values = [list(val) for val in values]
                            for val in values:
                                id = val[0]
                                val[0] = idc_val[id]
                                val.insert(1,cid_val[id])
                    except Exception as e:
                        logging.error(e)
                    return render_template('server_list.html', values=values, tables=tables,form=form,export=True,assets_type = Args['type'])
                if (Args['ip'] and Args['port']) or Args['hostname']:
                    try:
                        total_infos = defaultdict()
                        ip = Args['ip']
                        ssh_port = Args['port']
                        hostname = Args['hostname']
                        total_infos['ssh_port'] = ssh_port
                        #获取服务器硬件信息
                        db_server = db_idc.idc_servers
                        if ip and ssh_port:
                            total_infos['ip'] = ip
                            server_info = db_server.query.with_entities(db_server.idc_id,db_server.ip,db_server.ssh_port,db_server.s_ip,db_server.host_type,db_server.hostname,
                                                                    db_server.sn,db_server.manufacturer,db_server.productname,db_server.system,db_server.cpu_info,
                                                                    db_server.cpu_core,db_server.mem,db_server.disk_count,db_server.disk_size,db_server.idrac,db_server.purch_date,db_server.expird_date,
                                                                    db_server.status,db_server.comment).filter(and_(db_server.ip==ip,db_server.ssh_port==ssh_port)).all()
                        if hostname:
                            total_infos['ip'] = hostname
                            server_info = db_server.query.with_entities(db_server.idc_id,db_server.ip,db_server.ssh_port,db_server.s_ip,db_server.host_type,db_server.hostname,
                                                                    db_server.sn,db_server.manufacturer,db_server.productname,db_server.system,db_server.cpu_info,
                                                                    db_server.cpu_core,db_server.mem,db_server.disk_count,db_server.disk_size,db_server.idrac,db_server.purch_date,db_server.expird_date,
                                                                    db_server.status,db_server.comment).filter(db_server.hostname==hostname).all()
                            ip = server_info[0][1]
                            ssh_port = int(server_info[0][2])
                    except Exception as e:
                        logging.error(e)
                    if server_info:
                        try:
                            server_info = list(server_info[0])
                            # 获取服务器机房机柜信息
                            idc_info = db_idc_id.query.with_entities(db_idc_id.aid,db_idc_id.cid).filter(db_idc_id.id==int(server_info[0])).all()
                            server_info.pop(0)
                            if idc_info:
                                server_info.insert(0,idc_info[0][1])
                                server_info.insert(0, idc_info[0][0])
                            else:
                                server_info.insert(0,None)
                                server_info.insert(0,None)
                            table_info = ['机房','机柜','IP','SSH_PORT','附属ip','主机类型','hostname','sn','生产厂家','服务器型号','操作系统','cpu信息','cpu核数','内存','磁盘数','磁盘总量','idrac','采购日期','过保日期','状态','管理','备注']
                            total_infos['server_info'] = [table_info,server_info]
                        except Exception as e:
                            logging.error(e)
                        try:
                            # 获取服务器监控信息
                            zabbix_infos = []
                            disks_name = []
                            disks_val = []
                            network_in_name = []
                            networ_in_val = []
                            network_out_name = []
                            networ_out_val = []
                            vals = db_zabbix.query.with_entities(db_zabbix.icmpping, db_zabbix.cpu_load,
                                                                 db_zabbix.mem_use, db_zabbix.disk_io,
                                                                 db_zabbix.openfile).filter(
                                and_(db_zabbix.ip == server_info[2], db_zabbix.ssh_port == server_info[3])).all()
                            if vals:
                                zabbix_infos = [float(val) for val in list(vals[0])]
                            Key = "zabbix_history_%s_%s" % (server_info[2], server_info[3])
                            zabbix_values = Redis.hgetall(Key)
                            if zabbix_values:
                                for key in zabbix_values:
                                    if '/' in key:
                                        disks_name.append(key)
                                        disks_val.append(zabbix_values[key])
                                    if 'in_' in key:
                                        network_in_name.append(key.split('_')[-1])
                                        networ_in_val.append(zabbix_values[key])
                                    if 'out_' in key:
                                        network_out_name.append(key.split('_')[-1])
                                        networ_out_val.append(zabbix_values[key])
                            total_infos['zabbix_infos'] = zabbix_infos
                            disk_bar = Bar(width='100%', height='250px')
                            disk_bar.add("磁盘使用率", disks_name, disks_val, mark_point=["max", "min"],is_yaxislabel_align=True, is_toolbox_show=False,yaxis_formatter='%',xaxis_interval=0,xaxis_rotate=15)
                            network_bar = Bar(width='100%', height='250px')
                            network_bar.add("入口流量", network_in_name, networ_in_val, mark_point=["max", "min"],is_yaxislabel_align=True, is_toolbox_show=False,yaxis_formatter='Mbps',xaxis_interval=0,xaxis_rotate=15)
                            network_bar.add("出口流量", network_out_name, networ_out_val, mark_point=["max", "min"],is_yaxislabel_align=True, is_toolbox_show=False,yaxis_formatter='Mbps',xaxis_interval=0,xaxis_rotate=15)
                            total_infos['bar_infos'] = [disk_bar, network_bar]
                        except Exception as e:
                            logging.error(e)
                        try:
                            # 获取第三方资源信息
                            third_table = ['应用服务', '应用端口', '所属项目', '集群类型', '业务使用','所属部门','负责人', '联系方式']
                            project_table = ['应用服务', '应用端口', '所属项目', '域名', '开发语言', '环境', '状态','所属业务']
                            total_infos['pool_project'] = True
                            db_third = db_idc.third_resource
                            db_project = db_op.project_list
                            db_busi = db_op.business
                            db_project_third = db_op.project_third
                            busis = db_busi.query.with_entities(db_busi.id,db_busi.business).all()
                            busis = {int(busi[0]):busi[1] for busi in busis}
                            busis[0] = '未知业务'
                            project_third = db_project_third.query.with_entities(db_project_third.third_id,db_project_third.project).all()
                            if project_third:
                                project_third = {info[0]:info[1] for info in project_third}
                            third_info = db_third.query.with_entities(db_third.id,db_third.resource_type, db_third.app_port, db_third.cluster_type,db_third.busi_id ,db_third.department, db_third.person,db_third.contact).filter(
                                and_(db_third.ip == ip, db_third.ssh_port == ssh_port,)).all()
                            if third_info:
                                third_info = [list(info) for info in third_info]
                                third_id= [info[0] for info in third_info]
                                for i,info in enumerate(third_info):
                                    info = list(info)
                                    info[4] = busis[int(info[4])]
                                    if project_third:
                                        if third_id[i] in project_third.keys():
                                            info.insert(3,project_third[third_id[i]])
                                        else:
                                            info.insert(3,'')
                                    else:
                                        info.insert(3, '')
                                    third_info[i] = info
                                third_info.insert(0, third_table)
                                total_infos['third_info'] = third_info
                        except Exception as e:
                            logging.error(e)
                        try:
                            #获取自有资源信息
                            project_info = db_project.query.with_entities(db_project.id,db_project.resource,db_project.app_port,db_project.project,db_project.domain,db_project.sys_args,db_project.env,db_project.status,db_project.business_id).filter(and_(db_project.ip==ip,db_project.ssh_port==ssh_port)).all()
                            project_info = [list(info) for info in project_info]
                            if project_info:
                                for info in project_info:
                                    business = db_busi.query.with_entities(db_busi.business).filter(db_busi.id == int(info[-1])).all()
                                    info[-1] = '%s:%s'%(info[-1],business[0][0])
                                project_info.insert(0,project_table)
                                total_infos['project_info'] = project_info
                        except Exception as e:
                            logging.error(e)
                    return render_template('server_infos.html',total_infos=total_infos)
            #判断是否是存储设备
            try:
                if Args['type'] == 'store' and Args['action']:
                    db_store = db_idc.idc_store
                    tables = ('机房','机柜','设备型号', 'ip', '购买日期', '过保日期', '状态', '备注')
                    if idc_ids:
                        val = db_store.query.with_entities(db_store.idc_id,db_store.type,db_store.ip,db_store.purch_date,
                                                           db_store.expird_date,db_store.status,
                                                           db_store.comment).filter(db_store.idc_id.in_(idc_ids)).all()
                        values = [list(va) for va in val]
                        for value in values:
                            idc_id = int(value[0])
                            cid = db_idc_id.query.with_entities(db_idc_id.aid,db_idc_id.cid).filter(db_idc_id.id==idc_id).all()
                            value.pop(0)
                            value.insert(0,cid[0][1])
                            value.insert(0, cid[0][0])
            except Exception as e:
                logging.error(e)
            #判断是否是网络设备
            try:
                if Args['type'] == 'network' and Args['action']:
                    db_network = db_idc.idc_networks
                    tables = ('机房','机柜','设备型号', 'ip', '冗余', '购买日期', '过保日期', '状态', '备注')
                    if idc_ids:
                        val = db_network.query.with_entities(db_network.idc_id,
                                                             db_network.type,db_network.ip,db_network.redundance,
                                                             db_network.purch_date,db_network.expird_date,db_network.status,
                                                             db_network.comment).filter(db_network.idc_id.in_(idc_ids)).all()
                        values = [list(va) for va in val]
                        for value in values:
                            idc_id = int(value[0])
                            cid = db_idc_id.query.with_entities(db_idc_id.aid,db_idc_id.cid).filter(db_idc_id.id==idc_id).all()
                            value.pop(0)
                            value.insert(0,cid[0][1])
                            value.insert(0, cid[0][0])
            except Exception as e:
                logging.error(e)
    except Exception as e:
        logging.error(e)
        flash('获取数据错误!',"error")
        return render_template('Message.html')
    return render_template('server_list.html', values=values, tables=tables, form=form, export=False,assets_type = Args['type'])

@page_Assets.route('/assets')
@check.login_required(grade=4)
def assets():
    try:
        form = MyForm.MyForm_server()
        tables=('机柜数量','物理机数量','虚拟机数量')
        ns = ('网络设备数量','存储设备数量','应用部署情况')
        phosts=[]
        vhosts=[]
        networks = []
        stores = []
        total = []
        #获取机房机柜信息
        db_idc_id = db_idc.idc_id
        db_hosts = db_idc.idc_servers
        values = db_idc_id.query.with_entities(db_idc_id.aid, func.count(db_idc_id.cid)).filter(db_idc_id.id != 1053).group_by(db_idc_id.aid).all()
        values = [list(val) for val in values]
        c_val = db_idc_id.query.with_entities(func.count(db_idc_id.cid)).filter(~db_idc_id.cid.in_(('KVM','OSS'))).all()
        p_val =  db_hosts.query.with_entities(func.count(db_hosts.ip)).filter(db_hosts.host_type=='physical').all()
        v_val = db_hosts.query.with_entities(func.count(db_hosts.ip)).filter(db_hosts.host_type == 'vm').all()
        e_val = db_hosts.query.with_entities(func.count(db_hosts.ip)).filter(and_(db_hosts.host_type=='physical',db_hosts.expird_date < tt,db_hosts.idc_id !=1053)).all()
        w_val = db_hosts.query.with_entities(func.count(db_hosts.ip)).filter(and_(db_hosts.host_type=='physical',db_hosts.expird_date >= tt,db_hosts.expird_date <= dt,db_hosts.idc_id !=1053)).all()
        n_val = db_hosts.query.with_entities(func.count(db_hosts.ip)).filter(db_hosts.idc_id == 1053).all()
        try:
            total.append(len(values))
            total.append(int(c_val[0][0]))
            total.append(int(p_val[0][0]))
            if e_val:
                total.append(int(e_val[0][0]))
            else:
                total.append(0)
            if w_val:
                total.append(int(w_val[0][0]))
            else:
                total.append(0)
            total.append(int(v_val[0][0]))
            if n_val:
                total.append(int(n_val[0][0]))
            else:
                total.append(0)
            Key = "op_disconnet_assets_count"
            d_val = Redis.smembers(Key)
            if d_val:
                total.append(len(d_val))
            else:
                total.append(0)
        except Exception as e:
            logging.error(e)
        for val in values:
            try:
                #获取指定机房机柜的服务器信息
                idc_id = db_idc_id.query.with_entities(db_idc_id.id).filter(db_idc_id.aid==val[0]).all()
                idc_id = tuple([id[0] for id in idc_id])
                #统计物理服务器数量
                phost_count = db_hosts.query.with_entities(func.count(db_hosts.ip)).filter(and_(db_hosts.host_type=='physical',db_hosts.idc_id.in_(idc_id))).all()
                phosts.append(phost_count)
                #获取虚拟机数量
                vhost_count = db_hosts.query.with_entities(func.count(db_hosts.ip)).filter(and_(db_hosts.host_type=='vm',db_hosts.idc_id.in_(idc_id))).all()
                vhosts.append(vhost_count)
                # 获取网络设备和存储设备、附属设备
                db_network = db_idc.idc_networks
                db_store = db_idc.idc_store
                network_count = db_network.query.with_entities(func.count(db_network.ip)).filter(db_network.idc_id.in_(idc_id)).all()
                networks.append(network_count)
                store_count = db_store.query.with_entities(func.count(db_store.ip)).filter(db_store.idc_id.in_(idc_id)).all()
                stores.append(store_count)
            except Exception as e:
                logging.error(e)
        #信息进行合并
        try:
            phosts=[host[0][0] for host in phosts]
            vhosts = [host[0][0] for host in vhosts]
            networks = [host[0][0] for host in networks]
            stores = [host[0][0] for host in stores]
            for i,val in enumerate(values):
                if int(vhosts[i]) > 0:
                    val[1] = int(val[1]) -1
                if int(phosts[i]) == 0:
                    val[1] = 0
                val.append(phosts[i])
                val.append(vhosts[i])
                val.append(networks[i])
                val.append(stores[i])
                val.append('查看')
                values[i] = val
        except Exception as e:
            logging.error(e)
        return render_template('assets.html', values=values, tables=tables, ns=ns, form=form,total=total)
    except Exception as e:
        logging.error(e,"error")
        flash('获取数据错误!',"error")
        return render_template('Message.html')

@page_Assets.route('/other_resource')
@check.login_required(grade=1)
def other_resource():
    try:
        db_other_resource = db_idc.other_resource
        domain_tables = ('顶级域名','服务商')
        domain_values = db_other_resource.query.with_entities(db_other_resource.domain,db_other_resource.provider).filter(db_other_resource.type=='domain').all()
        cdn_tables = ('加速域名','服务商')
        cdn_values = db_other_resource.query.with_entities(db_other_resource.domain,db_other_resource.provider).filter(db_other_resource.type=='cdn').all()
    except Exception as e:
        logging.error(e)
    return render_template("other_resource.html", domain_values=domain_values,domain_tables=domain_tables,cdn_tables=cdn_tables,cdn_values=cdn_values)

@page_Assets.route('/assets_deploy/<room>')
@page_Assets.route('/assets_deploy/business/<busi>')
@page_Assets.route('/assets_deploy/business/<busi>/<idc>')
@check.login_required(grade=1)
def assets_deploy(room=None,busi=None,idc=None):
    CONFS = defaultdict
    INFOS = defaultdict
    BUSIS = defaultdict
    busi_vals = defaultdict
    idc_vals = defaultdict
    db_dic_id = db_idc.idc_id
    db_server = db_idc.idc_servers
    db_third = db_idc.third_resource
    db_project = db_op.project_list
    db_busi = db_op.business
    db_project_third = db_op.project_third
    try:
        if room:
            try:
                idcs = db_dic_id.query.with_entities(db_dic_id.id).filter(db_dic_id.aid == room).all()
                if idcs:
                    #获取机房信息
                    idcs = tuple([int(idc[0]) for idc in idcs])
                    #获取资产信息
                    vals = db_server.query.with_entities(db_server.hostname,db_server.ip,db_server.ssh_port,db_server.host_type,db_server.cpu_core,db_server.mem).filter(db_server.idc_id.in_(idcs)).all()
            except Exception as e:
                logging.error(e)
        if busi:
            try:
                busi_id = db_busi.query.with_entities(db_busi.id).filter(db_busi.business==busi).all()
                busi_id = busi_id[0][0]
                projects = db_project.query.with_entities(distinct(db_project.project)).filter(db_project.business_id==busi_id).all()
                projects = tuple([project[0] for project in projects])
                ids = db_project_third.query.with_entities(db_project_third.third_id).filter(db_project_third.project.in_(projects)).all()
                third_ids = [id[0] for id in ids]
                self_ips = db_project.query.with_entities(distinct(db_project.ip)).filter(db_project.project.in_(projects)).all()
                self_ips = [ip[0] for ip in self_ips]
                third_ips = db_third.query.with_entities(distinct(db_third.ip)).filter(db_third.id.in_(tuple(third_ids))).all()
                third_ips = [ip[0] for ip in third_ips]
                if idc:
                    idc_ids = db_dic_id.query.with_entities(db_dic_id.id).filter(db_dic_id.aid==idc).all()
                    idc_ids = tuple([id[0] for id in idc_ids])
                    vals = db_server.query.with_entities(db_server.hostname, db_server.ip, db_server.ssh_port,
                                                         db_server.host_type, db_server.cpu_core, db_server.mem).filter(and_(
                        db_server.ip.in_(tuple(self_ips + third_ips)),db_server.idc_id.in_(idc_ids))).all()
                else:
                    vals = db_server.query.with_entities(db_server.hostname, db_server.ip, db_server.ssh_port,
                                                     db_server.host_type, db_server.cpu_core, db_server.mem).filter(db_server.ip.in_(tuple(self_ips + third_ips))).all()
            except Exception as e:
                logging.error(e)
        try:
            CONFS = {val[0]:val[3:] for val in vals}
            INFOS = {val[0]:[] for val in vals}
            BUSIS = {val[0]: [] for val in vals}
            hostnames = {val[1]:val[0] for val in vals}
            ips = tuple([val[1] for val in vals])
            if room:
                #获取业务信息
                busi_vals = db_busi.query.with_entities(db_busi.id,db_busi.business).all()
                busi_vals = {b[0]:b[1] for b in busi_vals}
            if busi:
                #获取机房信息
                idc_vals = db_dic_id.query.with_entities(db_dic_id.id,db_dic_id.aid).all()
                idc_vals = {int(b[0]): b[1] for b in idc_vals}
            IDCS = db_server.query.with_entities(db_server.hostname,db_server.idc_id).filter(db_server.ip.in_(ips)).all()
            IDCS = {idc[0]:[int(idc[1])] for idc in IDCS}
        except Exception as e:
            logging.error(e)
        #获取应用服务信息
        try:
            third_vals = db_third.query.with_entities(db_third.resource_type,db_third.ip).filter(db_third.ip.in_(ips)).all()
            for info in third_vals:
                resource,ip = info
                INFOS[hostnames[ip]].append(resource)
            project_vals = db_project.query.with_entities(db_project.resource,db_project.ip,db_project.business_id).filter(db_project.ip.in_(ips)).all()
            for info in project_vals:
                resource,ip,business_id = info
                BUSIS[hostnames[ip]].append(business_id)
                INFOS[hostnames[ip]].append(resource)
        except Exception as e:
            logging.error(e)
        #格式化数据
        try:
            if INFOS:
                for info in INFOS:
                    INFOS[info] = set(INFOS[info])
            if BUSIS:
                for info in BUSIS:
                    BUSIS[info] = set(BUSIS[info])
        except Exception as e:
            logging.error(e)
    except Exception as e:
        logging.error(e)
    if room:
        tables = ['主机名', '部署应用', '线上业务', '主机类型', 'CPU核数','内存']
        return render_template('assets_deploy.html',INFOS=INFOS,BUSIS=BUSIS,tables=tables,CONFS=CONFS,busi_vals=busi_vals,room=room,busi=busi)
    if busi:
        tables = ['主机名', '部署应用', '机房', '主机类型', 'CPU核数','内存']
        return render_template('assets_deploy.html',INFOS=INFOS,BUSIS=IDCS,tables=tables,CONFS=CONFS,busi_vals=idc_vals,room=room,busi=busi)

@page_Assets.before_request
@check.login_required(grade=10)
def check_login(error=None):
    produce.Async_log(g.user, request.url)

@page_Assets.teardown_request
def db_remove(error=None):
    db_idc.DB.session.remove()
    db_op.DB.session.remove()
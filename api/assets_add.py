#-*- coding: utf-8 -*-
from flask import Blueprint,jsonify,request
from Modules import db_op,check,db_idc,loging,SSH,tools
from sqlalchemy import distinct,and_
import tcpping
import time
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from Modules import init
app = Flask(__name__)
app.config.from_pyfile('../conf/sql.conf')
DB = SQLAlchemy(app)
limiter = init.web_limiter()
limiter = limiter.limiter
logging = loging.Error()
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/security.conf')
app.config.from_pyfile('../conf/assets.conf')
PHYSICAL_TYPES = app.config.get('PHYSICAL_TYPES')
page_assets_add = Blueprint('assets_add', __name__)
@page_assets_add.route('/assets_add')
@limiter.limit("60/minute")
@check.acl_ip
def assets_add():
    try:
        if tools.http_args(request,'ip'):
            ip = tools.http_args(request,'ip')
            ssh_port = 20443
            if tools.http_args(request,'ssh_port'):
                ssh_port = tools.http_args(request,'ssh_port')
            db_ips = db_idc.resource_ip
            db_idc_id = db_idc.idc_id
            exist_ips = []
            rip = ip.split('.')
            rip[3] = 0
            aid = db_ips.query.with_entities(db_ips.aid).filter(db_ips.network==rip).all()
            if aid:
                aid = aid[0][0]
            else:
                return jsonify({'error':"没有找到对应的机房信息!"})
            db_server = db_idc.idc_servers
            m_ips = db_server.query.with_entities(distinct(db_server.ip)).all()
            if m_ips:
                exist_ips = [ip[0] for ip in m_ips]
            e_ips = db_server.query.with_entities(distinct(db_server.s_ip)).all()
            for ips in e_ips:
                if None not in ips:
                    if ';' in ips[0]:
                        ips = ips[0].split(';')
                        for ip in ips:
                            exist_ips.append(ip)
                    exist_ips.append(ips[0])
            if ip not in exist_ips:
                if tcpping(host=ip, port=ssh_port, timeout=1):
                    try:
                        Ssh = SSH.ssh(ip=ip, ssh_port=ssh_port)
                        values = Ssh.Run('/usr/sbin/dmidecode -s system-manufacturer')
                        if values['stdout']:
                            if values['stdout'][0].strip('\n') in PHYSICAL_TYPES:
                                v = db_server(idc_id=1053,ip=ip, ssh_port=ssh_port, s_ip='', host_type='physical', hostname='', sn='',
                                              manufacturer='', productname='',
                                              system='', cpu_info='', cpu_core='', mem='',disk_count=0, disk_size='', idrac='',
                                              purch_date='',
                                              expird_date='', status='新发现', comment='')
                                db_idc.DB.session.add(v)
                                db_idc.DB.session.commit()
                            else:
                                #判断机房机柜信息
                                idc_id = db_idc_id.query.with_entities(db_idc_id.id).filter(and_(db_idc_id.aid==aid,db_idc_id.cid == 'KVM'))
                                if not idc_id:
                                    c = db_idc_id(aid=aid,cid='KVM')
                                    db_idc.DB.session.add(c)
                                    db_idc.DB.session.commit()
                                    idc_id = db_idc_id.query.with_entities(idc_id.id).filter(
                                        and_(db_idc_id.aid == aid, db_idc_id.cid == 'KVM'))
                                idc_id = idc_id[0][0]
                                dt = time.strftime('%Y-%m-%d', time.localtime())
                                v = db_server(idc_id=idc_id,ip=ip,ssh_port=ssh_port,s_ip='',host_type='vm',hostname='',sn='',manufacturer='',productname='',
                                              system='',cpu_info='',cpu_core='',mem='',disk_count=0,disk_size='',idrac='',purch_date=dt,expird_date='2999-12-12',status='使用中',comment='')
                                db_idc.DB.session.add(v)
                                db_idc.DB.session.commit()
                            for cmd in ("yum -y install dmidecode","chmod +s /usr/sbin/dmidecode"):
                                Ssh.Run(cmd)
                    except Exception as e:
                        return jsonify({'error':e})
                    else:
                        return jsonify({'info':'%s add success' %ip,'api':request.url,'time':'%s' %time.strftime('%Y-%m-%d %H:%M:%S',time.localtime())})
                    finally:
                        Ssh.Close()
                else:
                    return jsonify({'error':'ssh port not connect!'})
            else:
                return jsonify({'error':'服务器信息已存在!'})
    except Exception as e:
        logging.error(e)
    finally:
        db_idc.DB.session.remove()
@page_assets_add.teardown_request
def db_remove(exception):
    db_op.DB.session.remove()
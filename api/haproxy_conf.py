#-*- coding: utf-8 -*-
from flask import Blueprint,jsonify,request
from Modules import db_op,loging,check
import shutil
import os
import paramiko
from scp import SCPClient
from sqlalchemy import and_
import __init__
app = __init__.app
limiter = __init__.limiter
logging = loging.Error()
Path  = app.config.get('HAPROXY_PATH_TMP')
page_haproxy_conf = Blueprint('haproxy_conf', __name__)
@page_haproxy_conf.route('/haproxy_conf')
@limiter.limit("20/minute")
@check.acl_ip
def haproxy_conf():
    def _init_ssh():
        if Value == '0' and Type == 'cw':
            host = app.config.get('HAPROXY_TEST_HOST')
        if Value == '1'and Type == 'cw':
            host = app.config.get('HAPROXY_TEST_INTRANET_HOST')
        User = app.config.get('HAPROXY_TEST_USER')
        Password = app.config.get('HAPROXY_TEST_PASSWORD')
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(host,22,username=User,password=Password,timeout=15)
        except Exception as e:
            return jsonify({'Error': str(e)})
        return ssh

    # 构造ssh会话
    def ssh_scp(path):
        ssh = _init_ssh()
        ha_path = app.config.get('HAPROXY_PATH')
        ha_cmd = "/usr/sbin/service haproxy restart"
        scp = SCPClient(ssh.get_transport())
        scp.put(path,ha_path)
        stdin, stdout, stderr = ssh.exec_command(ha_cmd)
        return stderr.read()

    def Init_conf(log_arg,conf_path):
        #初始化配置文件头部
        with open(conf_path,'a+') as ff:
            with open(Mod_path,'r') as f:
                for line in f:
                    line = line.replace('<LOG>',log_arg)
                    ff.write(line)
        return True
    def Get_arg(arg):
        #解析请求参数
        if arg in request.args:
            return  request.args[arg].encode('utf-8')
        else:
            return None

    def Write_file(path,info):
        with open(path,'a+') as f:
            f.write('%s\n'%info)

    def Write_conf(path,data):
        try:
            ACL = []
            CONF = {}
            #分离域名
            for i in range(len(data)):
                v = [str(x).encode('utf-8') for x in data[i] ]
                domain = v[0]
                ACL.append(domain)
                Key = '%s_%i'%(domain,i)
                CONF[Key] = v[1:]
            ACL = set(ACL)
            #生成ACL规则
            for domain in ACL:
                name = '%s_%s'%(domain.split('.')[1],domain.split('.')[0])
                Write_file(path,'   acl %s hdr_dom(host) -i %s'%(name,domain))
                Write_file(path,'   use_backend %s if %s\n'%(name,name))
            Write_file(path,'   default_backend haproxy')
            #格式化BACKEND信息
            BACKEND = {}
            for domain in ACL:
                BACKEND[domain] = [CONF[Key] for Key in CONF if Key.startswith(domain)]
            #生成BACKEND规则
            for domain in BACKEND:
                i = 0
                name = '%s_%s'%(domain.split('.')[1],domain.split('.')[0])
                Write_file(path,'\nbackend %s'%name)
                balance,monitor,session,ip,port,maxconn,backup = BACKEND[domain][0]
                Write_file(path,'   mode http')
                if '/' in monitor.strip():
                    Write_file(path,'   option httpchk HEAD %s HTTP/1.1\\r\\nHost:\\ %s'%(monitor,domain))
                Write_file(path,'   balance %s' %balance)
                if session == '1':
                    Write_file(path,'   cookie SESSION_COOKIE insert indirect nocache')
                for balance,monitor,session,ip,port,maxconn,backup in BACKEND[domain]:
                    line = '   server  {0}:{1}  {0}:{1}  check inter 1s fall 3 rise 2 weight 1 maxconn {2}'.format(ip,port,maxconn)
                    if session == '1':
                        i+=1
                        line =line.replace('check','check cookie %i' %i)
                    if backup == '1':
                        line =line.replace('check','check  backup')
                    Write_file(path,line)
        except Exception as e:
            logging.error(e)
            return jsonify({'Error':'Failed to generate configuration file!'})

    def create_conf(terms,Type):
        def output_conf():
            try:
                #写入BANCKEND规则
                if terms['terms_backend']:
                    terms_backend = eval(terms['terms_backend'])
                    db = db_op.haproxy_conf
                    data = db.query.with_entities(db.domain,db.balance,db.monitor,db.session,db.ip,db.port,db.maxconn,db.backup).filter(terms_backend).all()
                    if data:
                        Write_conf(conf_path,data)
                        result = ssh_scp(conf_path)
                        if result:
                            return 'haproxy configure fail!'
                        return u'Haproxy新配置已生效!'
                    else:
                        return 'Get data error!'
            except Exception as e:
                logging.error(e)
            finally:
                db_op.DB.session.remove()
        #判断配置文件'
        if os.path.exists(Mod_path):
            try:
                v = []
                if Type == 'cw':
                    conf_path = '%s/haproxy_%s.cfg' %(Path,Type)
                    bak_path = '%s/haproxy_%s.cfg.bak' %(Path,Type)
                    log_arg = app.config.get('HAPROXY_OTHER')
                    #生成初始配置文件
                    if os.path.exists(conf_path):
                        shutil.move(conf_path,bak_path)
                    if not Init_conf(log_arg,conf_path):
                        return jsonify({'Error':'Failed to generate configuration file!'})
                    re = output_conf()
                return re or v
            except Exception as e:
                logging.error(e)
        else:
            return jsonify({'Error':'Can not find template file!'})
    def Create_terms(arg=None,Type=None):
        #生成sql条件语句
        try:
            terms_backend = None
            if arg:
                if Type:
                    terms_backend = "and_(db_op.haproxy_conf.{0} == '{1}',db_op.haproxy_conf.Type == '{2}')".format(arg,Value,Type)
            re = {'terms_backend':terms_backend}
            return re
        except Exception as e:
            logging.error(e)

    #解析http参数
    try:
        Type = Get_arg('type')
        ip = Get_arg('ip')
        domain = Get_arg('domain')
        if Type == 'cw':
            Mod_path = "%s/../conf/haproxy_cw_template.cfg" % page_haproxy_conf.root_path
            Value = '0'
            arg = 'intranet'
            if Get_arg(arg):
                Value = '1'
            if ip and domain:
                if ':' in ip:
                    ip, port = ip.split(':')
                    db = db_op.haproxy_conf
                    val = db.query.filter(and_(db.domain == domain,db.intranet == Value,db.Type == Type)).all()
                    if val:
                        for c in val:
                            db_op.DB.session.delete(c)
                            db_op.DB.session.commit()
                    v = db(domain=domain, balance='roundrobin',monitor = '',session = '0',ip=ip,port=port,maxconn=1000,backup='0',intranet=Value,Type=Type)
                    db_op.DB.session.add(v)
                    db_op.DB.session.commit()
                else:
                    return jsonify({'Error':'parameter error!'})
            result = create_conf(Create_terms(arg,Type=Type),Type)
        else:
            return jsonify({'Error':'parameter error!'})
        return jsonify({'result':result})
    except Exception as e:
        logging.error(e)

@page_haproxy_conf.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
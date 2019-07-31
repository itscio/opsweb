#-*- coding: utf-8 -*-
import os
from tcpping import tcpping
import time
import json
import shutil
from urllib.request import urlretrieve
import requests
import paramiko
from scp import SCPClient
import redis
import zipfile
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from module import Md5,db_op,loging,produce
from sqlalchemy import and_,desc
app = Flask(__name__)
DB = SQLAlchemy(app)
logging = loging.Error()
bak_path = '/opt/bak/'
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/ssh.conf')
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
Redis = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
username = app.config.get('USER')
key_file = app.config.get('KEY_FILE')
db_project = db_op.project_list
db_publish = db_op.publish_records
Publish_types = {'batch':5,'step':1}
#流水日志记录
def _flow_log(flow_number,Msg):
    try:
        tm = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime())
        if not os.path.exists("%s/flow_logs" %bak_path):
            os.system("/bin/mkdir -p %s/flow_logs" %bak_path)
        flow_log_ptah = "%s/flow_logs/%s.log" %(bak_path,flow_number)
        with open(flow_log_ptah,'a+') as f:
            f.write("%s  %s\n"%(tm,str(Msg)))
    except Exception as e:
        logging.error(e)
#终端消息输出
def _console_out(channel,Msg_key,Msg):
    if channel == 'web':
        th = time.strftime('%H:%M:%S', time.localtime())
        if '_End_' in Msg or '-' * 100 in Msg:
            Redis.lpush(Msg_key,'%s' %Msg)
        else:
            Redis.lpush(Msg_key,"%s  %s" %(th,Msg))
#结果汇总模块
def _result_handle(result,server_lists_counts,INFOS):
    # 将执行信息写入数据库
    try:
        channel = INFOS['channel']
        if result in ('Fail','Success'):
            package_url = INFOS['package_url']
            package = package_url.split('/')[-1]
            project = '-'.join(package.split('-')[:-1])
            version = package.split('-')[-1]
            version = version.replace('.zip', '')
            version = version.replace('.war', '')
            callback_url = INFOS['callback_url']
            c = db_publish(date=time.strftime('%Y-%m-%d', time.localtime()),
                           time=time.strftime('%H:%M:%S', time.localtime()),
                           user=INFOS['user'], project=project, version=version, package_url=package_url,describe=INFOS['describe'],
                           package_md5=INFOS['package_md5'], package_type=INFOS['package_type'], publish_type=INFOS['publish_type'],
                           restart=INFOS['restart'], check_url=INFOS['check_url'], callback_url=callback_url,token=INFOS['token'],
                           execute=INFOS['execute'], gray=int(INFOS['gray']),channel=channel, result=result,flow_number=INFOS['timestamp'])
            db_op.DB.session.add(c)
            db_op.DB.session.commit()
            db_op.DB.session.remove()
            _flow_log(INFOS['timestamp'],"publish info write to the database")
    except Exception as e:
        _flow_log(INFOS['timestamp'], e)
    #api渠道进行接口回调
    if channel == 'api':
        headers = {'Content-Type':'application/json'}
        try:
            data = json.dumps({'result':str(result),
                               'project_name': INFOS['project'],
                               'project_version': INFOS['version'],
                               'package_md5': INFOS['package_md5'],
                               'application_numbers': server_lists_counts,
                               'execute': INFOS['execute'],
                               'timestamp': INFOS['timestamp']
                               })
        except Exception as e:
            _flow_log(INFOS['timestamp'], e)
        finally:
            callback_url = INFOS['callback_url']
            _flow_log(INFOS['timestamp'],data)
            #回调接口返回信息
            try:
                f = requests.post(callback_url, data=data, headers=headers)
            except Exception as e:
                _flow_log(INFOS['timestamp'],e)
            else:
                _flow_log(INFOS['timestamp'],"callback_status:%s"%f.status_code)
    #将流水记录写入数据库
    db_publish_log = db_op.publish_log
    flow_number = INFOS['timestamp']
    flow_log_ptah = "%s/flow_logs/%s.log" % (bak_path,flow_number)
    try:
        with open(flow_log_ptah, 'r') as f:
            records = f.read().replace("'",'"')
        c = db_publish_log(fid =flow_number,record = records)
        db_op.DB.session.add(c)
        db_op.DB.session.commit()
    except Exception as e:
        logging.error(e)
    finally:
        db_op.DB.session.remove()

#代码部署代理
def Publish_agent(args):
    #代码分发模块
    def _publish_code(package_type, d_files, package_name, ssh, ip, ssh_port, app_port, package_path, package_md5,execute):
        #上线操作前进行数据备份
        _console_out(channel, Msg_Key,"ip:%s  ssh_port:%s   app_port:%s        --->start deploy %s......" % (ip, ssh_port, app_port,project))
        if execute == 'publish':
            try:
                cmd = "[ -e %s%s ] && echo ok" % (web_path, package_name)
                stdin, stdout, stderr = ssh.exec_command(cmd)
                result = str(stdout.read().strip(),encoding='utf8')
                if result == 'ok':
                    if package_name.endswith('.war'):
                        cmd = "\cp -rf %s%s  %s%s" % (web_path, package_name, bak_path,package_name)
                    else:
                        cmd = "/usr/bin/rsync -av --delete %s%s/  %s%s/" % (web_path, package_name, bak_path, package_name)
                    stdin, stdout, stderr = ssh.exec_command(cmd)
                    result = stderr.read()
                    if result:
                        _flow_log(flow_number,"Error:%s"%result)
                        return "ip:%s  ssh_port:%s   app_port:%s       --->backup Fail !" % (ip, ssh_port, app_port)
            except Exception as e:
                _flow_log(flow_number,'Error:%s'%str(e))
                return "ip:%s  ssh_port:%s   app_port:%s       --->backup Fail !" % (ip, ssh_port, app_port)
        scp = SCPClient(ssh.get_transport())
        #增量包部署
        if package_type == 'part':
            try:
                scp.put("%s/"%d_files, "%s%s/" % (web_path, package_name), recursive=True)
            except Exception as e:
                # 传输错误重试3次
                for i in range(3):
                    time.sleep(3)
                    try:
                        scp.put("%s/" % d_files, "%s%s/" % (web_path, package_name), recursive=True)
                    except:
                        if i >=2:
                            break
                        continue
                    else:
                        cmd = "chown %s:%s -R %s%s/" % (service_user, service_user, web_path, package_name)
                        stdin, stdout, stderr = ssh.exec_command(cmd)
                        result = stderr.read()
                        if result:
                            _flow_log(flow_number, "Error:%s" % result)
                            return "ip:%s  ssh_port:%s   web_path:%s%s        --->chown Fail !" % (ip, ssh_port, web_path, package_name)
                _flow_log(flow_number,'Error:%s'%str(e))
                return "ip:%s  ssh_port:%s   app_port:%s        --->deploy Fail !" % (ip, ssh_port, app_port)
            else:
                cmd = "chown %s:%s -R %s%s/" %(service_user,service_user,web_path, package_name)
                stdin, stdout, stderr = ssh.exec_command(cmd)
                result = stderr.read()
                if result:
                    _flow_log(flow_number, "Error:%s" % result)
                    return "ip:%s  ssh_port:%s   web_path:%s%s        --->chown Fail !" % (ip, ssh_port,web_path, package_name)
        #整包部署
        if package_type == 'full':
            try:
                d_zip = "%s%s" % (web_path, package_path.split('/')[-1])
                try:
                    scp.put(package_path, d_zip)
                except Exception as e:
                    # 传输错误重试3次
                    for i in range(3):
                        time.sleep(3)
                        try:
                            scp.put(package_path, d_zip)
                        except:
                            if i >= 2:
                                break
                            continue
                    _flow_log(flow_number,'Error:%s'%str(e))
                    return "ip:%s  ssh_port:%s   app_port:%s         --->transfers Fail !" % (ip, ssh_port, app_port)
                cmd = '/usr/bin/md5sum %s' % d_zip
                stdin, stdout, stderr = ssh.exec_command(cmd)
                R_md5 = str(stdout.read().split()[0],encoding='utf8')
                if R_md5 == package_md5:
                    package_zip = package_path.split('/')[-1]
                    cmd = "cd %s  && /usr/bin/unzip -qo %s  && /bin/rm -f %s && [ -e %s ] && echo ok" % (web_path,package_zip,package_zip,package_zip.replace('.zip', ''))
                    stdin, stdout, stderr = ssh.exec_command(cmd)
                    result_zip = str(stdout.read().strip(),encoding='utf8')
                    result = stderr.read()
                    if result_zip == 'ok':
                        cmd = "cd %s && /bin/rm -rf %s{,.war} &&/bin/mv %s %s" % (web_path,project,package_zip.replace('.zip', ''), package_name)
                        stdin, stdout, stderr = ssh.exec_command(cmd)
                        result = stderr.read()
                        if result:
                            _flow_log(flow_number,"Error:%s"%result)
                            return "ip:%s  ssh_port:%s   app_port:%s       --->deploy Fail !" % (ip, ssh_port, app_port)
                        else:
                            cmd = "chown %s:%s  %s%s" % (service_user, service_user, web_path, package_name)
                            stdin, stdout, stderr = ssh.exec_command(cmd)
                            result = stderr.read()
                            if result:
                                _flow_log(flow_number, "Error:%s" % result)
                                return "ip:%s  ssh_port:%s   web_path:%s%s        --->chown Fail !" % (ip, ssh_port, web_path, package_name)
                    else:
                        _flow_log(flow_number, "Error:%s" % result)
                        return "ip:%s  ssh_port:%s   app_port:%s         --->unzip Fail !" % (ip, ssh_port, app_port)
                else:
                    return "ip:%s  ssh_port:%s   app_port:%s       --->md5 Fail !" % (ip, ssh_port, app_port)
            except Exception as e:
                if 'old-style' not in str(e):
                    _flow_log(flow_number,'Error:%s'%str(e))
                return "ip:%s  ssh_port:%s   app_port:%s        --->deploy Fail !" % (ip, ssh_port, app_port)

    #服务重启模块
    def _restart_service(restart, ssh, ip, ssh_port, app_port):
        # 判断是否需要重启
        try:
            if restart == 'True':
                _console_out(channel, Msg_Key,"ip:%s  ssh_port:%s   app_port:%s        --->restart tomcat ......" % (ip, ssh_port, app_port))
                cmd = "supervisorctl  restart  tomcat-%s" %project
                stdin, stdout, stderr = ssh.exec_command(cmd)
                result = stderr.read()
                if result:
                    _flow_log(flow_number,"Error:%s"%result)
                    return "ip:%s  ssh_port:%s   app_port:%s        --->restart tomcat Fail !'" % (ip, ssh_port, app_port)
                else:
                    time.sleep(15)
        except Exception as e:
            _flow_log(flow_number,'Error:%s'%str(e))
            return "ip:%s  ssh_port:%s   app_port:%s        --->restart tomcat Fail !" % (ip, ssh_port, app_port)

    #服务健康检测模块
    def _check_service(check_url, ip, ssh_port, app_port):
        # 检测服务是否正常启动
        try:
            _console_out(channel, Msg_Key,"ip:%s  ssh_port:%s   app_port:%s        --->check service ...... " % (ip, ssh_port, app_port))
            check_url = check_url.split('/')
            headers = {'Host': check_url[2]}
            check_url[2] = '%s:%s' % (ip, app_port)
            check_url = '/'.join(check_url)
            for i in range(30):
                try:
                    f = requests.post(check_url, data={'src': 1}, headers=headers)
                    if int(f.status_code) not in (200, 301, 302):
                        raise logging.error("error status_cod %s" % f.status_code)
                except Exception as e:
                    logging.error(e)
                    try:
                        f = requests.get(check_url, headers=headers)
                        if int(f.status_code) not in  (200,301,302):
                            raise logging.error("error status_cod %s" %f.status_code)
                    except Exception as e:
                        logging.error(e)
                        if i >= 30:
                            return "ip:%s  ssh_port:%s   app_port:%s        --->check service Fail !" % (ip, ssh_port, app_port)
                            break
                        time.sleep(2)
                        _console_out(channel, Msg_Key,"ip:%s  ssh_port:%s   app_port:%s        --->check service %i 次......" %(ip, ssh_port, app_port,i))
                        continue
                    else:
                        break
                else:
                    break
        except Exception as e:
            _flow_log(flow_number,'Error:%s'%str(e))
            return "ip:%s  ssh_port:%s   app_port:%s        --->check service Fail !" % (ip, ssh_port, app_port)

    #消息队列模块
    def Deploy_project(server_lists_key,ssh,secret_key):
        while True:
            #部署异常，停止部署
            if Redis.exists(deploy_fail_key):
                return 'Fail'
            vals = Redis.spop(server_lists_key)
            if vals:
                try:
                    ip, ssh_port, app_port = eval(vals)
                    msg = "ip:%s  ssh_port:%s   app_port:%s    %s start......" % (ip, ssh_port, app_port, execute)
                    _flow_log(flow_number,msg)
                    _console_out(channel, Msg_Key,msg)
                    ssh.connect(ip, int(ssh_port), username, pkey=ssh_key, timeout=30)
                    #代码分发部署
                    _flow_log(flow_number,"start publish_code ......")
                    result = _publish_code(package_type, d_files, package_name, ssh, ip, ssh_port, app_port,
                                           package_path, package_md5, execute)
                    if result:
                        _flow_log(flow_number,result)
                        raise _console_out(channel,Msg_Key, result)
                    else:
                        #记录部署成功的应用服务
                        Redis.sadd(deploy_success_key, [ip, ssh_port, app_port])
                        msg = "ip:%s  ssh_port:%s   app_port:%s    --->deploy code Success!" % (ip, ssh_port, app_port)
                        _flow_log(flow_number,msg)
                        _console_out(channel, Msg_Key,msg)
                    # 是否需要重启操作
                    _flow_log(flow_number,"start _restart_service ......")
                    result = _restart_service(restart, ssh, ip, ssh_port, app_port)
                    if result:
                        _flow_log(flow_number,result)
                        raise _console_out(channel,Msg_Key, result)
                    else:
                        msg = "ip:%s  ssh_port:%s   app_port:%s   --->restart service Success!" % (ip, ssh_port, app_port)
                        _flow_log(flow_number,msg)
                        _console_out(channel, Msg_Key,msg)
                    #检测应用服务是否正常
                    _flow_log(flow_number,'start _check_service ......')
                    result = _check_service(check_url, ip, ssh_port, app_port)
                    if result:
                        _flow_log(flow_number,result)
                        raise _console_out(channel,Msg_Key, result)
                    else:
                        msg = "ip:%s  ssh_port:%s   app_port:%s    --->check service Success!" % (ip, ssh_port, app_port)
                        _flow_log(flow_number,msg)
                        _console_out(channel, Msg_Key,msg)
                        # 识别是否是灰度上线并标记服务器
                        if execute == 'publish':
                            if int(INFOS['gray']) == 1:
                                gray_key = 'gray_server_%s' %secret_key
                                db_project.query.filter(db_project.ip==ip,db_project.ssh_port==ssh_port,db_project.app_port==app_port).update({db_project.gray:1})
                                db_op.DB.session.commit()
                                Redis.lpush(gray_key,'%s:%s'%(ip,app_port))
                            else:
                                db_project.query.filter(db_project.ip == ip, db_project.ssh_port == ssh_port,db_project.app_port == app_port).update({db_project.gray:0})
                                db_op.DB.session.commit()
                except Exception as e:
                    if 'old-style' not in str(e):
                        _flow_log(flow_number,'Error:%s'%str(e))
                    return 'Fail'
                else:
                    _console_out(channel,Msg_Key, "ip:%s  ssh_port:%s   app_port:%s        --->%s Success!" % (ip, ssh_port, app_port, execute))
                finally:
                    ssh.close()
            else:
                break

    #自动回滚模块
    def Auto_rollback(deploy_success_key, ssh):
        while True:
            vals = Redis.spop(deploy_success_key)
            if vals:
                ip, ssh_port, app_port = eval(vals)
                ssh.connect(ip, int(ssh_port), username, pkey=ssh_key, timeout=30)
                try:
                    msg = "ip:%s  ssh_port:%s   app_port:%s  start auto rollbackup......" % (ip, ssh_port, app_port)
                    _flow_log(flow_number,msg)
                    _console_out(channel, Msg_Key,msg)
                    # 回滚操作
                    if package_name.endswith('.war'):
                        cmd = "/usr/bin/rm -rf %s%s{,.war} && \cp %s%s  %s%s" % (web_path, project,bak_path, package_name, web_path, package_name)
                    else:
                        cmd = "/usr/bin/rsync -av --delete %s%s/  %s%s/" % (bak_path, package_name, web_path, package_name)
                    stdin, stdout, stderr = ssh.exec_command(cmd)
                    result = stderr.read()
                    if result:
                        _flow_log(flow_number,"Error:%s"%result)
                        #回滚失败记录
                        Redis.sadd(rollback_fail_key, [ip, ssh_port, app_port])
                    else:
                        # 是否需要重启操作
                        result = _restart_service(restart, ssh, ip, ssh_port, app_port)
                        if result:
                            _flow_log(flow_number,result)
                            _console_out(channel,Msg_Key, result)
                        # 检测服务是否正常
                        result = _check_service(check_url, ip, ssh_port, app_port)
                        if result:
                            _flow_log(flow_number,result)
                            _console_out(channel,Msg_Key, result)
                except Exception as e:
                    msg = "ip:%s  ssh_port:%s   app_port:%s       --->auto rollback Fail !" % (ip, ssh_port, app_port)
                    _flow_log(flow_number,'Error:%s'%str(e))
                    _flow_log(flow_number,msg)
                    _console_out(channel,Msg_Key, msg)
                    continue
                else:
                    msg = "ip:%s  ssh_port:%s   app_port:%s        --->auto rollback Success !"% (ip, ssh_port, app_port)
                    _flow_log(flow_number,msg)
                    #回滚成功计数
                    Redis.incr(rollback_count_key,1)
                    _console_out(channel,Msg_Key,msg)
            else:
                break
    #代码分发控制逻辑
    try:
        server_lists_key, server_lists_counts, d_files,project,package_name, package_path, Msg_Key,secret_key, INFOS = args
        web_path = '/opt/tomcat-%s/webapps/' % project
        service_users = {'tomcat': 'www', 'php': 'phper', 'python': 'www'}
        service = db_project.query.with_entities(db_project.resource).filter(db_project.project == project).limit(1).all()
        service = service[0][0]
        service_user = service_users[service]
    except Exception as e:
        logging.error(e)
    else:
        try:
            #自动回滚失败Key
            rollback_fail_key = 'rollback_fail_%s' %secret_key
            #自动回滚统计key
            rollback_count_key = 'rollback_count_%s' %secret_key
            #部署成功Key
            deploy_success_key = 'deploy_success_%s' %secret_key
            #部署失败Key
            deploy_fail_key = 'deploy_fail_%s' %secret_key
            KEYS = {'rollback_fail_key': rollback_fail_key, 'deploy_success_key': deploy_success_key,'deploy_fail_key':deploy_fail_key,'rollback_count_key':rollback_count_key}
            #获取相关信息
            package_md5 = INFOS['package_md5']
            package_type = INFOS['package_type']
            restart = INFOS['restart']
            check_url = INFOS['check_url']
            execute = INFOS['execute']
            publish_type = INFOS['publish_type']
            channel = INFOS['channel']
            flow_number = INFOS['timestamp']
            #初始化ssh实例
            ssh = paramiko.SSHClient()
            ssh_key = paramiko.RSAKey.from_private_key_file(key_file)
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            #代码分发
            result = Deploy_project(server_lists_key,ssh,secret_key)
            #代码分发失败触发自动回滚,独立回滚操作不触发
            if result == 'Fail' and execute == 'publish':
                Redis.set(deploy_fail_key,'Fail')
                Auto_rollback(deploy_success_key,ssh)
        except Exception as e:
            _flow_log(flow_number,'Error:%s'%str(e))
        finally:
            try:
                #判断并发执行是否完成
                ends_key = '%s_ends' %secret_key
                Redis.incr(ends_key)
                if int(Redis.get(ends_key))>=int(Publish_types[publish_type]):
                    result = 'Fail'
                    #自动回滚失败服务器列表
                    deploy_fail_counts = 0
                    if Redis.exists(rollback_fail_key):
                        deploy_fail_counts = len(Redis.smembers(rollback_fail_key))
                        _flow_log(flow_number,"auto rollback fail list:%s" % str(Redis.smembers(rollback_fail_key)))
                    # 部署的服务器列表
                    deploy_success_counts = 0
                    if Redis.exists(deploy_success_key):
                        deploy_success_counts = len(Redis.smembers(deploy_success_key))
                    else:
                        Redis.sadd(deploy_success_key,'None')
                    # 遗漏的服务器列表
                    lost_publish_counts = 0
                    vals_diff = Redis.sdiff(server_lists_key,deploy_success_key)
                    if vals_diff:
                        lost_publish_counts = len(vals_diff)
                        _flow_log(flow_number,"Lost publish list:%s" % str(vals_diff))
                    Auto_rollback_counts = 0
                    if Redis.exists(rollback_count_key):
                        Auto_rollback_counts = int(Redis.get(rollback_count_key))
                    if deploy_fail_counts == 0 and deploy_success_counts == server_lists_counts and lost_publish_counts == 0 and Auto_rollback_counts == 0:
                        result = 'Success'
                    gray = 'False'
                    gray_server = None
                    if int(INFOS['gray']) == 1:
                        gray = 'True'
                        gray_key = 'gray_server_%s' %secret_key
                        gray_server = ' '.join(Redis.lrange(gray_key,0,-1))
                    #汇总结果后回调接口
                    _result_handle(result,server_lists_counts,INFOS)
                    _console_out(channel, Msg_Key,'-' * 100)
                    _console_out(channel, Msg_Key,"_End_:{0},{1},{2},{3},{4}:{5}:{6},{7}".format(deploy_success_counts,deploy_fail_counts,Auto_rollback_counts,lost_publish_counts,server_lists_counts,flow_number,gray,gray_server))
                    # 清除统计keys
                    for Key in KEYS:
                        Redis.expire(KEYS[Key],15)
                    Redis.expire(ends_key, 15)
                    Redis.expire(Msg_Key,15)
            except Exception as e:
                logging.error(e)
#代码部署中心
def Publish_center(args):
    try:
        INFOS, Msg_Key, secret_key = args
        server_lists_counts = 0
        #获取上线操作参数
        execute = INFOS['execute']
        channel = INFOS['channel']
        flow_number = INFOS['timestamp']
        _flow_log(flow_number, 'Publish center(%s) start work ......' % os.getpid())
        _flow_log(flow_number,INFOS)
        _console_out(channel,Msg_Key, '-' * 100)
        _console_out(channel,Msg_Key, "初始化代码分发参数及检测部署环境,检测进行中......")
        #页面回滚操作需要将部分参数回写
        if execute == 'rollback' and channel == 'web':
            project = INFOS['project']
            version = INFOS['version']
            vals = db_publish.query.with_entities(db_publish.package_url, db_publish.package_md5,db_publish.package_type,
                                                  db_publish.publish_type, db_publish.restart,
                                                  db_publish.check_url,db_publish.gray).filter(
                and_(db_publish.project == project, db_publish.version == version,db_publish.result == 'Success')).order_by(desc(db_publish.date)).all()
            if vals:
                package_url, package_md5, package_type, publish_type, restart, check_url,gray = vals[0]
                INFOS['package_url'] = package_url
                INFOS['package_md5'] = package_md5
                INFOS['package_type'] = package_type
                INFOS['publish_type'] = publish_type
                INFOS['restart'] = restart
                INFOS['check_url'] = check_url
                INFOS['gray'] = int(gray)
            else:
                _Msg = "project:%s  version:%s        --->not relevant data Fail !" % (project, version)
                _flow_log(flow_number,_Msg)
                raise _console_out(channel,Msg_Key,_Msg)
        project = INFOS['project']
        package_url = INFOS['package_url']
        package_md5 = INFOS['package_md5']
        package_type = INFOS['package_type']
        publish_type = INFOS['publish_type']
        gray = INFOS['gray']
        web_path = '/opt/tomcat-%s/webapps/' %project
        #判断代码包类型
        Package_name = package_url.split('/')[-1]
        os.system("/bin/mkdir -p %s" % web_path)
        os.system("/bin/mkdir -p %s" %bak_path)
        package_path = "%s%s" %(bak_path,Package_name)
        package_name = Package_name.replace('.zip', '')
        s_files = "%s%s" % (web_path, package_name)
        #验证包规则
        if project == '-'.join(package_name.split('-')[:-1]):
            if package_name.endswith('.war'):
                package_name = '%s.war' %project
            else:
                package_name = project
        else:
            _Msg = "%s package format Fail" %Package_name
            _flow_log(flow_number,_Msg)
            raise _console_out(channel, Msg_Key,_Msg)
        if package_name.endswith('.war') and package_type == 'part':
            _Msg = "%s package not allow part publish" % Package_name
            _flow_log(flow_number, _Msg)
            raise _console_out(channel, Msg_Key, _Msg)
        d_files = "%s%s" % (web_path, package_name)
        #删除旧包
        if os.path.exists(package_path):
            os.remove(package_path)
        #获取代码压缩包
        try:
            urlretrieve(package_url,package_path)
        except Exception as e:
            msg = "package_url:%s              --->check package url Fail !" %package_url
            _flow_log(flow_number,'Error:%s'%str(e))
            _flow_log(flow_number,msg)
            raise _console_out(channel,Msg_Key,msg)
        #对压缩包进行md5对比
        _flow_log(flow_number,"package_md5:%s"%Md5.Md5_file(package_path))
        if package_md5 == Md5.Md5_file(package_path):
            #解压缩代码包
            try:
                zip_file = zipfile.ZipFile(package_path)
                if os.path.exists('%s%s' %(web_path,package_name)):
                    try:
                        shutil.rmtree('%s%s' %(web_path,package_name))
                    except:
                        os.remove('%s%s' %(web_path,package_name))
                zip_file.extractall(web_path)
            except Exception as e:
                msg = "package:%s              --->check unzip package Fail !" %package_name
                _flow_log(flow_number,'Error:%s'%str(e))
                _flow_log(flow_number, msg)
                raise _console_out(channel,Msg_Key,msg)
        else:
            _Msg = "package:%s              --->check  package md5 Fail !" % package_name
            _flow_log(flow_number,_Msg)
            raise _console_out(channel,Msg_Key,_Msg)
        if os.path.exists(s_files):
            shutil.move(s_files,d_files)
        if os.path.exists(d_files):
            #获取应用部署列表
            vals = db_project.query.with_entities(db_project.ip,db_project.ssh_port,db_project.app_port).filter(db_project.project==project).all()
            if vals:
                server_lists = [list(val) for val in vals]
                #判断是否为灰度上线，并尝试获取服务器灰度标识
                if int(gray) == 1:
                    gray_vals = db_project.query.with_entities(db_project.ip, db_project.ssh_port,db_project.app_port).filter(and_(db_project.project == project,db_project.gray == 1)).all()
                    if gray_vals:
                        server_lists = [list(val) for val in gray_vals]
                    else:
                        server_lists = [list(val) for val in vals][0]
                server_lists_counts = len(server_lists)
                #服务器和应用服务连通性检测
                for infos in server_lists:
                    ip, ssh_port, app_port = infos
                    try:
                        try:
                            ssh = paramiko.SSHClient()
                            ssh_key = paramiko.RSAKey.from_private_key_file(key_file)
                            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                            ssh.connect(ip, int(ssh_port), username, pkey=ssh_key, timeout=30)
                        except:
                            _Msg = "ip:%s  ssh_port:%s        --->check sshd Fail !" % (ip, ssh_port)
                            _flow_log(flow_number, _Msg)
                            raise _console_out(channel, Msg_Key, _Msg)
                        else:
                            #检测线上代码包路径是否存在
                            cmd = "[ -d %s ] && echo ok" % web_path
                            stdin, stdout, stderr = ssh.exec_command(cmd)
                            result = str(stdout.read().strip(),encoding='utf8')
                            if result != 'ok':
                                _Msg = "ip:%s  ssh_port:%s   web_path:%s       --->check app path Fail !" % (ip, ssh_port, web_path)
                                _flow_log(flow_number, _Msg)
                                raise _console_out(channel, Msg_Key, _Msg)
                            #创建备份目录
                            if package_name.endswith('.war'):
                                cmd = "/bin/mkdir -p %s" %bak_path
                            else:
                                cmd = "/bin/mkdir -p %s/%s" % (bak_path, package_name)
                            stdin, stdout, stderr = ssh.exec_command(cmd)
                            result = stderr.read()
                            if result:
                                _Msg = "ip:%s  ssh_port:%s   bak_path:%s       --->make bak path Fail !" % (ip, ssh_port, bak_path)
                                _flow_log(flow_number, "Error:%s" % result)
                                _flow_log(flow_number, _Msg)
                                raise _console_out(channel, Msg_Key, _Msg)
                            ssh.close()
                    except:
                        raise
                    else:
                        if not tcpping(host=ip, port=app_port, timeout=3):
                            _Msg = "ip:%s   app_port:%s        --->check app port Fail !" % (ip, app_port)
                            _flow_log(flow_number,_Msg)
                            raise _console_out(channel,Msg_Key,_Msg)
                #部署列表写入redis队列
                server_lists_key = '%s_server_lists_key' %secret_key
                for info in server_lists:
                    Redis.sadd(server_lists_key,info)
                #启动多个子控制中心并发执行
                _console_out(channel, Msg_Key, "代码分发相关参数及运行环境检测全部通过!")
                _console_out(channel, Msg_Key, "启动代码分发模块,开始部署%s,执行过程稍后输出......" % package_name)
                _console_out(channel, Msg_Key, '-' * 100)
                for i in range(Publish_types[publish_type]):
                    Scheduler = produce.SchedulerPublish()
                    Scheduler = Scheduler.Scheduler_mem(Publish_agent, [server_lists_key,server_lists_counts,d_files,project,package_name,package_path,Msg_Key,secret_key,INFOS])
                    Scheduler.start()
                    time.sleep(1)
            else:
                _Msg = "Error:not find app service lists!"
                _flow_log(flow_number,_Msg)
                raise _console_out(channel,Msg_Key,_Msg)
        else:
            _Msg = "package:%s              --->move package  Fail !" % package_name
            _flow_log(flow_number,_Msg)
            raise _console_out(channel,Msg_Key,_Msg)
    except Exception as e:
        if 'old-style' not in str(e):
            _flow_log(flow_number,'Error:%s'%str(e))
        result = "代码分发环境检测到错误,不执行代码分发操作!"
        _console_out(channel,Msg_Key,result)
        _console_out(channel,Msg_Key, '-' * 100)
        _console_out(channel,Msg_Key, "_End_:0,0,0,%i,%i:%s" %(server_lists_counts,server_lists_counts,flow_number))
        #汇总结果后回调接口
        _result_handle(result,server_lists_counts,INFOS)
        Redis.expire(Msg_Key,15)
    finally:
        db_op.DB.session.remove()
#-*- coding: utf-8 -*-
import paramiko
from scp import SCPClient
import sys,os
import re
import hashlib
import io
import shutil
import time
import redis
import Mysql,loging
import __init__
app = __init__.app
username = 'work'
key_file = '/home/%s/.ssh/id_rsa' % username
tag_path = '/home/%s/svn/tag' % username
svn_path = '/home/%s/svn' % username
web_path = '/home/%s/baihe' % username
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
Redis = redis.Redis(redis_host, redis_port)
mysql_user = app.config.get('MYSQL_USER')
mysql_password = app.config.get('MYSQL_PASSWORD')
mysql_host = app.config.get('MYSQL_HOST')
mysql_port = app.config.get('MYSQL_PORT')
mysql_db = 'op'
MYSQL = Mysql.MYSQL(mysql_user,mysql_password,mysql_host,mysql_port,mysql_db)
svn_user = app.config.get('SVN_USER')
svn_password = app.config.get('SVN_PASSWORD')
def php_update(publish_key,Key):
    def svn_co(Key, line, ssline, sdline, ver):
        try:
            Redis.lpush(Key, 'check out ' + line + '\n')
            os.system('export LC_CTYPE="zh_CN.UTF-8"')
            os.system('/bin/mkdir -p  ' + ssline)
            for s_l in os.popen(
                                                                                            "/usr/bin/svn co --no-auth-cache --non-interactive --username " +svn_user+ " --password " + svn_password + " http://svn.ibaihe.com:1722/svn" + sdline + ' ' + ssline + ' -r ' + ver):
                if '/home/work/svn' not in s_l:
                    Redis.lpush(Key, s_l)
        except Exception as e:
            Redis.lpush(Key, 'svn_co:{0} fail'.format(e))
            sys.exit()

    def md5sum(path):
        m = hashlib.md5()
        file = io.FileIO(path, 'r')
        bytes = file.read(1024)
        while (bytes != b''):
            m.update(bytes)
            bytes = file.read(1024)
        file.close()
        md5value = m.hexdigest()
        return md5value

    def check_path(List, Key, arg, gray):
        Redis.lpush(Key, '-' * 80 + '\n')
        Redis.lpush(Key, 'check serverlist,filepath,svnpath......\n')
        pp = []
        for line in List:
            line = line.strip()
            if line.startswith('#') or not line.split():
                continue
            m = re.match(r'[0-9]', line)
            p = re.match(r'/', line)
            if m:
                ver = line
                continue
            try:
                if ver and p:
                    if not p:
                        Redis.lpush(Key, 'fail ' + line + '  begin with "/"!\n')
                        sys.exit(1)
            except:
                Redis.lpush(Key, 'fail :not svn version number!\n')
                sys.exit(1)
            line = line.replace('\\', '/')
            line = line.replace('$', '\$')
            po = tuple(line.split('/'))
            project = po[3]
            swline = '/' + '/'.join(po[3:])
            pp.append(project)
            swline = web_path + swline
            sdline = '/' + '/'.join(po[:-1])
            ssline = svn_path + sdline
            sline = svn_path + line
            if arg == 'publish':
                svn_co(Key, line, ssline, sdline, ver)
                if os.path.exists(sline) and not os.path.exists(swline):
                    if os.path.isfile(sline):
                        Redis.lpush(Key, line + ' is new file\n')
                    if os.path.isdir(sline):
                        Redis.lpush(Key, line + ' is new Directory\n')
                if not os.path.exists(sline):
                    Redis.lpush(Key, line + ' path is error!\n')
                    sys.exit(1)
                if os.path.exists(svn_path):
                    shutil.rmtree(svn_path)
        if len(set(pp)) != 1:
            Redis.lpush(Key, "fail the %s is not same project!" % pp[:])
            sys.exit(1)
        Redis.lpush(Key, '    --->serverlist,filepath,svnpath pass!\n')
        Redis.lpush(Key, '-' * 80 + '\n')
        # 灰度发布
        if gray:
            cmd = 'select ip from php_list where project = "%s" and type = "%i" and Gray = "1";' % (project, Type)
            sip = MYSQL.Run(cmd)
            if not sip:
                cmd = 'select ip from php_list where project = "%s" and type = "%i" limit 1;' % (project, Type)
                sip = MYSQL.Run(cmd)
                cmd = 'update php_list set Gray = "1" where project = "%s" and ip = "%s";' % (project, sip[0])
                MYSQL.Run(cmd)
        else:
            cmd = 'select ip from php_list where project = "%s" and type = "%i" ;' % (project, Type)
            sip = MYSQL.Run(cmd)
        if not sip:
            Redis.lpush(Key,'fail :%s not find' %project)
            sys.exit(1)
        else:
            sip = set([ip[0] for ip in sip])
        MYSQL.Close()
        return (sip, project)

    def sync2(Key, arg, line, sline, wline, swline, project):
        def create_paths(pa):
            cp = []
            list_dirs = os.walk(pa)
            for root, dirs, files in list_dirs:
                for f in files:
                    cp.append(os.path.join(root, f))
            return cp

        def Verify(Key, ip, path):
            try:
                ssh = paramiko.SSHClient()
                key = paramiko.RSAKey.from_private_key_file(key_file)
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(ip, 22, username, pkey=key, timeout=30)
                cmd = '/usr/bin/md5sum ' + path
                stdin, stdout, stderr = ssh.exec_command(cmd)
                rmd5 = stdout.read().split()[0]
                smd5 = md5sum(path)
                Redis.lpush(Key, '   --->verify %s \n' % path)
                if rmd5 != smd5:
                    Redis.lpush(Key, '-' * 30 + '\n')
                    Redis.lpush(Key, ' verify ' + path + ' on ' + ip + ' fail \n')
                    Redis.lpush(Key, '-' * 30 + '\n' * 3)
                    Redis.lpush(Key, 'verify %s on %s fail' % (path, ip))
                    time.sleep(5)
                else:
                    Redis.lpush(Key, '         --->PASS!\n')
                ssh.close()
            except Exception as e:
                Redis.lpush(Key, 'Verify:{0} fail'.format(e))
                ssh.close()

        def scp2(Key, arg, wline, swline):
            try:
                ssh = paramiko.SSHClient()
                key = paramiko.RSAKey.from_private_key_file(key_file)
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                for ip in ips:
                    ip = ip.strip()
                    Redis.lpush(Key, 'sync ' + line + ' to ' + ip + '\n')
                    ssh.connect(ip, 22, username, pkey=key, timeout=30)
                    scp = SCPClient(ssh.get_transport())
                    cmd = 'mkdir -p ' + wline
                    stdin, stdout, stderr = ssh.exec_command(cmd)
                    if os.path.isdir(swline):
                        scp.put(swline, wline, recursive=True)
                    else:
                        scp.put(swline, swline)
                    ssh.close()
                    if arg == 'publish':
                        if os.path.isdir(swline):
                            dirs = create_paths(swline)
                            for path in dirs:
                                Verify(Key, ip, path)
                        else:
                            Verify(Key, ip, swline)
            except Exception as e:
                Redis.lpush(Key, 'scp2:{0} fail'.format(e))
                ssh.close()

        if arg == 'publish':
            if os.path.exists(sline) and not os.path.exists(swline):
                if os.path.isdir(sline):
                    shutil.copytree(sline, swline, True)
                else:
                    if not os.path.exists(wline):
                        os.makedirs(wline)
                    shutil.copy(sline, swline)
            elif os.path.exists(sline) and os.path.exists(swline):
                if os.path.isfile(swline):
                    Redis.lpush(Key, 'backup ' + line + '\n')
                    shutil.copy(swline, swline + '.bak')
                    shutil.copy(sline, swline)
                else:
                    shutil.rmtree(swline)
                    shutil.copytree(sline, swline, True)
            os.popen('find ' + swline + ' -name .svn|xargs rm -rf')
            scp2(Key, arg, wline, swline)
        if arg == 'recover':
            if os.path.isdir(swline):
                Redis.lpush(Key,'fail :%s is Directory not recover' %swline)
                sys.exit()
            else:
                Redis.lpush(Key, 'recover ' + line + '\n')
                shutil.copy(swline + '.bak', swline)
                scp2(Key, arg, wline, swline)

    def publish2(Key, arg, line, sline, wline, swline, ver, project):
        svn_co(Key, line, ssline, sdline, ver)
        sync2(Key, arg, line, sline, wline, swline, project)
        if os.path.exists(svn_path):
            shutil.rmtree(svn_path)
    try:
        if Redis.exists(publish_key):
            Info = Redis.rpop(publish_key)
            Redis.delete(publish_key)
            if Info:
                Info = eval(Info)
                Type = int(Info['arg'])
                Action = Info['action']
                Key_file_list = Info['Key_file_lis']
                Gray = Info['gray']
                List = Redis.get(Key_file_list)
                List = eval(List)
                ips,project = check_path(List,Key,Action,Gray)
                for line in List:
                    line = line.strip()
                    if line.startswith('#') or not line.split():
                        continue
                    m = re.match(r'[0-9]',line)
                    if m:
                        ver = line
                        continue
                    line = line.replace('\\','/')
                    line = line.replace('$','\$')
                    po = tuple(line.split('/'))
                    swline = '/'+'/'.join(po[3:])
                    wline = '/'+'/'.join(po[3:-1])
                    wline = web_path+wline
                    swline = web_path+swline
                    sdline = '/'+'/'.join(po[:-1])
                    ssline = svn_path+sdline
                    sline = svn_path+line
                    Redis.lpush(Key,'.'*80+'\n')
                    if Action == 'publish':
                        publish2(Key,Action,line,sline,wline,swline,ver,project)
                    if Action == 'recover':
                        sync2(Key,Action,line,sline,wline,swline)
                    Redis.lpush(Key,'.'*80+'\n')
                # 灰度发布初始化
                if Gray and Action == 'publish':
                    Redis.lpush(Key, '灰度发布信息:{0}    {1}'.format(ips[0], username))
                else:
                    cmd = "update php_list set Gray = '0' where project = '%s';" % project
                    MYSQL.Run(cmd)
                    MYSQL.Close()
            else:
                Redis.lpush(Key, '没有获取到上线相关信息,请重试!')
    except Exception as e:
        Redis.lpush(Key,'main:{0} fail'.format(e))
    finally:
        Redis.lpush(Key,'End')
        Redis.expire(Key, 30)
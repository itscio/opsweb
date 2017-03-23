#-*- coding: utf-8 -*-
import paramiko
from scp import SCPClient
import sys,os
import time
import hashlib
import io
import shutil
import zipfile
import Mysql,loging
import redis
import __init__
app = __init__.app
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
Redis = redis.Redis(redis_host, redis_port)
mysql_user = app.config.get('MYSQL_USER')
mysql_password = app.config.get('MYSQL_PASSWORD')
mysql_host = app.config.get('MYSQL_HOST')
mysql_port = app.config.get('MYSQL_PORT')
mysql_db = 'op'
MYSQL = Mysql.MYSQL(mysql_user,mysql_password,mysql_host,mysql_port,mysql_db)
svnUser = app.config.get('SVN_USER')
svnPassword = app.config.get('SVN_PASSWORD')
svnDir = app.config.get('SVN_FILE_DIR')
def java_update(publish_key,Message_key):
    # 计算文件md5
    def md5sum(path):
        m = hashlib.md5()
        file = io.FileIO(path, 'r')
        bytes = file.read(2048)
        while bytes != b'':
            m.update(bytes)
            bytes = file.read(2048)
        file.close()
        return m.hexdigest()

    def create_paths(war):
        cp = []
        list_dirs = os.walk(war)
        for root, dirs, files in list_dirs:
            for f in files:
                cp.append(os.path.join(root, f))
        return cp

    def svn_up(Project):
        try:
            os.system('export LC_CTYPE="zh_CN.UTF-8"')
            os.system('mkdir -p %s' % svnDir)
            os.system(
                "/usr/bin/svn export --no-auth-cache --non-interactive --username " + svnUser + " --password " + svnPassword + " http://svn.ibaihe.com:1722/svn/publish/%s" % Project + ' ' + '%s%s' % (
                svnDir, Project))
            if os.path.exists('%s%s' % (svnDir, Project)):
                f_zip = zipfile.ZipFile('%s%s' % (svnDir, Project), 'r')
                f_zip.extractall(svnDir)
                Redis.lpush(Message_key, '=>%s svn up success!' % Project)
                return '%s%s' % (svnDir, WarName)
            else:
                Redis.lpush(Message_key, '%s svn up fail!' % Project)
                sys.exit(1)
        except Exception as e:
            Redis.lpush(Message_key, 'svn:{0}'.format(e))

    def check_path(ServerList):
        try:
            paths = {}
            for ip, username in ServerList:
                key_file = '/home/' + username + '/.ssh/id_rsa'
                cmd = ['cd /home/' + username + ' && ls |grep jboss-', ]
                jb_name = ssh2(ip, username, key_file, cmd).strip()
                count = len(jb_name.split('\n'))
                if count == 1:
                    path = '/home/' + username + '/' + jb_name + '/server/default/deploy/' + WarName + '/'
                else:
                    Redis.lpush(Message_key, jb_name + '\n' + 'error,just one')
                    sys.exit(1)
                if Action == 'update':
                    cmd = ['[[ -d ' + path + ' && -w ' + path + ' ]] && echo True', ]
                if Action == 'rollback':
                    path = '/home/' + username + '/' + jb_name + '/server/default/deploy/' + WarName + '/'
                    cmd = ['[[ -d ' + path + ' && -d /tmp/' + username + '/' + WarName + ' ]] && echo True', ]
                values = ssh2(ip, username, key_file, cmd)
                if values:
                    K = '%s_%s' % (username, ip)
                    paths[K] = path
                else:
                    if Action == 'update':
                        Redis.lpush(Message_key, WarName + ' is not exist or not writable on ' + ip)
                    if Action == 'rollback':
                        Redis.lpush(Message_key, '%s not exist on %s ' % (WarName, ip))
                    sys.exit(1)
                Redis.lpush(Message_key, '=>check ' + ip + ' ' + username + ' pass\n')
            return (paths)
        except Exception as e:
            Redis.lpush(Message_key, 'check_path:{0}'.format(e))
            sys.exit()

    def ssh2(ip, username, key_file, cmd):
        try:
            ssh = paramiko.SSHClient()
            key = paramiko.RSAKey.from_private_key_file(key_file)
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, 22, username, pkey=key, timeout=30)
            for m in cmd:
                stdin, stdout, stderr = ssh.exec_command(m)
            return (stdout.read())
            ssh.close()
        except Exception as e:
            Redis.lpush(Message_key, 'ssh2:{0}'.format(e))
            sys.exit(1)

    def scp2(path):
        def reDl(str):
            if '$' in str:
                return str.replace('$', '\$')
            else:
                return str
        try:
            ssh = paramiko.SSHClient()
            key = paramiko.RSAKey.from_private_key_file(key_file)
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, 22, username, pkey=key, timeout=30)
            cmd = ['/usr/bin/rsync -av --delete ' + path + '/tmp/' + username + '/' + WarName + '/',
                   'rm -rf ' + path_jboss + '/server/default/{log,work}/*']
            for m in cmd:
                stdin, stdout, stderr = ssh.exec_command(m)
                err = stderr.read()
            if err:
                Redis.lpush(Message_key, err)
                sys.exit(1)
            else:
                Redis.lpush(Message_key, ' =>{0} {1} 备份{2}完成! '.format(ip, username, WarName))
            scp = SCPClient(ssh.get_transport())
            Redis.lpush(Message_key, '==>同步{0}到{1} '.format(WarName, path))
            stderr = scp.put('%s/' % WarDir, path, recursive=True, preserve_times=60)
            if stderr:
                Redis.lpush(Message_key, stderr)
                sys.exit(1)
            for p in create_paths(WarDir):
                l_md5sum = md5sum(p)
                p = p.split(WarName)[1].strip('/')
                cmd = '/usr/bin/md5sum %s' % (path + p)
                stdin, stdout, stderr = ssh.exec_command(reDl(cmd))
                r_md5sum = stdout.read().split()
                if l_md5sum == r_md5sum[0]:
                    Redis.lpush(Message_key, "====>{0}进行MD5验证通过!".format(path + p))
                else:
                    cmd = ['/usr/bin/rsync -av --delete /tmp/' + username + '/' + WarName + '/   ' + path, ]
                    ssh2(ip, username, key_file, cmd)
                    Redis.lpush(Message_key, '{0}进行MD5验证失败,{1}下文件已自动回滚!'.format(p, username))
                    sys.exit(1)
            Redis.lpush(Message_key, "=====>restart jboss on " + ip)
            cmd = ['source ~/.bash_profile && /usr/bin/killall -9 java']
            ssh2(ip, username, key_file, cmd)
            ssh.close()
        except Exception as e:
            Redis.lpush(Message_key, 'scp2:{0}'.format(e))
            sys.exit()

    try:
        if Redis.exists(publish_key):
            INFO = Redis.rpop(publish_key)
            Redis.delete(publish_key)
            if INFO:
                INFO = eval(INFO)
                Project = INFO['project']
                Action = INFO['Action']
                ServerList = INFO['ServerList']
                Gray = INFO['Gray']
                WarName = INFO['warname']
                if Action == 'update':
                    WarDir = svn_up(Project)
                paths = check_path(ServerList)
                for ip,username in ServerList:
                    key_file='/home/'+username+'/.ssh/id_rsa'
                    K = '%s_%s' %(username,ip)
                    path = paths.get(K)
                    path_home=path.split('server')
                    path_jboss=path_home[0]
                    time.sleep(5)
                    if Action == 'update':
                        scp2(path)
                        Redis.lpush(Message_key,'==>{0} {1} {2} 增量上线完成'.format(ip,username,WarName))
                    if Action == 'rollback':
                        cmd = ['/usr/bin/rsync -av --delete /tmp/'+username+'/'+WarName+'/   '+path,'/usr/bin/pkill -9 java']
                        ssh2(ip,username,key_file,cmd)
                        Redis.lpush(Message_key, '==>{0} {1} {2} 增量回滚完成'.format(ip, username, WarName))
                if os.path.exists(WarDir):
                    shutil.rmtree(WarDir)
                # 灰度发布
                if Gray and Action == 'update':
                    Redis.lpush(Message_key, '灰度发布信息:{0}   {1}'.format(ip,username))
                else:
                    cmd = "update java_list set Gray = '0' where project = '%s';" % WarName
                    MYSQL.Run(cmd)
                    MYSQL.Close()
            else:
                Redis.lpush(Message_key, '没有获取到上线相关信息,请重试!')
    except Exception as e:
        Redis.lpush(Message_key,'main:{0}'.format(e))
    finally:
        Redis.lpush(Message_key,'End')
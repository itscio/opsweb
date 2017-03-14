#-*- coding: utf-8 -*-
import os
import sys
import hashlib
import io
import shutil
import Mysql,loging
import paramiko
from scp import SCPClient
import redis
import __init__
app = __init__.app
web_path = '/home/work/baihe/'
tag_path = '{0}/tags'.format(web_path)
bak_path = '{0}/bak'.format(web_path)
username = 'work'
key_file = '/home/work/.ssh/id_rsa'
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
git_user = app.config.get('GIT_USER')
git_password = app.config.get('GIT_PASSWORD')
def php_publish(publish_Key,Key):
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
    # 从svn获取项目代码
    def svn_co(path, tag_path, App):
        try:
            Redis.lpush(Key, '-' * 60)
            Redis.lpush(Key, 'svn export %s' % path)
            os.system('export LC_CTYPE="zh_CN.UTF-8"')
            if not os.path.exists(tag_path):
                os.system("/bin/mkdir -p %s" % tag_path)
            if os.path.exists('%s%s.zip' % (web_path, App)):
                os.remove('%s%s.zip' % (web_path, App))
            if path.endswith('.zip'):
                os.system(
                    "/usr/bin/svn export --no-auth-cache --non-interactive --force --username {0} --password {1} http://svn.ibaihe.com:1722/svn/{2}  {3}/tags.zip".format(
                        svn_user, svn_password, path, web_path))
            else:
                os.system(
                    "/usr/bin/svn export --no-auth-cache --non-interactive --force --username {0} --password {1} http://svn.ibaihe.com:1722/svn/{2}  {3}".format(
                        svn_user, svn_password, path, tag_path))
                if not os.listdir(tag_path):
                    Redis.lpush(Key, 'svn up fail,check the svn path!')
                    sys.exit(0)
            if path.endswith('.zip'):
                zip_file = path.split('/')[-1]
                zip_file = zip_file.replace('.zip', '')
                if os.path.exists('%s/tags.zip' % web_path):
                    shutil.rmtree(tag_path)
                    os.system('cd %s && /usr/bin/unzip -o tags.zip' % web_path)
                    os.remove("%s/tags.zip" % web_path)
                    shutil.move("{0}{1}".format(web_path, zip_file), "{0}/tags".format(web_path))
            os.system('cd %s && /usr/bin/zip -qr %s.zip tags' % (web_path, App))
            shutil.rmtree(tag_path)
            if os.path.exists('%s%s.zip' % (web_path, App)):
                S_md5 = md5sum('%s%s.zip' % (web_path, App))
            else:
                raise "zip %s.zip fail!" % App
        except Exception as e:
            Redis.lpush(Key, 'svn_co:{0}'.format(e))
            sys.exit()
        return S_md5
    # 从git获取项目代码
    def git_co(path, tag_path, App):
        try:
            Redis.lpush(Key, '-' * 30 + '\n')
            Redis.lpush(Key, 'git clone http://git.baihe.com%s' % path)
            if not os.path.exists(web_path):
                os.system("/bin/mkdir -p %s" % tag_path)
            if os.path.exists('%s%s.zip' % (web_path, App)):
                os.remove('%s%s.zip' % (web_path, App))
            paths = path.split(';')
            path = paths[0]
            tag_name = paths[1]
            gitCoCmd = 'cd {0} && /usr/bin/git clone http://{1}:{2}@git.baihe.com{3} '.format(web_path, git_user,
                                                                                              git_password, path)
            os.system(gitCoCmd)
            if not os.path.exists('{0}{1}'.format(web_path, App)):
                Redis.lpush(Key, 'git clone fail!')
                sys.exit(0)
            else:
                gitCoCmd = 'cd {0}{1} && /usr/bin/git checkout {2}'.format(web_path, App, tag_name)
                results = os.popen(gitCoCmd)
                Redis.lpush(Key, results.read())
                os.rename('{0}{1}'.format(web_path, App), tag_path)
            os.system('cd {0} && /usr/bin/zip -qr {1}.zip tags'.format(web_path, App))
            shutil.rmtree(tag_path)
            S_md5 = md5sum('%s%s.zip' % (web_path, App))
        except Exception as e:
            Redis.lpush(Key, 'git_co:{0}'.format(e))
            sys.exit()
        return S_md5

    def Update(sip, S_md5, App, path):
        ssh = paramiko.SSHClient()
        key = paramiko.RSAKey.from_private_key_file(key_file)
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        for ip in sip:
            ip = ip.strip()
            Redis.lpush(Key, '-' * 60)
            Redis.lpush(Key, 'publish ' + path + ' to ' + ip + '\n')
            try:
                ssh.connect(ip, 22, username, pkey=key, timeout=15)
                cmd = "mkdir -p {0}".format(web_path)
                ssh.exec_command(cmd)
                scp = SCPClient(ssh.get_transport())
                scp.put('%s%s.zip' % (web_path, App), web_path)
                cmd = '/usr/bin/md5sum %s/%s.zip' % (web_path, App)
                stdin, stdout, stderr = ssh.exec_command(cmd)
                R_md5 = stdout.read().split()[0]
                if R_md5 == S_md5:
                    Redis.lpush(Key, '%s  md5 verify        --->pass!' % App)
                    Redis.lpush(Key, 'unzip start ......')
                    cmds = ['cd %s && /usr/bin/unzip -qo %s.zip && /bin/rm -f %s.zip' % (web_path, App, App),
                            '[ -e %s ] && echo ok' % tag_path]
                    for cmd in cmds:
                        stdin, stdout, stderr = ssh.exec_command(cmd)
                        result_zip = stdout.read().strip()
                    if result_zip == 'ok':
                        Redis.lpush(Key, '%s         --->unzip success!' % App)
                        Redis.lpush(Key, 'backup start ......')
                        cmds = ('/bin/mkdir -p %s' % bak_path,
                                '[ -e %s/%s ] && /bin/rm -rf %s/%s' % (bak_path, App, bak_path, App),
                                '[ -e %s%s ] && /bin/mv %s%s  %s/%s' % (web_path, App, web_path, App, bak_path, App))
                        for cmd in cmds:
                            stdin, stdout, stderr = ssh.exec_command(cmd)
                            result_backup = stderr.read()
                        if result_backup:
                            Redis.lpush(Key, result_backup)
                            Redis.lpush(Key, '%s         --->backup fail!' % App)
                        else:
                            Redis.lpush(Key, '%s         --->backup success!' % App)
                            Redis.lpush(Key, 'publish start ......')
                            cmd = '/bin/mv %s %s%s' % (tag_path, web_path, App)
                            stdin, stdout, stderr = ssh.exec_command(cmd)
                            result_rsync = stderr.read()
                            if result_rsync:
                                Redis.lpush(Key, result_rsync)
                                Redis.lpush(Key, '%s         --->publish fail!' % App)
                            else:
                                Redis.lpush(Key, '%s         --->publish success!' % App)
                                ssh.close()
                            Redis.lpush(Key, '-' * 60)
                    else:
                        Redis.lpush(Key, '%s         --->unzip fail!' % App)
                else:
                    Redis.lpush(Key, 'S_MD5:%r' % S_md5)
                    Redis.lpush(Key, 'R_MD5:%r' % R_md5)
                    Redis.lpush(Key, ' verify %s on %s fail!!!' % (App, ip))
            except Exception as e:
                Redis.lpush(Key, 'Update:{0}'.format(e))
                ssh.close()
                sys.exit()

    def Recover(App, sip):
        ssh = paramiko.SSHClient()
        key = paramiko.RSAKey.from_private_key_file(key_file)
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        for ip in sip:
            ip = ip.strip()
            Redis.lpush(Key, '-' * 60)
            Redis.lpush(Key, 'recover ' + App + ' to ' + ip + '\n')
            try:
                ssh.connect(ip, 22, username, pkey=key, timeout=15)
                cmds = ('/usr/bin/rsync -av --delete %s/%s/ %s/%s/' % (bak_path, App, web_path, App),
                        '[ -d %s/%s ] || echo ok' % (bak_path, App))
                for cmd in cmds:
                    stdin, stdout, stderr = ssh.exec_command(cmd)
                    Redis.lpush(Key, stderr.read())
                    va = stdout.read()
                    va = va.strip()
                if va == 'ok':
                    Redis.lpush(Key, '         --->recover success!\n')
                    ssh.close()
                else:
                    Redis.lpush(Key, 'Recover %s on %s fail!!!\n' % (App, ip))
            except Exception as e:
                Redis.lpush(Key, 'Recover:{0}'.format(e))
                ssh.close()
                sys.exit()
    if Redis.exists(publish_Key):
        INFO = Redis.rpop(publish_Key)
        if INFO:
            try:
                Info = eval(INFO)
                action = Info['action']
                path = Info['path']
                App = Info['app']
                sip = Info['sip']
                Gray = Info['gray']
                Way = Info['Way']
                if action == 'publish':
                    if Way == 'SVN':
                        S_md5 = svn_co(path,tag_path,App)
                    if Way == 'GIT':
                        S_md5 = git_co(path,tag_path,App)
                    Update(sip,S_md5,App,path)
                elif action == 'recover':
                    Recover(App,sip)
                if Gray and action == 'publish':
                    Redis.lpush(Key, '灰度发布信息:{0}    {1}'.format(sip[0], username))
                else:
                    cmd = "update php_list set Gray = '0' where project = '%s';" % App
                    MYSQL.Run(cmd)
                    MYSQL.Close()
            except Exception as e:
                Redis.lpush(Key,'main:{0}'.format(str(e)))
            finally:
                Redis.lpush(Key,'End')
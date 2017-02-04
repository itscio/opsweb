#-*- coding: utf-8 -*-
import paramiko
from scp import SCPClient
import sys
import os
import time
import redis
import mysql.connector as mysql
import ConfigParser
import shutil
#修改服务器灰度状态
class MYSQL(object):
    def __init__(self, user, password, host, port, db='mysql'):
        self.__user = user
        self.__password = password
        self.__host = host
        self.__port = port
        self.__db = db
        try:
            self.cnx = mysql.connect(user=self.__user, password=self.__password, host=self.__host, port=self.__port,
                                     db=self.__db)
        except:
            pass
        else:
            self.cur = self.cnx.cursor(buffered=True)

    def Run(self, cmd):
        try:
            self.cur.execute(cmd)
            self.cnx.commit()
            return [cu for cu in self.cur if self.cur if self.cur]
        except:
            pass

    def Close(self):
        self.cur.close()
        self.cnx.close()
#获取redis数据
def Get_key(myRedis):
    key = 'publish_java'
    INFO = myRedis.rpop(key)
    if INFO:
        if isinstance(INFO,str):
            INFO = eval(INFO)
            return INFO
    sys.exit()
#从svn获取war包
def svn_up(warZipName):
    path = "%s/script_svn.conf" % Path
    conf.read(path)
    svnUser = conf.get('SVN', 'USER')
    svnPassword = conf.get('SVN', 'PASSWORD')
    svnDir = conf.get('SVN', 'FILE_DIR')
    os.system('export LC_CTYPE="zh_CN.UTF-8"')
    shutil.rmtree(svnDir)
    os.system('/bin/mkdir -p %s' % svnDir)
    war_path = '%s%s'%(svnDir,warZipName)
    warTagName = warZipName.split('.zip')[0]
    if os.path.exists(war_path):
        os.remove(war_path)
    svnCoCmd = '/usr/bin/svn export --no-auth-cache --non-interactive --username %s --password %s http://svn.ibaihe.com:1722/svn/publish/produce/%s  %s' % (svnUser,svnPassword,warZipName,war_path)
    os.system(svnCoCmd)
    if os.path.exists(war_path):
        os.system('cd %s  &&  /usr/bin/unzip -qo %s' %(svnDir,warZipName))
        if os.path.exists("{0}{1}".format(svnDir,warTagName)):
           shutil.rmtree("{0}{1}".format(svnDir,warTagName))
        else:
            myRedis.lpush(Message_key, '%s name error!' % warTagName)
            sys.exit()
        myRedis.lpush(Message_key, '%s svn export success!' % warZipName)
        myRedis.lpush(Message_key, '*' * 60)
    else:
        myRedis.lpush(Message_key,'*'*60)
        myRedis.lpush(Message_key,'%s svn export fail!'%warZipName)
        myRedis.lpush(Message_key,'*'*60)
        sys.exit()
    return svnDir
#从git获取war包
def git_up(project):
    path = "%s/script_git.conf" % Path
    conf.read(path)
    gitUser = conf.get('GIT', 'USER')
    gitPassword = conf.get('GIT', 'PASSWORD')
    gitDir = conf.get('GIT', 'FILE_DIR')
    warname = project.split('/')[-1]
    war_path = '%s%s'%(gitDir,warname)
    if not os.path.isdir(gitDir):
        os.system('mkdir -p %s' % gitDir)
    if os.path.exists(war_path):
        os.remove(war_path)
    gitCoCmd = 'cd {0} && /usr/bin/git clone http://{1}:{2}@git.baihe.com/{3}' % (gitDir,gitUser,gitPassword,project)
    os.system(gitCoCmd)
    if os.path.exists(war_path):
        myRedis.lpush(Message_key, '%s git clone success!' % warZipName)
        myRedis.lpush(Message_key, '*' * 60)
    else:
        myRedis.lpush(Message_key,'*'*60)
        myRedis.lpush(Message_key,'%s git clone fail!'%warZipName)
        myRedis.lpush(Message_key,'*'*60)
        sys.exit()
    return war_path
#构造ssh连接
def _init_ssh(ip,username):
    keyFile = '/home/' +username+ '/.ssh/id_rsa'
    ssh = paramiko.SSHClient()
    key = paramiko.RSAKey.from_private_key_file(keyFile)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(ip,22,username,pkey=key,timeout=15)
    except Exception as e:
        myRedis.lpush(Message_key,'*'*60)
        myRedis.lpush(Message_key,'%s %s login fail!' %(ip,username))
        myRedis.lpush(Message_key,'*'*60)
        sys.exit()
    return ssh

def check_path(ssh,ip,username):
    #获取jboss目录并备份旧war包
    cmd = 'cd /home/' +username+ ' && ls |grep jboss-'
    stdin, stdout, stderr = ssh.exec_command(cmd)
    jbossName = stdout.read()
    count = len(jbossName.strip().splitlines())
    if count == 1:
        basePath = '/home/%s/%s/server/default/deploy/' %(username,jbossName.strip())
        myRedis.lpush(Message_key,'check %s %s env ---> Pass' %(ip,username))
    else:
        myRedis.lpush(Message_key,'*'*60)
        myRedis.lpush(Message_key,'%s -->jboss Directory just one!' %ip)
        myRedis.lpush(Message_key,'*'*60)
        sys.exit()
    return basePath
def Restart_java(ssh,warZipName):
    cmd = '/usr/bin/pkill -9 java'
    try:
        for i in xrange(3):
            time.sleep(1)
            ssh.exec_command(cmd)
        ssh.close()
    except Exception as e:
        myRedis.lpush(Message_key,'Restart_java:{0}'.format(e))
        myRedis.lpush(Message_key, '      %s --->restart Fail'%warZipName)
    else:
        myRedis.lpush(Message_key, '      %s --->restart Success'%warZipName)
def publish(warZipName,basePath,file_Dir,ssh):
    try:
        warTagName = warZipName.split('.zip')[0]
        scp = SCPClient(ssh.get_transport())
        myRedis.lpush(Message_key, '      {0} --->publish start ......'.format(warZipName))
        myRedis.lpush(Message_key, 'backup {0}{1}'.format(basePath, warName))
        cmds = ['/bin/mkdir -p {0}'.format(bakPath),'/usr/bin/rsync -av --delete %s%s/ %s%s/' %(basePath,warName,bakPath,warName)]
        for cmd in cmds:
            try:
                stdin, stdout, stderr = ssh.exec_command(cmd)
                if stderr.read():
                    myRedis.lpush(Message_key,cmd)
                    myRedis.lpush(Message_key, 'ERROR:{0}'.format(stderr.read()))
            except Exception as e:
                myRedis.lpush(Message_key,str(e))
                sys.exit()
        try:
            myRedis.lpush(Message_key, '      %s --->backup Success' % warName)
            myRedis.lpush(Message_key, "copy {0} to {1}:{2}".format(warZipName, ip, username))
            scp.put('%s%s'%(file_Dir,warZipName), '%s%s'%(basePath,warZipName))
            myRedis.lpush(Message_key, '      %s --->copy Success' % warZipName)
            myRedis.lpush(Message_key, "unzip {0} ......".format(warZipName))
            cmd = "cd %s  &&  /usr/bin/unzip -qo %s" % (basePath, warZipName)
            stdin, stdout, stderr = ssh.exec_command(cmd)
            if stderr.read():
                myRedis.lpush(Message_key, 'ERROR:{0}'.format(stderr.read()))
            cmd = "[ -d {0}{1} ]  && echo True ".format(basePath, warTagName)
            stdin, stdout, stderr = ssh.exec_command(cmd)
            if stderr.read():
                myRedis.lpush(Message_key, 'ERROR:{0}'.format(stderr.read()))
            Msg_zip = stdout.read().strip()
            if Msg_zip == 'True':
                myRedis.lpush(Message_key, '      %s --->unzip Success' % warZipName)
                myRedis.lpush(Message_key,"rsync  {0} to {1}".format(warTagName,warName))
                cmds = ["/bin/rm -rf {0}{1}".format(basePath,warName),"/usr/bin/rsync -av  --delete {0}{1}/  {0}{2}/".format(basePath,warTagName,warName),"/bin/rm -rf %s%s" %(basePath,warZipName) ,"/bin/rm -rf %s%s" %(basePath,warTagName)]
                for cmd in cmds:
                    stdin, stdout, stderr = ssh.exec_command(cmd)
                    if stderr.read():
                        myRedis.lpush(Message_key, cmd)
                        myRedis.lpush(Message_key, 'ERROR:{0}'.format(stderr.read()))
                cmd = "[ -d {0}{1} ]  && echo True ".format(basePath,warName)
                stdin, stdout, stderr = ssh.exec_command(cmd)
                if stderr.read():
                    myRedis.lpush(Message_key, 'ERROR:{0}'.format(stderr.read()))
                Msg_sync = stdout.read().strip()
                if Msg_sync == 'True':
                    myRedis.lpush(Message_key, '      %s --->Publish Success' % warZipName)
                    myRedis.lpush(Message_key, '*' * 60)
                    Restart_java(ssh, warZipName)
                else:
                    myRedis.lpush(Message_key, '      %s --->rsync Fail' % warName)
                    cmd = '/usr/bin/rsync -av --delete %s%s/ %s%s/' % (bakPath, warName, basePath, warName)
                    stdin, stdout, stderr = ssh.exec_command(cmd)
                    if stderr.read():
                        myRedis.lpush(Message_key, 'ERROR:{0}'.format(stderr.read()))
                    myRedis.lpush(Message_key, '      %s --->Publish Fail' % warZipName)
                    myRedis.lpush(Message_key, '*' * 60)
            else:
                myRedis.lpush(Message_key, '      %s --->unzip Fail' % warZipName)
        except Exception as e:
            cmd = '/usr/bin/rsync -av --delete %s%s/ %s%s/' % (bakPath, warName,basePath, warName)
            stdin, stdout, stderr = ssh.exec_command(cmd)
            if stderr.read():
                myRedis.lpush(Message_key,'ERROR:{0}'.format(stderr.read()))
            myRedis.lpush(Message_key, '*' * 60)
            myRedis.lpush(Message_key,str(e))
            myRedis.lpush(Message_key, '*' * 60)
    except Exception as e:
        myRedis.lpush(Message_key,'publish:{0}'.format(e))
        sys.exit()

def rollback(ssh,basePath,warName,warZipName):
    cmd = '/usr/bin/rsync -av --delete %s%s/ %s%s/' %(bakPath,warName,basePath,warName)
    try:
        stdin, stdout, stderr = ssh.exec_command(cmd)
        if stderr.read():
            myRedis.lpush(Message_key, 'ERROR:{0}'.format(stderr.read()))
    except Exception as e:
        myRedis.lpush(Message_key,str(e))
        myRedis.lpush(Message_key, '         %s  --->rollback fail!' % warZipName)
    else:
        myRedis.lpush(Message_key,'         %s --->rollback success!' %warZipName)
        Restart_java(ssh, warZipName)
if __name__ == '__main__':
    Message_key = 'None'
    Path = '/home/work/webroot/conf'
    conf = ConfigParser.ConfigParser()
    path = "%s/script_redis.conf" % Path
    conf.read(path)
    redis_host = conf.get('REDIS', 'HOST')
    redis_port = conf.getint('REDIS', 'PORT')
    myRedis = redis.Redis(redis_host, redis_port)
    path = "%s/script_sql.conf" % Path
    conf.read(path)
    mysql_host = conf.get('MYSQLDB', 'HOST')
    mysql_port = conf.getint('MYSQLDB', 'PORT')
    mysql_user = conf.get('MYSQLDB', 'USER')
    mysql_password = conf.get('MYSQLDB', 'PASSWORD')
    mysql_db = conf.get('MYSQLDB', 'DB')
    MySql = MYSQL(mysql_user, mysql_password, mysql_host, mysql_port, mysql_db)
    try:
        INFO = Get_key(myRedis)
        warZipName = INFO['warTagName']
        warName = INFO['warname']
        Action = INFO['Action']
        ServerList = INFO['ServerList']
        Message_key = INFO['key']
        Gray = INFO['Gray']
        Type = INFO['Type']
        Way = INFO['Way']
        if Action == 'publish':
            if Way == 'SVN':
                file_Dir = svn_up(warZipName)
            if Way == 'GIT':
                file_Dir = git_up(warZipName)
        for ip,username in ServerList:
            bakPath = '/home/%s/bak/'%username
            ssh  = _init_ssh(ip,username)
            basePath = check_path(ssh,ip,username)
            time.sleep(5)
            if Action == 'restart':
                Restart_java(ssh,warZipName)
            if Action == 'publish':
                publish(warZipName,basePath,file_Dir,ssh)
            if Action == 'rollback':
                rollback(ssh,basePath,warName,warZipName)
        if Gray and Action == 'publish':
            myRedis.lpush(Message_key, '灰度发布信息:{0}   {1}'.format(ip, username))
        else:
            cmd = "update java_list set Gray = '0' where project = '%s';" % warName
            MySql.Run(cmd)
            MySql.Close()
    except Exception as e:
        myRedis.lpush(Message_key,'main:{0}'.format(e))
        sys.exit()
    finally:
        myRedis.lpush(Message_key,'End')
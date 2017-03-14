#-*- coding: utf-8 -*-
import Mysql
import loging
import memcache
import time
import datetime
import os
import redis
import json
import socket
import __init__
app = __init__.app
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
Redis = redis.Redis(redis_host, redis_port)
USER = app.config.get('MYSQL_USER')
PASSWORD = app.config.get('MYSQL_PASSWORD')
HOST = app.config.get('MYSQL_HOST')
PORT = app.config.get('MYSQL_PORT')
TWEMPROXY_HOSTS = app.config.get('TWEMPROXY_HOSTS')
DB = 'idc'
def task_tables_info():
    MYSQL_IDC = Mysql.MYSQL(USER,PASSWORD,HOST,PORT,DB)
    Table = 'tableinfo'
    cmds = ("TRUNCATE TABLE %s;" %Table,"select ip,port,db from mysqldb;")
    results = map(MYSQL_IDC.Run,cmds)
    log_path = '/tmp/tables_info.log'
    for host,port,dbs in results[1]:
        try:
            if '172.16.9.' not in host:
                loging.write(host,log_path=log_path)
                MYSQL = Mysql.MYSQL(USER,PASSWORD,host,port,'mysql')
                cmd = "show variables like 'version';"
                version = MYSQL.Run(cmd)
                version = version[0][1]  or 'None'
                for db in dbs.split('|'):
                    cmd = "show table status from %s;"  %db
                    results = MYSQL.Run(cmd)
                    if results:
                        for table_info in results:
                            Table_Name = table_info[0]
                            Engine = table_info[1] or 'None'
                            Rows = table_info[4]  or 0
                            Charset = table_info[14]  or 'None'
                            cmd = ("insert into %s (ip,port,database_name,table_name,Engine_name,Rows,Charset,version)  VALUES ('%s',%i,'%s','%s','%s',%i,'%s','%s');" %(Table,host,int(port),db,Table_Name,Engine,Rows,Charset,version))
                            MYSQL_IDC.Run(cmd)
                MYSQL.Close()
        except Exception as e:
            loging.write(e)
        MYSQL_IDC.Close()

def clear_kestrel():
    MYSQL = Mysql.MYSQL(USER, PASSWORD, HOST, PORT, DB)
    cmd = "select kestrel_ip,kestrel_port,kestrel_key from kestrel where kestrel_num ='0';"
    results = MYSQL.Run(cmd)
    if results:
        MYSQL.Close()
        for ip,port,key in results:
            loging.write('%s %s %s delete......\n')  %(ip,port,key)
            try:
                Kestrel = memcache.Client(['%s:%s'%(ip,port)],debug=0,socket_timeout=1)
                Kestrel.delete(str(key))
            except:
                continue

def check_publish():
    def rollback_java(Project, warname, ServerList):
        information = {}
        information['warname'] = warname
        information['warTagName'] = Project
        information['ServerList'] = ServerList
        information['Action'] = 'publish'
        information['key'] = 'auto_rollback'
        information['Gray'] = False
        information['Type'] = '2'
        information['Way'] = 'SVN'
        Redis.delete('auto_rollback')
        Redis.lpush('publish_java', information)

    def rollback_php(Project, App, ServerList):
        Info = {}
        Info['action'] = 'publish'
        Info['key'] = 'auto_rollback'
        Info['path'] = Project
        Info['app'] = App
        Info['sip'] = ServerList
        Info['gray'] = False
        Info['Type'] = '2'
        Info['Way'] = 'SVN'
        Redis.lpush('publish_php', str(Info))
    td  = time.strftime('%Y-%m-%d',time.localtime())
    tt = (datetime.datetime.now()-datetime.timedelta(hours=4)).strftime('%H:%M:%S')
    MYSQL = Mysql.MYSQL(USER, PASSWORD, HOST, PORT, DB)
    cmd = "SELECT DISTINCT(project) FROM op_operation WHERE TYPE = '灰度' AND DATE  = '{0}' AND TIME <= '{1}';".format(td,tt)
    result  = MYSQL.Run(cmd)
    if result:
        for Project in result:
            os.system("/bin/tomail pd.list@baihe.com 灰度发布警告 {0} 项目已经保持灰度状态超过4个时间,请相关开发人员尽快处理!".format(Project[0]))
    cmd = "SELECT DISTINCT(project) FROM op_operation WHERE DATE = '{0}' AND TIME < '{1}' AND TYPE = '测外';".format(td,tt)
    results = MYSQL.Run(cmd)
    if results:
        results = [str(re[0]) for re in results]
        for Project in results:
            cmd = "SELECT DISTINCT(project) FROM op_operation WHERE DATE = '{0}' AND TIME > '{1}' AND TYPE = '线上' AND project = '{2}' ;".format(td,tt,Project)
            if MYSQL.Run(cmd):
                pass
                results.remove(Project)
        if results:
            for PRoject in results:
                if '.war.zip' in PRoject:
                    project = PRoject.split('-')[:-1]
                    project = '-'.join(project)
                    cmd = "SELECT ip,USER FROM java_list WHERE project = '{0}' AND TYPE = '2'".format(project + '.war')
                    ServerList = MYSQL.Run(cmd)
                    cmd = "SELECT project FROM op_operation WHERE TYPE = '线上' AND ACTION <> 'restart' and project like '{0}-%.war.zip' ORDER BY id DESC LIMIT 1;".format(project)
                    loging.write('java:{0}\n'.format(ServerList))
                elif 'tags' in PRoject:
                    App = PRoject.split('/')[3]
                    project = PRoject.split('tags')[-1]
                    project = project.replace('/','').split('-')[:-1]
                    project = '-'.join(project)
                    cmd = "SELECT ip,USER FROM php_list WHERE project = '{0}' AND TYPE = '2'".format(App)
                    ServerList = MYSQL.Run(cmd)
                    cmd = "SELECT project FROM op_operation WHERE TYPE = '线上' AND ACTION <> 'restart' and project like '%{0}%' ORDER BY id DESC LIMIT 1;".format(project)
                    loging.write('php:{0}\n'.format(ServerList))
                else:
                    continue
                result = MYSQL.Run(cmd)
                loging.write('project:{0}\n'.format(result))
                #os.system("/bin/tomail pd.list@baihe.com 测外发布警告 {0} 项目已经保持测外状态超过4个时间,请相关开发人员尽快处理!".format(Project[0]))
    MYSQL.Close()

def get_twemproxy_redis():
    MYSQL = Mysql.MYSQL(USER, PASSWORD, HOST, PORT, DB)
    redis_info = {}
    for twemproxy_ip in TWEMPROXY_HOSTS:
        try:
            sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            sock.connect((twemproxy_ip,22222))
            INFOS = json.loads(sock.recv(86400))
            for key in INFOS:
                if 'redis_' in key:
                    IP_list = []
                    for ip_key in INFOS[key]:
                        if '172.16.' in ip_key:
                            IP_list.append(ip_key.split(':')[0])
                    redis_info[key] = IP_list
        except Exception as e:
            loging.write(e)
            continue
    cmd = "TRUNCATE TABLE twemproxyInfo;"
    MYSQL.Run(cmd)
    for key in redis_info:
        for ip in redis_info[key]:
            try:
                Redis = redis.StrictRedis(host=ip,port=6379,db=0,socket_timeout=1)
                Keys = Redis.info()['db0']['keys']
                cmd = "insert into twemproxyInfo (serviceGroup,clientIP,clientKeyItems) VALUES('%s','%s','%s');"%(key,ip,Keys)
                MYSQL.Run(cmd)
            except:
                continue

    MYSQL.Close()


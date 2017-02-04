#!/usr/bin/env python
#-*- coding: utf-8 -*-
import time
import mysql.connector as mysql
from multiprocessing.dummy import Pool as Third_pool
import ConfigParser
from Modules import loging
class MYSQL(object):
    def __init__(self,user,password,host,port,db='mysql'):
        self.__user = user
        self.__password = password
        self.__host = host
        self.__port = port
        self.__db = db
        try:
            self.cnx = mysql.connect(user=self.__user,password=self.__password,host=self.__host,port=self.__port,db=self.__db)
        except:
            pass
        else:
            self.cur = self.cnx.cursor(buffered=True)
    def Run(self,cmd):
        try:
            self.cur.execute(cmd)
            self.cnx.commit()
            return [cu for cu in self.cur if self.cur if self.cur]
        except Exception as e:
            return e
    def Close(self):
        self.cur.close()
        self.cnx.close()
def Query_sql(user,password,ip,port,db,cmd):
    MYsql = MYSQL(user,password,ip,port,db)
    try:
        return MYsql.Run(cmd)
    except Exception as e:
        return e
    finally:
        MYsql.Close()
def Run_sql(val):
    id,IP,PORT,DB = val[:4]
    CMD = val[5]
    val = Query_sql(user,password,IP,PORT,DB,CMD)
    if val:
        val = str(val).replace("'",'')
    else:
        val = 'None'
    cmd = "update sql_scheduler set status = '已执行' ,results = '%s' where id = '%s';" %(val,id)
    Query_sql(user,password,host,port,db,cmd)
if __name__== "__main__":
    t = time.strftime('%Y-%m-%d',time.localtime())
    Path = '/home/work/webroot/conf'
    conf = ConfigParser.ConfigParser()
    path = "%s/script_sql.conf" % Path
    conf.read(path)
    host = conf.get('MYSQLDB', 'HOST')
    port = conf.getint('MYSQLDB', 'PORT')
    user = conf.get('MYSQLDB', 'USER')
    password = conf.get('MYSQLDB', 'PASSWORD')
    db = conf.get('MYSQLDB', 'DB')
    cmd = "select * from sql_scheduler where status = '未执行' and time = '%s';" %t
    values = Query_sql(user,password,host,port,db,cmd)
    try:
        if values:
            # 并发执行
            POOLS = Third_pool(10)
            POOLS.map_async(Run_sql,values)
            POOLS.close()
            POOLS.join()
    except Exception as e:
        loging.write(e)
#-*- coding: utf-8 -*-
import time
from multiprocessing.dummy import Pool as Third_pool
import loging,Mysql,check
import __init__
app = __init__.app
log_path = '/tmp/mysql_scheduler.log'
USER = app.config.get('MYSQL_USER')
PASSWORD = app.config.get('MYSQL_PASSWORD')
HOST = app.config.get('MYSQL_HOST')
PORT = app.config.get('MYSQL_PORT')
DB = 'op'
@check.proce_lock
def mysql_scheduler():
    t = time.strftime('%Y-%m-%d',time.localtime())
    MYSQL = Mysql.MYSQL(USER,PASSWORD,HOST,PORT,DB)
    def Run_sql(val):
        id, IP, PORT, DB = val[:4]
        CMD = val[5]
        val = Mysql.Query_sql(IP, PORT, DB, CMD)
        if val:
            val = str(val).replace("'", '')
        else:
            val = 'None'
        cmd = "update sql_scheduler set status = '已执行' ,results = '%s' where id = '%s';" % (val, id)
        loging.write(cmd,log_path=log_path)
        MYSQL.Run(cmd)
        MYSQL.Close()
    try:
        cmd = "select * from sql_scheduler where status = '未执行' and time = '%s';" % t
        values = MYSQL.Run(cmd)
        MYSQL.Close()
        if values:
            # 并发执行
            POOLS = Third_pool(10)
            POOLS.map_async(Run_sql,values)
            POOLS.close()
            POOLS.join()
    except Exception as e:
        loging.write(e,log_path=log_path)
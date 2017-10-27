#-*- coding: utf-8 -*-
import time
import loging,Mysql,check
import __init__
app = __init__.app
logging = loging.Error()
USER = app.config.get('MYSQL_USER')
PASSWORD = app.config.get('MYSQL_PASSWORD')
HOST = app.config.get('MYSQL_HOST')
PORT = app.config.get('MYSQL_PORT')
DB = 'op'
@check.proce_lock
def mysql_scheduler():
    t = time.strftime('%Y-%m-%d',time.localtime())
    MYSQL = Mysql.MYSQL(USER,PASSWORD,HOST,PORT,DB)
    try:
        def Run_sql(val):
            id, IP, PORT, DB = val[:4]
            CMD = val[5]
            val = Mysql.Query_sql(IP, PORT, DB, CMD)
            if val:
                val = str(val).replace("'", '')
            else:
                val = 'None'
            cmd = "update sql_scheduler set status = '已执行' ,results = '%s' where id = '%s';" % (val, id)
            MYSQL.Run(cmd)
            MYSQL.Close()
        cmd = "select * from sql_scheduler where status = '未执行' and time = '%s';" %t
        for values in MYSQL.Run(cmd):
            Run_sql(values)
        MYSQL.Close()
    except Exception as e:
        logging.error(e)
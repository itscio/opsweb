#-*- coding: utf-8 -*-
import mysql.connector as mysql
from module import loging
import conf
app = conf.app
logging = loging.Error()
mysql_user = app.config.get('MYSQL_USER')
mysql_password = app.config.get('MYSQL_PASSWORD')
mysql_host = app.config.get('MYSQL_HOST')
mysql_port = app.config.get('MYSQL_PORT')
class MYSQL(object):
    def __init__(self,user=mysql_user,password=mysql_password,host=mysql_host,port=mysql_port,db='mysql'):
        try:
            self.__user = user
            self.__password = password
            self.__host = host
            self.__port = port
            self.__db = db
            self.cnx = mysql.connect(user=self.__user,password=self.__password,host=self.__host,port=self.__port,db=self.__db)
            self.cur = self.cnx.cursor(buffered=True)
        except Exception as e:
            logging.error(e)
    def Run(self,cmd):
        try:
            self.cur.execute(cmd)
            self.cnx.commit()
        except Exception as e:
            logging.error(e)
        else:
            try:
                return [cu for cu in self.cur]
            except:
                return []
    def Close(self):
        if self.cur:
            self.cur.close()
        self.cnx.close()
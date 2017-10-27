#-*- coding: utf-8 -*-
import mysql.connector as mysql
import loging,db_op
import time
from flask import request
from sqlalchemy import and_,distinct
import __init__
app = __init__.app
logging = loging.Error()
user = app.config.get('MYSQL_USER')
password = app.config.get('MYSQL_PASSWORD')
class MYSQL(object):
    def __init__(self,user=user,password=password,host=None,port=None,db='mysql'):
        try:
            assert host,'host not null'
            assert port,'host not null'
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
            vue = [cu for cu in self.cur if cu]
            if vue:
                return vue
            return None
        except Exception as e:
            logging.error(e)
    def Close(self):
        if self.cur:
            self.cur.close()
        self.cnx.close()
def Query_sql(ip,port,db,cmd):
    MYsql = MYSQL(user = user,password = password,host = ip,port = port,db = db)
    try:
        MYsql.Run("SET NAMES UTF8")
        return MYsql.Run(cmd)
    except Exception as e:
        logging.error(e)
        return e
    finally:
        MYsql.Close()

class mysql_op(object):
    def __init__(self,user,action,Type=2,project='None',version='None',Gray = False,work = 'None',project_level = 0,changelog='None'):
        self.date = time.strftime('%Y-%m-%d',time.localtime())
        self.time = time.strftime('%H:%M:%S',time.localtime())
        self.List = {1: '线上', 2: "测外"}
        self.user = user
        self.action = action
        self.Type = Type
        self.project = project
        self.version = version
        self.work = work
        self.grade = project_level
        self.changelog = changelog
        if Gray:
            self.Type = '灰度'
        else:
            self.Type = self.List[self.Type]
        self.ip = request.headers.get('X-Forwarded-For')
        if self.ip:
            if len(self.ip.split(',')) >=2:
                self.ip = self.ip.split(',')[0]
        else:
            self.ip = request.remote_addr
    def op_operation(self):
        db = db_op.op_operation
        try:
            c = db(date=self.date, time=self.time, user=self.user,project=self.project,version=self.version,action=self.action,Type=self.Type,work=self.work,grade=self.grade,changelog=self.changelog)
            db_op.DB.session.add(c)
            if self.Type == '线上':
                db.query.filter(and_(db.project == self.project,db.Type != '测外')).update({db.Type:self.Type})
            db_op.DB.session.commit()
        except Exception as e:
            logging.error(e)
        finally:
            db_op.DB.session.remove()
    def op_log(self):
        db = db_op.op_log
        c = db(date = self.date,time = self.time,ip = self.ip,user = self.user,access=self.action)
        try:
            db_op.DB.session.add(c)
            db_op.DB.session.commit()
        except Exception as e:
            logging.error(e)
        finally:
            db_op.DB.session.remove()
def db_produce(Type):
    db = db_op.server_pool
    try:
        val_produce = db.query.with_entities(db.user,db.ip).filter(and_(db.Type == Type,db.status == '0',db.target == 'xs')).order_by(db.ip).all()
        val_test = db.query.with_entities(db.user,db.ip).filter(and_(db.Type == Type,db.status == '0',db.target == 'cw')).order_by(db.ip).all()
        return val_produce,val_test
    finally:
        db_op.DB.session.remove()

def db_list(Type):
    if Type == 'php':
        db = db_op.php_list
    if Type == 'java':
        db = db_op.java_list
    try:
        val = db.query.with_entities(distinct(db.project)).all()
        return val
    finally:
        db_op.DB.session.remove()
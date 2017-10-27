#-*- coding: utf-8 -*-
from flask_sqlalchemy import SQLAlchemy
import __init__
app = __init__.app
DB = SQLAlchemy(app)
class idc_mysqldb(DB.Model):
    __tablename__ = 'mysqldb'
    __bind_key__='idc'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    ip = DB.Column(DB.String(20))
    port = DB.Column(DB.String(8))
    db = DB.Column(DB.String(200))
    master = DB.Column(DB.String(8))
    slave = DB.Column(DB.String(8))
    Master_Host = DB.Column(DB.String(20))
    Master_User = DB.Column(DB.String(20))
    Master_Port = DB.Column(DB.String(8))
    def __init__(self,ip,port,DB,master,slave,Master_host,Master_User,Master_Port):
        self.ip = ip
        self.port = port
        self.DB = DB
        self.master = master
        self.slave = slave
        self.Master_Host = Master_host
        self.Master_User = Master_User
        self.Master_Port = Master_Port
    def __repr__(self):
        values=(self.ip,self.port,self.DB,self.master,self.slave,self.Master_Host,self.Master_User,self.Master_Port)
        return '%s,%s,%s,%s,%s,%s,%s,%s' %values

class idc_servers(DB.Model):
    __tablename__ = 'servers'
    __bind_key__='idc'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    cid = DB.Column(DB.String(20))
    sn = DB.Column(DB.String(30))
    type = DB.Column(DB.String(30))
    system = DB.Column(DB.String(30))
    cpu_core = DB.Column(DB.Integer)
    mem = DB.Column(DB.String(30))
    disk_size = DB.Column(DB.Integer)
    ip = DB.Column(DB.String(30))
    department = DB.Column(DB.String(30))
    status = DB.Column(DB.String(30))
    application = DB.Column(DB.String(20))
    comment = DB.Column(DB.String(30))
    def __init__(self,cid,sn,type,system,cpu_core,mem,disk_size,ip,department,status,application,comment):
        self.cid = cid
        self.sn = sn
        self.type = type
        self.system = system
        self.cpu_core = cpu_core
        self.mem = mem
        self.disk_size = disk_size
        self.ip = ip
        self.department = department
        self.status = status
        self.application = application
        self.comment = comment
    def __repr__(self):
        values=(self.cid,self.sn,self.type,self.system,self.cpu_core,self.mem,self.disk_size,self.ip,self.department,self.status,self.application,self.comment)
        return '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s'%values

class idc_networks(DB.Model):
    __tablename__ = 'networks'
    __bind_key__='idc'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    cid = DB.Column(DB.String(20))
    type = DB.Column(DB.String(30))
    ip = DB.Column(DB.String(30))
    status = DB.Column(DB.String(8))
    comment = DB.Column(DB.String(30))
    def __init__(self,cid,type,ip,status,comment):
        self.cid = cid
        self.type = type
        self.ip = ip
        self.status = status
        self.comment = comment
    def __repr__(self):
        values=(self.cid,self.type,self.ip,self.status,self.comment)
        return '%s,%s,%s,%s,%s'%values

class idc_app(DB.Model):
    __tablename__ = 'app'
    __bind_key__='idc'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    ip = DB.Column(DB.String(20))
    user = DB.Column(DB.String(30))
    appName = DB.Column(DB.String(100))
    domainName = DB.Column(DB.String(500))
    def __init__(self,ip,user,appName,domainName):
        self.ip = ip
        self.user = user
        self.appName = appName
        self.domainName = domainName
    def __repr__(self):
        values=(self.ip,self.user,self.appName,self.domainName)
        return '%s,%s,%s,%s'%values

class idc_store(DB.Model):
    __tablename__ = 'store'
    __bind_key__='idc'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    cid = DB.Column(DB.String(20))
    type = DB.Column(DB.String(30))
    ip = DB.Column(DB.String(20))
    department = DB.Column(DB.String(20))
    status = DB.Column(DB.String(8))
    comment = DB.Column(DB.String(30))
    def __init__(self,cid,type,ip,department,status,comment):
        self.cid = cid
        self.type = type
        self.ip = ip
        self.department = department
        self.status = status
        self.comment = comment
    def __repr__(self):
        values=(self.cid,self.type,self.ip,self.department,self.status,self.comment)
        return '%s,%s,%s,%s,%s,%s'%values

class idc_twemproxy(DB.Model):
    __tablename__ = 'twemproxyInfo'
    __bind_key__='idc'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    serviceType = DB.Column(DB.String(20))
    serviceGroup = DB.Column(DB.String(30))
    clientIP = DB.Column(DB.String(30))
    clientPort = DB.Column(DB.String(10))
    clientKey = DB.Column(DB.String(60))
    clientKeyItems = DB.Column(DB.String(60))
    comments = DB.Column(DB.String(200))
    def __init__(self,serviceType,serviceGroup,clientIP,clientPort,clientKey,clientKeyItems,comments):
        self.serviceType = serviceType
        self.serviceGroup = serviceGroup
        self.clientIP = clientIP
        self.clientPort = clientPort
        self.clientKey = clientKey
        self.clientKeyItems = clientKeyItems
        self.comments = comments
    def __repr__(self):
        values=(self.serviceType,self.serviceGroup,self.clientIP,self.clientPort,self.clientKey,self.clientKeyItems,self.comments)
        return '%s,%s,%s,%s,%s,%s,%s'%values

class idc_kestrel(DB.Model):
    __tablename__ = 'kestrel'
    __bind_key__='idc'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    kestrel_ip = DB.Column(DB.String(30))
    kestrel_port = DB.Column(DB.String(10))
    kestrel_key = DB.Column(DB.String(50))
    kestrel_num = DB.Column(DB.Integer)
    def __init__(self,kestrel_ip,kestrel_port,kestrel_key,kestrel_num):
        self.kestrel_ip = kestrel_ip
        self.kestrel_port = kestrel_port
        self.kestrel_key = kestrel_key
        self.kestrel_num = kestrel_num
    def __repr__(self):
        values=(self.kestrel_ip,self.kestrel_port,self.kestrel_key,self.kestrel_num)
        return '%s,%s,%s,%s'%values

class idc_tableinfo(DB.Model):
    __tablename__ = 'tableinfo'
    __bind_key__='idc'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    ip = DB.Column(DB.String(20))
    port = DB.Column(DB.Integer)
    database_name = DB.Column(DB.String(50))
    table_name = DB.Column(DB.String(30))
    Engine_name = DB.Column(DB.String(30))
    Rows = DB.Column(DB.Integer)
    Charset = DB.Column(DB.String(30))
    version = DB.Column(DB.String(30))
    def __init__(self,ip,port,database_name,table_name,Engine_name,Rows,Charset,version):
        self.ip = ip
        self.port = port
        self.database_name = database_name
        self.table_name = table_name
        self.Engine_name = Engine_name
        self.Rows = Rows
        self.Charset = Charset
        self.version = version
    def __repr__(self):
        values=(self.ip,self.port,self.database_name,self.table_name,self.Engine_name,self.Rows,self.Charset,self.version)
        return '%s,%i,%s,%s,%s,%i,%s,%s'%values

class idc_redis_cluster_info(DB.Model):
    __tablename__ = 'redis_cluster_info'
    __bind_key__='idc'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    getdate = DB.Column(DB.String(20))
    gettime = DB.Column(DB.String(20))
    master = DB.Column(DB.String(20))
    add_keys = DB.Column(DB.Integer)
    connected_clients = DB.Column(DB.Integer)
    HitRate = DB.Column(DB.Integer)
    commands = DB.Column(DB.Integer)
    net_input = DB.Column(DB.Integer)
    net_output = DB.Column(DB.Integer)
    def __init__(self,getdate,gettime,master,add_keys,connected_clients,HitRate,commands,net_input,net_output):
        self.getdate = getdate
        self.gettime = gettime
        self.master = master
        self.add_keys = add_keys
        self.connected_clients = connected_clients
        self.HitRate = HitRate
        self.commands = commands
        self.net_input = net_input
        self.net_output = net_output
    def __repr__(self):
        values=(self.getdate,self.gettime,self.master,self.add_keys,self.connected_clients,self.HitRate,self.commands,self.net_input,self.net_output)
        return '%s,%s,%s,%i,%i,%i,%i,%i,%i'%values
#-*- coding: utf-8 -*-
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
app = Flask(__name__)
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/sql.conf')
class apscheduler_jobs(DB.Model):
    __tablename__ = 'apscheduler_jobs'
    __bind_key__ = 'idc'
    id = DB.Column(DB.String(200),primary_key=True)
    next_run_time = DB.Column(DB.BigInteger)
    job_state = DB.Column(DB.BLOB)
    def __init__(self,id,next_run_time,job_state):
        self.id = id
        self.next_run_time = next_run_time
        with open(job_state,'rb') as f:
            self.job_state = f.read()
    def __repr__(self):
        values = (self.id,self.next_run_time,self.job_state)
        return '%s,%s,%r' % values

class idc_servers(DB.Model):
    __tablename__ = 'servers'
    __bind_key__='idc'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    idc_id = DB.Column(DB.Integer)
    ip = DB.Column(DB.String(20))
    ssh_port = DB.Column(DB.Integer)
    s_ip = DB.Column(DB.String(100))
    host_type = DB.Column(DB.String(20))
    hostname = DB.Column(DB.String(45))
    sn = DB.Column(DB.String(50))
    manufacturer = DB.Column(DB.String(50))
    productname = DB.Column(DB.String(50))
    system = DB.Column(DB.String(50))
    cpu_info = DB.Column(DB.String(50))
    cpu_core = DB.Column(DB.Integer)
    mem = DB.Column(DB.String(30))
    disk_count = DB.Column(DB.Integer)
    disk_size = DB.Column(DB.String(20))
    idrac = DB.Column(DB.String(30))
    purch_date = DB.Column(DB.String(30))
    expird_date = DB.Column(DB.String(30))
    status = DB.Column(DB.String(8))
    comment = DB.Column(DB.String(30))
    uptime = DB.Column(DB.String(45))
    def __init__(self,idc_id,ip,ssh_port,s_ip,host_type,hostname,sn,manufacturer,productname,system,
                 cpu_info,cpu_core,mem,disk_size,disk_count,idrac,purch_date,expird_date,status,
                 comment,uptime):
        self.idc_id = idc_id
        self.ip = ip
        self.s_ip = s_ip
        self.ssh_port = ssh_port
        self.host_type = host_type
        self.hostname = hostname
        self.sn = sn
        self.manufacturer = manufacturer
        self.productname = productname
        self.system = system
        self.cpu_info = cpu_info
        self.cpu_core = cpu_core
        self.mem = mem
        self.disk_count = disk_count
        self.disk_size = disk_size
        self.idrac = idrac
        self.purch_date = purch_date
        self.expird_date = expird_date
        self.status = status
        self.comment = comment
        self.uptime = uptime
    def __repr__(self):
        values=(self.idc_id,self.ip,self.ssh_port,self.s_ip,self.host_type,self.hostname,self.sn,self.manufacturer,
                self.productname,self.system,self.cpu_info,self.cpu_core,self.mem,self.disk_count,self.disk_size,
                self.idrac,self.purch_date,self.expird_date,self.status,self.comment,self.uptime)
        return '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s'%values

class idc_id(DB.Model):
    __tablename__ = 'idc_id'
    __bind_key__='idc'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    aid = DB.Column(DB.String(20))
    cid = DB.Column(DB.String(20))
    def __init__(self,aid,cid):
        self.aid = aid
        self.cid = cid
    def __repr__(self):
        values=(self.aid,self.cid)
        return '%s,%s'%values

class third_resource(DB.Model):
    __tablename__ = 'third_resource'
    __bind_key__='idc'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    resource_type = DB.Column(DB.String(30))
    cluster_type = DB.Column(DB.String(30))
    ip = DB.Column(DB.String(30))
    ssh_port = DB.Column(DB.Integer)
    app_port = DB.Column(DB.Integer)
    busi_id = DB.Column(DB.Integer)
    department = DB.Column(DB.String(30))
    person = DB.Column(DB.String(30))
    contact = DB.Column(DB.String(30))
    status = DB.Column(DB.String(8))
    update_date = DB.Column(DB.String(45))
    def __init__(self,resource_type,cluster_type,ip,ssh_port,app_port,busi_id,department,person,contact,status,update_date):
        self.resource_type = resource_type
        self.cluster_type = cluster_type
        self.ip = ip
        self.ssh_port = ssh_port
        self.app_port = app_port
        self.busi_id = busi_id
        self.department = department
        self.person = person
        self.contact = contact
        self.status = status
        self.update_date = update_date
    def __repr__(self):
        values=(self.resource_type,self.cluster_type,self.ip,self.ssh_port,self.app_port,self.busi_id,self.department,self.person,self.contact,self.status,self.update_date)
        return '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s'%values

class idc_networks(DB.Model):
    __tablename__ = 'networks'
    __bind_key__='idc'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    idc_id = DB.Column(DB.Integer)
    type = DB.Column(DB.String(20))
    ip = DB.Column(DB.String(30))
    redundance = DB.Column(DB.String(8))
    purch_date = DB.Column(DB.String(20))
    expird_date = DB.Column(DB.String(20))
    status = DB.Column(DB.String(8))
    comment = DB.Column(DB.String(30))
    def __init__(self,idc_id,type,ip,redundance,purch_date,expird_date,status,comment):
        self.idc_id = idc_id
        self.type = type
        self.ip = ip
        self.redundance = redundance
        self.purch_date = purch_date
        self.expird_date = expird_date
        self.status = status
        self.comment = comment
    def __repr__(self):
        values=(self.idc_id,self.type,self.ip,self.redundance,self.purch_date,self.expird_date,self.status,self.comment)
        return '%s,%s,%s,%s,%s,%s,%s,%s'%values

class idc_store(DB.Model):
    __tablename__ = 'store'
    __bind_key__='idc'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    idc_id = DB.Column(DB.Integer)
    type = DB.Column(DB.String(30))
    ip = DB.Column(DB.String(20))
    purch_date = DB.Column(DB.String(20))
    expird_date = DB.Column(DB.String(20))
    status = DB.Column(DB.String(8))
    comment = DB.Column(DB.String(30))
    def __init__(self,idc_id,type,ip,purch_date,expird_date,status,comment):
        self.idc_id = idc_id
        self.type = type
        self.ip = ip
        self.purch_date = purch_date
        self.expird_date = expird_date
        self.status = status
        self.comment = comment
    def __repr__(self):
        values=(self.idc_id,self.type,self.ip,self.purch_date,self.expird_date,self.status,self.comment)
        return '%s,%s,%s,%s,%s,%s,%s'%values

class idc_mysqldb(DB.Model):
    __tablename__ = 'mysqldb'
    __bind_key__='idc'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    ip = DB.Column(DB.String(20))
    port = DB.Column(DB.Integer)
    db = DB.Column(DB.String(500))
    master = DB.Column(DB.String(8))
    slave = DB.Column(DB.String(8))
    Master_Host = DB.Column(DB.String(20),default=None)
    Master_User = DB.Column(DB.String(20),default=None)
    Master_Port = DB.Column(DB.String(8),default=None)
    def __init__(self,ip,port,db,master,slave,Master_Host,Master_User,Master_Port):
        self.ip = ip
        self.port = port
        self.db = db
        self.master = master
        self.slave = slave
        self.Master_Host = Master_Host
        self.Master_User = Master_User
        self.Master_Port = Master_Port
    def __repr__(self):
        values=(self.ip,self.port,self.db,self.master,self.slave,self.Master_Host,self.Master_User,self.Master_Port)
        return '%s,%i,%s,%s,%s,%s,%s,%s' %values

class idc_tableinfo(DB.Model):
    __tablename__ = 'tableinfo'
    __bind_key__='idc'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    ip = DB.Column(DB.String(20))
    port = DB.Column(DB.Integer)
    database_name = DB.Column(DB.String(50))
    table_name = DB.Column(DB.String(50))
    Engine_name = DB.Column(DB.String(50))
    Rows = DB.Column(DB.Integer)
    size = DB.Column(DB.String(50))
    Charset = DB.Column(DB.String(50))
    version = DB.Column(DB.String(50))
    update_time = DB.Column(DB.DateTime)
    def __init__(self,ip,port,database_name,table_name,Engine_name,Rows,size,Charset,version,update_time):
        self.ip = ip
        self.port = port
        self.database_name = database_name
        self.table_name = table_name
        self.Engine_name = Engine_name
        self.Rows = Rows
        self.size = size
        self.Charset = Charset
        self.version = version
        self.update_time = update_time
    def __repr__(self):
        values=(self.ip,self.port,self.database_name,self.table_name,self.Engine_name,self.Rows,self.size,self.Charset,self.version,self.update_time)
        return '%s,%i,%s,%s,%s,%i,%s,%s,%s,%s'%values

class resource_ip(DB.Model):
    __tablename__ = 'resource_ip'
    __bind_key__='idc'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    aid = DB.Column(DB.String(20))
    network = DB.Column(DB.String(30))
    def __init__(self,aid,network):
        self.aid = aid
        self.network = network
    def __repr__(self):
        values=(self.aid,self.network)
        return '%s,%s'%values

class zabbix_info(DB.Model):
    __tablename__ = 'zabbix_info'
    __bind_key__='idc'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    ip = DB.Column(DB.String(20))
    ssh_port = DB.Column(DB.Integer)
    hostname = DB.Column(DB.String(50))
    icmpping = DB.Column(DB.Integer)
    cpu_load = DB.Column(DB.Float)
    mem_use = DB.Column(DB.Float)
    disk_io = DB.Column(DB.Float)
    openfile = DB.Column(DB.Integer)
    update_time = DB.Column(DB.String(45))
    def __init__(self,ip,ssh_port,hostname,icmpping,cpu_load,mem_use,disk_io,openfile,update_time):
        self.ip = ip
        self.ssh_port = ssh_port
        self.hostname = hostname
        self.icmpping =icmpping
        self.cpu_load = cpu_load
        self.mem_use = mem_use
        self.disk_io = disk_io
        self.openfile = openfile
        self.update_time = update_time
    def __repr__(self):
        values=(self.ip,self.ssh_port,self.hostname,self.icmpping,self.cpu_load,self.mem_use,self.disk_io,self.openfile,self.update_time)
        return '%s,%i,%s,%i,%i,%i,%i,%i,%s'%values

class crontabs(DB.Model):
    __tablename__ = 'crontabs'
    __bind_key__='idc'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    cron = DB.Column(DB.String(45))
    user = DB.Column(DB.String(45))
    action = DB.Column(DB.String(500))
    server_id = DB.Column(DB.Integer)
    update_date = DB.Column(DB.String(45))
    def __init__(self,cron,user,action,server_id,update_time):
        self.cron = cron
        self.user = user
        self.action = action
        self.server_id = server_id
        self.update_date = update_time
    def __repr__(self):
        values=(self.cron,self.user,self.action,self.server_id,self.update_date)
        return '%s,%s,%s,%i,%s'%values

class hosts(DB.Model):
    __tablename__ = 'hosts'
    __bind_key__='idc'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    host = DB.Column(DB.String(45))
    hostname = DB.Column(DB.String(100))
    server_id = DB.Column(DB.Integer)
    update_date = DB.Column(DB.String(45))
    def __init__(self,host,hostname,server_id,update_time):
        self.host = host
        self.hostname = hostname
        self.server_id = server_id
        self.update_date = update_time
    def __repr__(self):
        values=(self.host,self.hostname,self.server_id,self.update_date)
        return '%s,%s,%i,%s'%values

class redis_info(DB.Model):
    __tablename__ = 'redis_info'
    __bind_key__='idc'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    server_id = DB.Column(DB.String(50))
    port = DB.Column(DB.Integer)
    masterauth = DB.Column(DB.String(50))
    requirepass = DB.Column(DB.String(50))
    master = DB.Column(DB.String(8))
    slave = DB.Column(DB.String(8))
    cluster = DB.Column(DB.String(8))
    Master_Host = DB.Column(DB.String(20))
    Master_Port = DB.Column(DB.String(8))
    start_time = DB.Column(DB.String(45))
    last_time = DB.Column(DB.String(45))
    def __init__(self,server_id,port,masterauth,requirepass,master,slave,cluster,Master_host,Master_Port,start_time,last_time):
        self.server_id = server_id
        self.port = port
        self.masterauth = masterauth
        self.requirepass = requirepass
        self.master = master
        self.slave = slave
        self.cluster = cluster
        self.Master_Host = Master_host
        self.Master_Port = Master_Port
        self.start_time = start_time
        self.last_time = last_time
    def __repr__(self):
        values=(self.server_id,self.port,self.masterauth,self.requirepass,self.master,self.slave,self.cluster,self.Master_Host,self.Master_Port,self.start_time,self.last_time)
        return '%i,%i,%s,%s,%s,%s,%s,%s,%i,%s,%s' %values

class kafka_topic(DB.Model):
    __tablename__ = 'kafka_topic'
    __bind_key__='idc'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    topic = DB.Column(DB.String(100))
    partitions = DB.Column(DB.Integer)
    offsets_prv = DB.Column(DB.Float)
    update_time = DB.Column(DB.DateTime)
    def __init__(self,topic,partitions,offsets_prv,update_time):
        self.topic = topic
        self.partitions = partitions
        self.offsets_prv = offsets_prv
        self.update_time = update_time
    def __repr__(self):
        values=(self.topic,self.partitions,self.offsets_prv,self.update_time)
        return '%s,%i,%i,%s'%values

class k8s_pods(DB.Model):
    __tablename__ = 'k8s_pods'
    __bind_key__='idc'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    context = DB.Column(DB.String(45))
    pod_ip = DB.Column(DB.String(45))
    pod_name = DB.Column(DB.String(100))
    node_name = DB.Column(DB.String(45))
    uptime = DB.Column(DB.String(45))
    def __init__(self,context,pod_ip,pod_name,node_name,uptime):
        self.context = context
        self.pod_ip = pod_ip
        self.pod_name = pod_name
        self.node_name = node_name
        self.uptime = uptime
    def __repr__(self):
        values=(self.context,self.pod_ip,self.pod_name,self.node_name,self.uptime)
        return '%s,%s,%s,%s,%s'%values
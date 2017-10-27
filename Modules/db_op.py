#-*- coding: utf-8 -*-
from flask_sqlalchemy import SQLAlchemy
import __init__
app = __init__.app
DB = SQLAlchemy(app)
class users(DB.Model):
    __tablename__ = 'users'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    name = DB.Column(DB.String(100))
    passwd = DB.Column(DB.String(100))
    system = DB.Column(DB.String(100))
    host = DB.Column(DB.String(100))
    def __init__(self,name,passwd,system,host):
        self.name = name
        self.passwd = passwd
        self.system = system
        self.host = host
    def __repr__(self):
        values=(self.name,self.passwd,self.system,self.host)
        return '%s,%s,%s,%s'%values

class idc_users(DB.Model):
    __tablename__ = 'idc_users'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    name = DB.Column(DB.String(100))
    passwd = DB.Column(DB.String(100))
    grade = DB.Column(DB.Integer)
    def __init__(self,name,passwd,grade):
        self.name = name
        self.passwd = passwd
        self.grade = grade
    def __repr__(self):
        values=(self.name,self.passwd,self.grade)
        return '%s,%s,%s' % values

class php_list(DB.Model):
    __tablename__ = 'php_list'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    project = DB.Column(DB.String(30),index=True)
    user = DB.Column(DB.String(8))
    ip = DB.Column(DB.String(30),index=True)
    type = DB.Column(DB.Integer)
    Gray =  DB.Column(DB.Enum('0','1'))
    operation = DB.Column(DB.String(20))
    def __init__(self,project,user,ip,type,Gray,operation):
        self.project = project
        self.user = user
        self.ip = ip
        self.type = type
        self.Gray = Gray
        self.operation  = operation
    def __repr__(self):
        values=(self.project,self.user,self.ip,self.type,self.Gray,self.operation)
        return '%s,%s,%s,%s,%s,%s' % values

class java_list(DB.Model):
    __tablename__ = 'java_list'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    project = DB.Column(DB.String(50),index=True)
    user = DB.Column(DB.String(8))
    ip = DB.Column(DB.String(30),index=True)
    type = DB.Column(DB.Integer)
    Gray =  DB.Column(DB.Enum('0','1'))
    operation = DB.Column(DB.String(20))
    def __init__(self,project,user,ip,type,Gray,operation):
        self.project = project
        self.user = user
        self.ip = ip
        self.type = type
        self.Gray = Gray
        self.operation = operation
    def __repr__(self):
        values=(self.project,self.user,self.ip,self.type,self.Gray,self.operation)
        return '%s,%s,%s,%s,%s,%s' % values

class haproxy_conf(DB.Model):
    __tablename__ = 'haproxy_conf'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    domain = DB.Column(DB.String(30),index=True)
    balance = DB.Column(DB.String(12))
    monitor = DB.Column(DB.String(50))
    session = DB.Column(DB.String(2),default='0')
    ip = DB.Column(DB.String(16))
    port = DB.Column(DB.Integer)
    maxconn = DB.Column(DB.Integer)
    backup = DB.Column(DB.Enum('0','1'))
    intranet = DB.Column(DB.Enum('0','1'))
    Type = DB.Column(DB.Enum('xs','cw','hd'))
    def __init__(self,domain,balance,monitor,session,ip,port,maxconn,backup,intranet,Type):
        self.domain = domain
        self.balance = balance
        self.monitor = monitor
        self.session = session
        self.ip = ip
        self.port = port
        self.maxconn = maxconn
        self.backup = backup
        self.intranet = intranet
        self.Type = Type

    def __repr__(self):
        values=(self.domain,self.balance,self.monitor,self.session,self.ip,self.port,self.maxconn,self.backup,self.intranet,self.Type)
        return '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s' % values

class svn_users(DB.Model):
    __tablename__ = 'svn_users'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    user = DB.Column(DB.String(30))
    password = DB.Column(DB.String(30))
    status = DB.Column(DB.Integer())
    def __init__(self,user,password,status):
        self.user = user
        self.password = password
        self.status = status
    def __repr__(self):
        values=(self.user,self.password,self.status)
        return '%s,%s,%i'%values

class svn_permission(DB.Model):
    __tablename__ = 'svn_permission'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    groups = DB.Column(DB.String(50))
    path = DB.Column(DB.String(100))
    permission = DB.Column(DB.String(8))
    def __init__(self,groups,path,permission):
        self.groups = groups
        self.path = path
        self.permission = permission
    def __repr__(self):
        values=(self.groups,self.path,self.permission)
        return '%s,%s,%s'%values

class svn_groups(DB.Model):
    __tablename__ = 'svn_groups'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    groups = DB.Column(DB.String(50))
    users = DB.Column(DB.String(50))
    def __init__(self,groups,users):
        self.groups = groups
        self.users = users
    def __repr__(self):
        values=(self.groups,self.users)
        return '%s,%s'%values

class sql_scheduler(DB.Model):
    __tablename__ = 'sql_scheduler'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    master_ip = DB.Column(DB.String(20))
    master_port = DB.Column(DB.Integer)
    db = DB.Column(DB.String(50))
    time = DB.Column(DB.String(20))
    sql_cmd = DB.Column(DB.String(1000))
    status = DB.Column(DB.String(20))
    results = DB.Column(DB.String(1000))
    def __init__(self,master_ip,master_port,db,time,sql_cmd,status,results):
        self.master_ip = master_ip
        self.master_port = master_port
        self.db = db
        self.time = time
        self.sql_cmd = sql_cmd
        self.status = status
        self.results = results
    def __repr__(self):
        values=(self.master_ip,self.master_port,self.db,self.time,self.sql_cmd,self.status,self.results)
        return '%s,%s,%s,%s,%s,%s,%s'%values

class rota(DB.Model):
    __tablename__ = 'rota'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    name = DB.Column(DB.String(30))
    duty = DB.Column(DB.String(20))
    date = DB.Column(DB.String(30))
    def __init__(self,name,duty,date):
        self.name = name
        self.duty = duty
        self.date = date
    def __repr__(self):
        values=(self.name,self.duty,self.date)
        return '%s,%s,%ss'%values


class op_operation(DB.Model):
    __tablename__ = 'op_operation'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    date = DB.Column(DB.String(20))
    time = DB.Column(DB.String(20))
    user = DB.Column(DB.String(20))
    project = DB.Column(DB.String(100))
    version = DB.Column(DB.String(20))
    action = DB.Column(DB.String(20))
    Type = DB.Column(DB.String(8))
    work = DB.Column(DB.String(30))
    grade = DB.Column(DB.Integer)
    changelog = DB.Column(DB.String(1000))
    def __init__(self,date,time,user,project,version,action,Type,work,grade,changelog):
        self.date = date
        self.time = time
        self.user = user
        self.project = project
        self.version = version
        self.action = action
        self.Type = Type
        self.work = work
        self.grade = grade
        self.changelog = changelog
    def __repr__(self):
        values=(self.date,self.time,self.user,self.project,self.version,self.action,self.Type,self.work,self.grade,self.changelog)
        return '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s'%values

class op_log(DB.Model):
    __tablename__ = 'op_log'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    date = DB.Column(DB.String(20))
    time = DB.Column(DB.String(20))
    ip = DB.Column(DB.String(20))
    user = DB.Column(DB.String(20))
    access = DB.Column(DB.String(200))
    def __init__(self,date,time,ip,user,access):
        self.date = date
        self.time = time
        self.ip = ip
        self.user = user
        self.access = access
    def __repr__(self):
        values=(self.date,self.time,self.ip,self.user,self.access)
        return '%s,%s,%s,%s,%s'%values

class server_pool(DB.Model):
    __tablename__ = 'server_pool'
    __bind_key__ = 'op'
    id = DB.Column(DB.Integer, primary_key=True, autoincrement=True)
    Type = DB.Column(DB.Enum('php','java'))
    user = DB.Column(DB.Enum('work','java','java2','java3','java4'))
    ip = DB.Column(DB.String(30))
    status = DB.Column(DB.Enum('0','1'))
    target = DB.Column(DB.Enum('xs', 'cw'))
    def __init__(self, Type, user,ip, status,target):
        self.Tpye = Type
        self.user = user
        self.ip = ip
        self.status = status
        self.target = target

    def __repr__(self):
        values = (self.Type, self.user, self.ip, self.status,self.target)
        return '%s,%s,%s,%s,%s' % values

class publish_code(DB.Model):
    __tablename__ = 'publish_code'
    __bind_key__ = 'op'
    id = DB.Column(DB.Integer, primary_key=True, autoincrement=True)
    project = DB.Column(DB.String(100))
    code = DB.Column(DB.String(20))
    platfrom = DB.Column(DB.String(20))
    user = DB.Column(DB.String(20))
    Time = DB.Column(DB.String(20))
    def __init__(self,project,code,platfrom,user,Time):
        self.project = project
        self.code = code
        self.platfrom = platfrom
        self.user = user
        self.Time = Time

    def __repr__(self):
        values = (self.project,self.platfrom,self.code, self.user,self.Time)
        return '%s,%s,%s,%s,%s' % values

class dns_innr(DB.Model):
    __tablename__ = 'dns_innr'
    __bind_key__ = 'op'
    id = DB.Column(DB.Integer, primary_key=True, autoincrement=True)
    domain = DB.Column(DB.String(30))
    field = DB.Column(DB.String(50))
    Type = DB.Column(DB.String(30))
    ip = DB.Column(DB.String(100))
    stats = DB.Column(DB.Enum('0','1'))
    system = DB.Column(DB.Enum('cw', 'xs'))
    def __init__(self,domain,field,Type,ip,stats,system):
        self.domain = domain
        self.field = field
        self.Type = Type
        self.ip = ip
        self.stats = stats
        self.system = system

    def __repr__(self):
        values = (self.domain,self.field,self.Type, self.ip,self.stats,self.system)
        return '%s,%s,%s,%s,%s,%s' % values

class op_menu(DB.Model):
    __tablename__ = 'op_menu'
    __bind_key__ = 'op'
    id = DB.Column(DB.Integer, primary_key=True, autoincrement=True)
    Menu = DB.Column(DB.String(10))
    Menu_id = DB.Column(DB.Integer)
    Menu_name = DB.Column(DB.String(10))
    id_name = DB.Column(DB.String(20))
    module_name = DB.Column(DB.String(50))
    action_name = DB.Column(DB.String(50))
    grade = DB.Column(DB.Integer)
    def __init__(self,Menu,Menu_id,Menu_name,id_name,module_name,action_name,grade):
        self.Menu = Menu
        self.Menu_id = Menu_id
        self.Menu_name = Menu_name
        self.id_name = id_name
        self.module_name = module_name
        self.action_name = action_name
        self.grade = grade

    def __repr__(self):
        values = (self.Menu,self.Menu_id,self.Menu_name,self.id_name,self.module_name,self.action_name,self.grade)
        return '%s,%s,%s,%s,%s,%s,%s' % values

class apscheduler_jobs(DB.Model):
    __tablename__ = 'apscheduler_jobs'
    __bind_key__ = 'op'
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

class haproxy_blacklist(DB.Model):
    __tablename__ = 'haproxy_blacklist'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    addtime = DB.Column(DB.String(30))
    ip = DB.Column(DB.String(16))
    stats = DB.Column(DB.Enum('0','1'))
    expire = DB.Column(DB.String(30))
    rule = DB.Column(DB.String(100))
    def __init__(self,addtime,ip,stats,expire,rule):
        self.addtime = addtime
        self.ip = ip
        self.stats = stats
        self.expire = expire
        self.rule = rule
    def __repr__(self):
        values=(self.addtime,self.ip,self.stats,self.expire,self.rule)
        return '%s,%s,%s,%s,%s' % values

class vpn_users(DB.Model):
    __tablename__ = 'vpn_users'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    user = DB.Column(DB.String(30))
    password = DB.Column(DB.String(100))
    status = DB.Column(DB.Integer())
    vpn_type = DB.Column(DB.Enum('intranet', 'internet'))
    def __init__(self,user,password,status,vpn_type):
        self.user = user
        self.password = password
        self.status = status
        self.vpn_type = vpn_type
    def __repr__(self):
        values=(self.user,self.password,self.status,self.vpn_type)
        return '%s,%s,%i,%s'%values

class url_blacklist(DB.Model):
    __tablename__ = 'url_blacklist'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    url = DB.Column(DB.String(100))
    counts = DB.Column(DB.Integer)
    stats = DB.Column(DB.Enum('0', '1'))
    def __init__(self,url,counts,stats):
        self.url = url
        self.counts = counts
        self.stats = stats
    def __repr__(self):
        values=(self.url,self.counts,self.stats)
        return '%s,%s,%s' % values

class project_level(DB.Model):
    __tablename__ = 'project_level'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    project = DB.Column(DB.String(50),unique=True)
    level = DB.Column(DB.Enum('1', '2','3', '4','5', '6','7'))
    def __init__(self,project,level):
        self.project = project
        self.level = level
    def __repr__(self):
        values=(self.project,self.level)
        return '%s,%s' % values

class project_apply(DB.Model):
    __tablename__ = 'project_apply'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    project = DB.Column(DB.String(50),index=True)
    types = DB.Column(DB.String(20),index=True)
    describe = DB.Column(DB.String(500))
    content = DB.Column(DB.String(500))
    Rollback = DB.Column(DB.String(500))
    sender = DB.Column(DB.String(30),index=True)
    def __init__(self,project,types,describe,content,Rollback,sender):
        self.project = project
        self.types = types
        self.describe = describe
        self.content = content
        self.Rollback = Rollback
        self.sender = sender
    def __repr__(self):
        values=(self.project,self.types,self.describe,self.content,self.Rollback,self.sender)
        return '%s,%s,%s,%s,%s,%s' % values

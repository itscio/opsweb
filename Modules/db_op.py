#-*- coding: utf-8 -*-
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)
app.config.from_pyfile('../conf/sql.conf')
DB = SQLAlchemy(app)
class user_auth(DB.Model):
    __tablename__ = 'user_auth'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    name = DB.Column(DB.String(20))
    openid = DB.Column(DB.String(100))
    dingId = DB.Column(DB.String(100))
    grade = DB.Column(DB.String(20))
    token = DB.Column(DB.String(45))
    update_time = DB.Column(DB.String(20))
    def __init__(self,name,openid,dingId,grade,token,update_time):
        self.name = name
        self.openid = openid
        self.dingId = dingId
        self.grade = grade
        self.token = token
        self.update_time = update_time
    def __repr__(self):
        values=(self.name,self.openid,self.dingId,self.grade,self.token,self.update_time)
        return '%s,%s,%s,%s,%s,%s' % values

class project_list(DB.Model):
    __tablename__ = 'project_list'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    resource = DB.Column(DB.String(30))
    project = DB.Column(DB.String(30),index=True)
    domain = DB.Column(DB.String(30))
    ip = DB.Column(DB.String(30),index=True)
    ssh_port = DB.Column(DB.Integer)
    app_port = DB.Column(DB.String(30))
    business_id = DB.Column(DB.Integer)
    sys_args = DB.Column(DB.String(30))
    env = DB.Column(DB.String(8))
    gray =  DB.Column(DB.String(8))
    status = DB.Column(DB.String(8))
    update_date = DB.Column(DB.String(45))
    def __init__(self,resource,project,domain,ip,ssh_port,app_port,business_id,sys_args,env,gray,status,update_date):
        self.resource = resource
        self.project = project
        self.domain = domain
        self.ip = ip
        self.ssh_port = ssh_port
        self.app_port = app_port
        self.business_id = business_id
        self.sys_args = sys_args
        self.env = env
        self.gray = gray
        self.status = status
        self.update_date = update_date
    def __repr__(self):
        values=(self.resource,self.project,self.domain,self.ip,self.ssh_port,self.app_port,self.business_id,self.sys_args,self.env,self.gray,self.status,self.update_date)
        return '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s' % values

class publish_records(DB.Model):
    __tablename__ = 'publish_records'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    date = DB.Column(DB.String(20))
    time = DB.Column(DB.String(20))
    user = DB.Column(DB.String(20))
    project = DB.Column(DB.String(50))
    version = DB.Column(DB.String(50))
    package_url = DB.Column(DB.String(500))
    describe = DB.Column(DB.String(500))
    package_md5 = DB.Column(DB.String(500))
    package_type = DB.Column(DB.String(20))
    publish_type = DB.Column(DB.String(20))
    restart = DB.Column(DB.String(20))
    check_url = DB.Column(DB.String(500))
    callback_url = DB.Column(DB.String(500))
    token = DB.Column(DB.String(500))
    execute = DB.Column(DB.String(20))
    gray = DB.Column(DB.Integer)
    channel = DB.Column(DB.String(20))
    result = DB.Column(DB.String(20))
    flow_number = DB.Column(DB.String(45))
    def __init__(self,date,time,user,project,version,package_url,describe,package_md5,package_type,
                 publish_type,restart,check_url,callback_url,token,execute,gray,channel,result,flow_number):
        self.date = date
        self.time = time
        self.user = user
        self.project = project
        self.version = version
        self.package_url = package_url
        self.describe = describe
        self.package_md5 = package_md5
        self.package_type = package_type
        self.publish_type = publish_type
        self.restart = restart
        self.check_url = check_url
        self.callback_url = callback_url
        self.token = token
        self.execute = execute
        self.gray = gray
        self.channel = channel
        self.result = result
        self.flow_number = flow_number
    def __repr__(self):
        values=(self.date,self.time,self.user,self.project,self.version,self.package_url,self.describe,self.package_md5,
                self.package_type,self.publish_type,self.restart,self.check_url,self.callback_url,self.token,
                self.execute,self.gray,self.channel,self.result,self.flow_number)
        return '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%i,%s,%s,%s'%values

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

class dns_innr(DB.Model):
    __tablename__ = 'dns_innr'
    __bind_key__ = 'op'
    id = DB.Column(DB.Integer, primary_key=True, autoincrement=True)
    domain = DB.Column(DB.String(30))
    field = DB.Column(DB.String(50))
    Type = DB.Column(DB.String(30))
    ip = DB.Column(DB.String(100))
    stats = DB.Column(DB.String(8))
    system = DB.Column(DB.String(8))
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
    sub_id = DB.Column(DB.Integer)
    Menu_name = DB.Column(DB.String(10))
    id_name = DB.Column(DB.String(20))
    module_name = DB.Column(DB.String(50))
    action_name = DB.Column(DB.String(50))
    grade = DB.Column(DB.Integer)
    def __init__(self,Menu,Menu_id,sub_id,Menu_name,id_name,module_name,action_name,grade):
        self.Menu = Menu
        self.Menu_id = Menu_id
        self.sub_id = sub_id
        self.Menu_name = Menu_name
        self.id_name = id_name
        self.module_name = module_name
        self.action_name = action_name
        self.grade = grade

    def __repr__(self):
        values = (self.Menu,self.Menu_id,self.sub_id,self.Menu_name,self.id_name,self.module_name,self.action_name,self.grade)
        return '%s,%s,%s,%s,%s,%s,%s,%s' % values

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

class user_approval(DB.Model):
    __tablename__ = 'user_approval'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    name = DB.Column(DB.String(20))
    openid = DB.Column(DB.String(50))
    dingId = DB.Column(DB.String(50))
    apply_time = DB.Column(DB.String(20))
    approval_time = DB.Column(DB.String(20))
    approval_person = DB.Column(DB.String(20))
    apply_grade = DB.Column(DB.Integer)
    status = DB.Column(DB.String(20))
    def __init__(self,name,openid,dingId,apply_time,approval_time,approval_person,apply_grade,status):
        self.name =  name
        self.openid = openid
        self.dingId = dingId
        self.apply_time = apply_time
        self.approval_time = approval_time
        self.approval_person = approval_person
        self.apply_grade = apply_grade
        self.status = status
    def __repr__(self):
        values=(self.name,self.openid,self.dingId,self.apply_time,self.approval_time,self.approval_person,self.apply_grade,self.status)
        return '%s,%s,%s,%s,%s,%s,%s,%s' % values

class permission(DB.Model):
    __tablename__ = 'permission'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    auth = DB.Column(DB.String(20))
    authid = DB.Column(DB.Integer)
    def __init__(self,auth,authid):
        self.auth = auth
        self.authid = authid
    def __repr__(self):
        values=(self.auth,self.authid)
        return '%s,%s' % values

class business(DB.Model):
    __tablename__ = 'business'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    business = DB.Column(DB.String(50))
    describe = DB.Column(DB.String(50))
    person = DB.Column(DB.String(30))
    contact = DB.Column(DB.String(30))
    def __init__(self,business,describe,person,contact):
        self.business = business
        self.describe = describe
        self.person = person
        self.contact = contact
    def __repr__(self):
        values=(self.business,self.describe,self.person,self.contact)
        return '%s,%s,%s,%s' % values

class project_third(DB.Model):
    __tablename__ = 'project_third'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    project = DB.Column(DB.String(30))
    project_id = DB.Column(DB.Integer)
    third_id = DB.Column(DB.Integer)
    def __init__(self,project,project_id,third_id):
        self.project = project
        self.project_id = project_id
        self.third_id = third_id
    def __repr__(self):
        values=(self.project,self.project_id,self.third_id)
        return '%s,%s,%s'%values

class business_monitor(DB.Model):
    __tablename__ = 'business_monitor'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    url = DB.Column(DB.String(50))
    method = DB.Column(DB.String(8))
    project = DB.Column(DB.String(50))
    version = DB.Column(DB.String(20))
    code = DB.Column(DB.Integer)
    error_ip = DB.Column(DB.String(50))
    update_time = DB.Column(DB.String(20))
    alarm_time = DB.Column(DB.String(20))
    lock = DB.Column(DB.Integer)
    alart_token = DB.Column(DB.String(500))
    def __init__(self,url,method,project,version,code,error_ip,update_time,alarm_time,lock,alart_token):
        self.url = url
        self.method = method
        self.project = project
        self.version = version
        self.code = code
        self.error_ip = error_ip
        self.update_time = update_time
        self.alarm_time = alarm_time
        self.lock = lock
        self.alart_token = alart_token
    def __repr__(self):
        values=(self.url,self.method,self.project,self.version,self.code,self.error_ip,self.update_time,self.alarm_time,self.lock,self.alart_token)
        return '%s,%s,%s,%s,%i,%s,%s,%s,%i,%s'%values

class platform_token(DB.Model):
    __tablename__ = 'platform_token'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    platform = DB.Column(DB.String(50))
    channel = DB.Column(DB.String(30))
    token = DB.Column(DB.String(100))
    award = DB.Column(DB.String(30))
    expire = DB.Column(DB.String(30))
    def __init__(self,platform,channel,token,award,expire):
        self.platform = platform
        self.channel = channel
        self.token = token
        self.award = award
        self.expire = expire
    def __repr__(self):
        values=(self.platform,self.channel,self.token,self.award,self.expire)
        return '%s,%s,%s,%s,%s'%values

class publish_log(DB.Model):
    __tablename__ = 'publish_log'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    fid = DB.Column(DB.Integer)
    record = DB.Column(DB.TEXT)
    def __init__(self,fid,record):
        self.fid = fid
        self.record = record
    def __repr__(self):
        values=(self.fid,self.record)
        return '%s,%s'%values

class project_other(DB.Model):
    __tablename__ = 'project_other'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    lable = DB.Column(DB.String(45))
    project = DB.Column(DB.String(100))
    server_id = DB.Column(DB.Integer)
    business_id = DB.Column(DB.Integer)
    update_date = DB.Column(DB.String(45))
    def __init__(self,lable,project,server_id,business_id,update_time):
        self.lable = lable
        self.project = project
        self.server_id = server_id
        self.business_id = business_id
        self.update_date = update_time
    def __repr__(self):
        values=(self.labe,self.project,self.server_id,self.business_id,self.update_date)
        return '%s,%s,%i,%i,%s'%values

class k8s_deploy(DB.Model):
    __tablename__ = 'k8s_deploy'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    project = DB.Column(DB.String(50))
    deployment = DB.Column(DB.String(45))
    image = DB.Column(DB.String(100))
    war = DB.Column(DB.String(45))
    container_port = DB.Column(DB.String(45))
    replicas = DB.Column(DB.Integer)
    re_requests = DB.Column(DB.String(45))
    re_limits = DB.Column(DB.String(45))
    action = DB.Column(DB.String(45))
    update_date = DB.Column(DB.String(45))
    update_time = DB.Column(DB.String(45))
    def __init__(self,project,deployment,image,war,container_port,replicas,re_requests,re_limits,
                 action,update_date,update_time):
        self.project = project
        self.deployment = deployment
        self.image = image
        self.war = war
        self.container_port = container_port
        self.replicas = replicas
        self.re_requests = re_requests
        self.re_limits = re_limits
        self.action = action
        self.update_date = update_date
        self.update_time = update_time
    def __repr__(self):
        values=(self.project,self.deployment,self.image,self.war,self.container_port,self.replicas,self.re_requests,self.re_limits,
                self.action,self.update_date,self.update_time)
        return '%s,%s,%s,%s,%i,%i,%s,%s,%s,%s,%s'%values
class k8s_ingress(DB.Model):
    __tablename__ = 'k8s_ingress'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    name = DB.Column(DB.String(50),default='nginx-ingress')
    namespace = DB.Column(DB.String(45),default='default')
    domain = DB.Column(DB.String(100))
    serviceName = DB.Column(DB.String(100))
    servicePort = DB.Column(DB.Integer)
    def __init__(self,name,namespace,domain,serviceName,servicePort):
        self.name = name
        self.namespace = namespace
        self.domain = domain
        self.serviceName = serviceName
        self.servicePort = servicePort
    def __repr__(self):
        values=(self.name,self.namespace,self.domain,self.serviceName,self.servicePort)
        return '%s,%s,%s,%s,%i'%values
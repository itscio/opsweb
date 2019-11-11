#-*- coding: utf-8 -*-
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
app = Flask(__name__)
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/sql.conf')
class project_list(DB.Model):
    __tablename__ = 'project_list'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    resource = DB.Column(DB.String(30))
    project = DB.Column(DB.String(30),index=True)
    domain = DB.Column(DB.String(200))
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
    package_url = DB.Column(DB.String(200))
    describe = DB.Column(DB.String(500))
    package_md5 = DB.Column(DB.String(200))
    package_type = DB.Column(DB.String(20))
    publish_type = DB.Column(DB.String(20))
    restart = DB.Column(DB.String(20))
    check_url = DB.Column(DB.String(200))
    callback_url = DB.Column(DB.String(200))
    token = DB.Column(DB.String(200))
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

class op_menu(DB.Model):
    __tablename__ = 'op_menu'
    __bind_key__ = 'op'
    id = DB.Column(DB.Integer, primary_key=True, autoincrement=True)
    Menu_id = DB.Column(DB.Integer)
    sub_id = DB.Column(DB.Integer)
    Menu_name = DB.Column(DB.String(10))
    module_name = DB.Column(DB.String(50))
    action_name = DB.Column(DB.String(50))
    grade = DB.Column(DB.Integer)
    def __init__(self,Menu_id,sub_id,Menu_name,module_name,action_name,grade):
        self.Menu_id = Menu_id
        self.sub_id = sub_id
        self.Menu_name = Menu_name
        self.module_name = module_name
        self.action_name = action_name
        self.grade = grade

    def __repr__(self):
        values = (self.Menu_id,self.sub_id,self.Menu_name,self.module_name,self.action_name,self.grade)
        return '%s,%s,%s,%s,%s,%s' % values

class user_approval(DB.Model):
    __tablename__ = 'user_approval'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    dingId = DB.Column(DB.String(100))
    apply_time = DB.Column(DB.String(20))
    approval_time = DB.Column(DB.String(20))
    approval_person = DB.Column(DB.String(20))
    apply_grade = DB.Column(DB.Integer)
    status = DB.Column(DB.String(20))
    def __init__(self,dingId,apply_time,approval_time,approval_person,apply_grade,status):
        self.dingId = dingId
        self.apply_time = apply_time
        self.approval_time = approval_time
        self.approval_person = approval_person
        self.apply_grade = apply_grade
        self.status = status
    def __repr__(self):
        values=(self.dingId,self.apply_time,self.approval_time,self.approval_person,self.apply_grade,self.status)
        return '%s,%s,%s,%s,%s,%s' % values

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
    context = DB.Column(DB.String(45))
    deployment = DB.Column(DB.String(45))
    image = DB.Column(DB.String(100))
    war = DB.Column(DB.String(45))
    container_port = DB.Column(DB.String(45))
    replicas = DB.Column(DB.Integer)
    re_requests = DB.Column(DB.String(45))
    re_limits = DB.Column(DB.String(45))
    healthcheck = DB.Column(DB.String(100))
    action = DB.Column(DB.String(45))
    update_date = DB.Column(DB.String(45))
    update_time = DB.Column(DB.String(45))
    user = DB.Column(DB.String(45))
    def __init__(self,project,context,deployment,image,war,container_port,replicas,re_requests,re_limits,
                 healthcheck,action,update_date,update_time,user):
        self.project = project
        self.context = context
        self.deployment = deployment
        self.image = image
        self.war = war
        self.container_port = container_port
        self.replicas = replicas
        self.re_requests = re_requests
        self.re_limits = re_limits
        self.action = action
        self.healthcheck = healthcheck
        self.update_date = update_date
        self.update_time = update_time
        self.user = user
    def __repr__(self):
        values=(self.project,self.context,self.deployment,self.image,self.war,self.container_port,self.replicas,self.re_requests,self.re_limits,
                self.healthcheck,self.action,self.update_date,self.update_time,self.user)
        return '%s,%s,%s,%s,%s,%i,%i,%s,%s,%s,%s,%s,%s,%s'%values

class docker_run(DB.Model):
    __tablename__ = 'docker_run'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    deployment = DB.Column(DB.String(45))
    context = DB.Column(DB.String(45))
    dockerfile = DB.Column(DB.Text)
    run_args = DB.Column(DB.Text)
    side_car = DB.Column(DB.String(1000))
    def __init__(self,deployment,context,dockerfile,run_args,side_car):
        self.deployment = deployment
        self.context = context
        self.dockerfile = dockerfile
        self.run_args = run_args
        self.side_car = side_car
    def __repr__(self):
        values=(self.deployment,self.context,self.dockerfile,self.run_args,self.side_car)
        return '%s,%s,%s,%s,%s'%values

class k8s_packages(DB.Model):
    __tablename__ = 'k8s_packages'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    deployment = DB.Column(DB.String(45))
    package = DB.Column(DB.String(100))
    def __init__(self,deployment,package):
        self.deployment = deployment
        self.package = package
    def __repr__(self):
        values=(self.deployment,self.package)
        return '%s,%s'%values

class k8s_ingress(DB.Model):
    __tablename__ = 'k8s_ingress'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    name = DB.Column(DB.String(50),default='nginx-ingress')
    context = DB.Column(DB.String(45),default='context')
    namespace = DB.Column(DB.String(45),default='default')
    domain = DB.Column(DB.String(100))
    path = DB.Column(DB.String(100))
    serviceName = DB.Column(DB.String(100))
    servicePort = DB.Column(DB.Integer)
    def __init__(self,name,context,namespace,domain,path,serviceName,servicePort):
        self.name = name
        self.context = context
        self.namespace = namespace
        self.domain = domain
        self.path = path
        self.serviceName = serviceName
        self.servicePort = servicePort
    def __repr__(self):
        values=(self.name,self.context,self.namespace,self.domain,self.path,self.serviceName,self.servicePort)
        return '%s,%s,%s,%s,%s,%s,%i'%values

class webssh_records(DB.Model):
    __tablename__ = 'webssh_records'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    date = DB.Column(DB.String(20))
    time = DB.Column(DB.String(20))
    msg_id = DB.Column(DB.String(100))
    user = DB.Column(DB.String(50))
    dst_ip = DB.Column(DB.String(20))
    sshport = DB.Column(DB.Integer)
    exec = DB.Column(DB.String(500))
    def __init__(self,date,time,msg_id,user,dst_ip,sshport,exec):
        self.date = date
        self.time = time
        self.msg_id = msg_id
        self.user = user
        self.dst_ip = dst_ip
        self.sshport = sshport
        self.exec = exec
    def __repr__(self):
        values=(self.date,self.time,self.msg_id,self.user,self.dst_ip,self.sshport,self.exec)
        return '%s,%s,%s,%s,%s,%i,%s'%values

class sql_execute(DB.Model):
    __tablename__ = 'sql_execute'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    date = DB.Column(DB.String(20))
    time = DB.Column(DB.String(20))
    dingid = DB.Column(DB.String(100))
    host = DB.Column(DB.String(50))
    port = DB.Column(DB.Integer)
    database = DB.Column(DB.String(100))
    sql_url = DB.Column(DB.String(200))
    sql_md5 = DB.Column(DB.String(200))
    describe = DB.Column(DB.String(500))
    work_number = DB.Column(DB.Integer)
    def __init__(self,date,time,dingid,host,port,database,sql_url,sql_md5,describe,work_number):
        self.date = date
        self.time = time
        self.dingid = dingid
        self.host = host
        self.port = port
        self.database = database
        self.sql_url = sql_url
        self.sql_md5 = sql_md5
        self.describe = describe
        self.work_number = work_number
    def __repr__(self):
        values=(self.date,self.time,self.dingid,self.host,self.port,self.database,self.sql_url,self.sql_md5,self.describe,self.work_number)
        return '%s,%s,%s,%s,%i,%s,%s,%s,%s,%i'%values

class user_sso(DB.Model):
    __tablename__ = 'user_sso'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    userName = DB.Column(DB.String(20))
    realName = DB.Column(DB.String(20))
    mail = DB.Column(DB.String(100))
    mobilePhone = DB.Column(DB.String(50))
    department = DB.Column(DB.String(50))
    dingunionid = DB.Column(DB.String(100))
    ticket = DB.Column(DB.String(100))
    grade = DB.Column(DB.String(50))
    update_time = DB.Column(DB.String(20))
    def __init__(self,userName,realName,mail,mobilePhone,department,dingunionid,ticket,grade,update_time):
        self.userName = userName
        self.realName = realName
        self.mail = mail
        self.mobilePhone= mobilePhone
        self.department = department
        self.dingunionid = dingunionid
        self.ticket = ticket
        self.grade = grade
        self.update_time = update_time
    def __repr__(self):
        values=(self.userName,self.realName,self.mail,self.mobilePhone,self.department,
                self.dingunionid,self.ticket,self.grade,self.update_time)
        return '%s,%s,%s,%s,%s,%s,%s,%s,%s'%values

class publish_application(DB.Model):
    __tablename__ = 'publish_application'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    date = DB.Column(DB.String(20))
    time = DB.Column(DB.String(20))
    dingid = DB.Column(DB.String(100))
    project = DB.Column(DB.String(100))
    version = DB.Column(DB.String(50))
    git_url = DB.Column(DB.String(100))
    describe = DB.Column(DB.String(500))
    comment = DB.Column(DB.String(500))
    test = DB.Column(DB.String(20))
    nottest = DB.Column(DB.String(20))
    product = DB.Column(DB.String(20))
    work_number = DB.Column(DB.Integer)
    def __init__(self,date,time,dingid,project,version,git_url,describe,comment,test,nottest,product,work_number):
        self.date = date
        self.time = time
        self.dingid = dingid
        self.project = project
        self.version = version
        self.git_url = git_url
        self.describe = describe
        self.comment = comment
        self.test = test
        self.nottest = nottest
        self.product = product
        self.work_number = work_number
    def __repr__(self):
        values=(self.date,self.time,self.dingid,self.project,self.version,self.git_url,
                self.describe,self.comment,self.test,self.nottest,self.product,self.work_number)
        return '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%i'%values

class work_order(DB.Model):
    __tablename__ = 'work_order'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    date = DB.Column(DB.String(20))
    work_number = DB.Column(DB.Integer)
    source = DB.Column(DB.String(50))
    applicant = DB.Column(DB.String(100))
    reviewer = DB.Column(DB.String(100))
    approval = DB.Column(DB.String(100))
    dingid = DB.Column(DB.String(100))
    status = DB.Column(DB.String(50))
    def __init__(self,date,work_number,source,applicant,reviewer,approval,dingid,status):
        self.date = date
        self.work_number = work_number
        self.source = source
        self.applicant = applicant
        self.reviewer = reviewer
        self.approval = approval
        self.dingid = dingid
        self.status = status
    def __repr__(self):
        values=(self.date,self.work_number,self.source,self.applicant,self.reviewer,self.approval,self.dingid,self.status)
        return '%s,%i,%s,%s,%s,%s,%s,%s'%values

class work_comment(DB.Model):
    __tablename__ = 'work_comment'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    date_time = DB.Column(DB.String(20))
    work_number = DB.Column(DB.Integer)
    dingid = DB.Column(DB.String(100))
    user = DB.Column(DB.String(45))
    comment = DB.Column(DB.String(500))
    def __init__(self,date_time,work_number,dingid,user,comment):
        self.date_time = date_time
        self.work_number = work_number
        self.dingid = dingid
        self.user = user
        self.comment = comment
    def __repr__(self):
        values=(self.date_time,self.work_number,self.dingid,self.user,self.comment)
        return '%s,%i,%s,%s,%s'%values

class server_auth(DB.Model):
    __tablename__ = 'server_auth'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    date = DB.Column(DB.String(20))
    time = DB.Column(DB.String(20))
    dingid = DB.Column(DB.String(100))
    leader = DB.Column(DB.String(50))
    servers = DB.Column(DB.String(500))
    auth_level = DB.Column(DB.String(50))
    purpose = DB.Column(DB.String(500))
    work_number = DB.Column(DB.Integer)
    def __init__(self,date,time,dingid,leader,servers,auth_level,purpose,work_number):
        self.date = date
        self.time = time
        self.dingid = dingid
        self.leader = leader
        self.servers = servers
        self.auth_level = auth_level
        self.purpose = purpose
        self.work_number = work_number
    def __repr__(self):
        values=(self.date,self.time,self.dingid,self.leader,self.servers,self.auth_level,self.purpose,self.work_number)
        return '%s,%s,%s,%s,%s,%s,%s,%i'%values

class project_offline(DB.Model):
    __tablename__ = 'project_offline'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    date = DB.Column(DB.String(20))
    time = DB.Column(DB.String(20))
    dingid = DB.Column(DB.String(100))
    project = DB.Column(DB.String(100))
    git_url = DB.Column(DB.String(100))
    describe = DB.Column(DB.String(500))
    comment = DB.Column(DB.String(500))
    work_number = DB.Column(DB.Integer)
    def __init__(self,date,time,dingid,project,git_url,describe,comment,work_number):
        self.date = date
        self.time = time
        self.dingid = dingid
        self.project = project
        self.git_url = git_url
        self.describe = describe
        self.comment = comment
        self.work_number = work_number
    def __repr__(self):
        values=(self.date,self.time,self.dingid,self.project,self.git_url,self.describe,self.comment,self.work_number)
        return '%s,%s,%s,%s,%s,%s,%s,%i'%values

class other_work(DB.Model):
    __tablename__ = 'other_work'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    date = DB.Column(DB.String(20))
    time = DB.Column(DB.String(20))
    dingid = DB.Column(DB.String(100))
    title = DB.Column(DB.String(100))
    describe = DB.Column(DB.Text)
    md5 = DB.Column(DB.String(50))
    work_number = DB.Column(DB.Integer)
    def __init__(self,date,time,dingid,title,describe,md5,work_number):
        self.date = date
        self.time = time
        self.dingid = dingid
        self.title = title
        self.describe = describe
        self.md5 = md5
        self.work_number = work_number
    def __repr__(self):
        values=(self.date,self.time,self.dingid,self.title,self.describe,self.md5,self.work_number)
        return '%s,%s,%s,%s,%s,%s,%i'%values

class k8s_events(DB.Model):
    __tablename__ = 'k8s_events'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    context = DB.Column(DB.String(100))
    date_time = DB.Column(DB.String(100))
    kind = DB.Column(DB.String(100))
    name = DB.Column(DB.String(100))
    namespace = DB.Column(DB.String(100))
    message = DB.Column(DB.String(500))
    reason = DB.Column(DB.String(500))
    type = DB.Column(DB.String(100))
    def __init__(self,context,date_time,kind,name,namespace,message,reason,type):
        self.context = context
        self.date_time = date_time
        self.kind = kind
        self.name = name
        self.namespace = namespace
        self.message = message
        self.reason = reason
        self.type = type
    def __repr__(self):
        values=(self.context,self.date_time,self.kind,self.name,self.namespace,self.message,self.reason,self.type)
        return '%s,%s,%s,%s,%s,%s,%s,%s'%values

class docker_hosts(DB.Model):
    __tablename__ = 'docker_hosts'
    __bind_key__='op'
    id = DB.Column(DB.Integer, primary_key=True,autoincrement=True)
    deployment = DB.Column(DB.String(100))
    context = DB.Column(DB.String(100))
    ip = DB.Column(DB.String(45))
    hostname = DB.Column(DB.String(100))
    def __init__(self,deployment,context,ip,hostname):
        self.deployment = deployment
        self.context = context
        self.ip = ip
        self.hostname = hostname
    def __repr__(self):
        values=(self.deployment,self.context,self.ip,self.hostname)
        return '%s,%s,%s,%s'%values
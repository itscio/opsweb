#-*- coding: utf-8 -*-
from flask_wtf import Form
from wtforms import StringField,BooleanField, PasswordField,TextAreaField,SelectField,SelectMultipleField,SubmitField,FileField ,IntegerField
from wtforms.validators import DataRequired,Length
import time
import db_op,Mysql
from sqlalchemy import distinct
from rediscluster import RedisCluster
import __init__
app = __init__.app
nodes = app.config.get('NODES')
rc = RedisCluster(startup_nodes=nodes,decode_responses=True)
class myform(Form):
    text = TextAreaField(validators=[DataRequired()])
    input = StringField('Input', validators=[DataRequired()])
    submit_redis = SubmitField('清除日志')
    submit = SubmitField('提交',id='btn1')

class Myform_op_user(Form):
    text = TextAreaField(validators=[DataRequired()])
    select = SelectField(choices=[('query', '查询'), ('add', '开通'),('del', '删除'),('unlock', '解锁'),('init', '初始化')])
    submit = SubmitField('提交',id='btn1')

class MyForm_input(Form):
    text = TextAreaField(validators=[DataRequired()])
    text2 = TextAreaField(validators=[DataRequired()])
    input = StringField('Input', validators=[DataRequired()])
    submit = SubmitField('提交',id='btn1')

class MyForm_login(Form):
    name = StringField('Name', validators=[DataRequired(),Length(4,16)])
    password = PasswordField('Password', validators=[DataRequired(),Length(4,16)])
    code = StringField('code', validators=[DataRequired()])
    remember_me =BooleanField('Remember_me',default = True)
    submit = SubmitField('登陆',id='btn1')

class MyForm_pw(Form):
    password = PasswordField('Password', validators=[DataRequired(),Length(4,16)])
    new_password1 = PasswordField('New_password1', validators=[DataRequired(),Length(4,16)])
    new_password2 = PasswordField('New_password2', validators=[DataRequired(),Length(4,16)])
    submit = SubmitField('提交',id='btn1')

class MyForm_app(Form):
    select = SelectField(choices=[('ip', 'ip地址'), ('app', '项目部署名称'), ('domain', '域名')])
    text = TextAreaField(validators=[DataRequired()])
    submit = SubmitField('提交',id='btn1')

class MyForm_server(Form):
    select = SelectField(choices=[('ip', 'ip地址'), ('cid', '机柜号'), ('sn', 'sn号'),('deparment', '部门'),('status', '使用状态')])
    text = TextAreaField(validators=[DataRequired()])
    submit = SubmitField('提交',id='btn1')

class MyForm_php(Form):
    code = IntegerField('code', validators=[DataRequired()])
    text = TextAreaField(validators=[DataRequired()])
    changelog = TextAreaField(validators=[DataRequired()])
    selectaction = SelectField(choices=[('publish', '上线'), ('recover', '回滚')])
    selecttype = SelectField(choices=[('2', '测外'),('1', '线上')])
    selectWay = SelectField(choices=[('SVN', 'SVN'), ('GIT', 'GIT')])
    selectwork = SelectField(choices=[('BUG', 'Bug修复'), ('NEW', '新增需求')])
    selectgrade = SelectField(choices=[('7', '7'), ('6', '6'), ('5', '5'), ('4', '4'), ('3', '3'), ('2', '2'), ('1', '1')])
    Gray = BooleanField('Gray', default=False)
    submit = SubmitField('提交',id='btn1')
    
class MyForm_publishJboss(Form):
    code = IntegerField('code', validators=[DataRequired()])
    text = TextAreaField(validators=[DataRequired()])
    changelog = TextAreaField(validators=[DataRequired()])
    selectAction = SelectField(choices=[('publish', '上线'),('rollback','回滚'),('restart', '重启')])
    selectType = SelectField(choices=[('2', '测外'),('1', '线上')])
    selectWay = SelectField(choices=[('SVN', 'SVN'), ('GIT', 'GIT')])
    selectwork = SelectField(choices=[('BUG', 'Bug修复'), ('NEW', '新增需求')])
    selectgrade = SelectField(choices=[('7', '7'), ('6', '6'), ('5', '5'), ('4', '4'), ('3', '3'), ('2', '2'), ('1', '1')])
    Gray = BooleanField('Gray',default = False)
    submit = SubmitField('提交',id='btn1',)

class MyForm_updateJboss(Form):
    text = TextAreaField(validators=[DataRequired()])
    selectAction = SelectField(choices=[('update', '上线'),('rollback','回滚')])
    Gray = BooleanField('Gray',default = False)
    submit = SubmitField('提交',id='btn1')

class MyFrom_php_list(Form):
    val = Mysql.db_list('php')
    php_project = [va[0].strip().strip('\t') for va in val]
    Project = SelectField(choices=[(str(project),str(project)) for project in php_project])
    text = TextAreaField(validators=[DataRequired()])
    select = SelectField(choices=[('2', '测外'),('1', '线上')])
    submit_query = SubmitField('查询')
    submit_modify = SubmitField('提交',id='btn1')

class MyFrom_java_list(Form):
    val = Mysql.db_list('java')
    java_project = [va[0].strip().strip('\t') for va in val]
    Project = SelectField(choices=[(str(project),str(project)) for project in java_project])
    text = TextAreaField(validators=[DataRequired()])
    select = SelectField(choices=[('2', '测外'),('1', '线上')])
    submit_query = SubmitField('查询')
    submit_modify = SubmitField('提交',id='btn1')

class MyForm_clear_redis(Form):
    text = TextAreaField(validators=[DataRequired()])
    select_port = SelectField(choices=[('select', '- Select -'),('6380','6380'),('6800','6800'),('6801','6801'),('6802','6802'),('6901','6901'),('6903','6903'),('6905','6905'),('6907','6907'),('6909','6909'),('6911','6911')])
    select_action = SelectField(choices=[('query','查询'),('clear','清除')])
    submit = SubmitField('提交',id='btn1')

class MyForm_vpn(Form):
    text = TextAreaField(validators=[DataRequired()])
    select_action = SelectField(choices=[('query','查询'),('add','开通'),('del','关闭')])
    submit = SubmitField('提交',id='btn1')

class MyForm_svn_admin(Form):
    text = TextAreaField(validators=[DataRequired()])
    select_action = SelectField(choices=[('query','查询'),('add','开通'),('del','关闭'),('lock','锁定'),('unlock','解锁'),('add_group','增加用户组'),('del_group','减少用户组')])
    db = db_op.svn_permission
    try:
        val = db.query.with_entities(distinct(db.groups)).all()
    finally:
        db_op.DB.session.remove()
    svn_groups = [va[0].strip().strip('\t') for va in val]
    select_groups = SelectMultipleField(choices=[(str(Group),str(Group)) for Group in svn_groups if str(Group) != '*'],default=None)
    submit = SubmitField('提交',id='btn1')

class MyForm_sql_scheduler(Form):
    sql_text = TextAreaField(validators=[DataRequired()])
    db_name = StringField('db_name', validators=[DataRequired(),Length(1,50)])
    submit = SubmitField('提交',id='btn1')

class MyForm_git_admin(Form):
    text = TextAreaField(validators=[DataRequired()])
    select_action = SelectField(choices=[('query','查询'),('add','开通'),('del','关闭')])
    submit = SubmitField('提交',id='btn1')

class MyForm_sql_kill(Form):
    ip = StringField('ip', validators=[DataRequired()])
    port = StringField('port', validators=[DataRequired()])
    select_action = SelectField(choices=[('Select', '- Select -'),('Sleep', 'Sleep'), ('Lock', 'Lock'),('Query','Query')])
    submit = SubmitField('提交',id='btn1')

class MyForm_sql_run(Form):
    sql_text = TextAreaField(validators=[DataRequired()])
    db_name = TextAreaField(validators=[DataRequired()])
    File = FileField('File')
    submit = SubmitField('提交',id='btn1')

class MyForm_deploy_jboss(Form):
    haproxy = BooleanField(label='外部HAPROXY')
    haproxy_intranet = BooleanField(label='内部HAPROXY')
    input_domain = StringField(validators=[DataRequired(), Length(4, 64)])
    input_produce = StringField()
    val_produce, val_test = Mysql.db_produce('java')
    select_produce = SelectField(choices = [('{0}:{1}'.format(va[1],va[0]),'{0}:{1}'.format(va[1],va[0])) for va in val_produce])
    select_test = SelectField(choices = [('{0}:{1}'.format(va[1],va[0]),'{0}:{1}'.format(va[1],va[0])) for va in val_test])
    input_test = StringField()
    submit_produce = SubmitField('提交',id='btn1')
    submit_test = SubmitField('提交',id='btn2')

class MyForm_deploy_php(Form):
    val_produce, val_test = Mysql.db_produce('php')
    select_produce = SelectField(choices = [('{0}:{1}'.format(va[1],va[0]),'{0}:{1}'.format(va[1],va[0])) for va in val_produce])
    select_test = SelectField(choices = [('{0}:{1}'.format(va[1],va[0]),'{0}:{1}'.format(va[1],va[0])) for va in val_test])
    ver_produce = SelectField(choices=[('5.4','5.4'), ('5.6','5.6')])
    ver_test = SelectField(choices=[('5.4','5.4'), ('5.6','5.6')])
    submit_produce= SubmitField('提交',id='btn1')
    submit_test = SubmitField('提交',id='btn2')

class MyForm_deploy_nginx(Form):
    haproxy = BooleanField(label='外部HAPROXY')
    haproxy_intranet = BooleanField(label='内部HAPROXY')
    input_domain = StringField(validators=[DataRequired(),Length(4, 64)])
    input_root = StringField(validators=[DataRequired(),Length(4, 64)])
    ip = TextAreaField(validators=[DataRequired()])
    select = SelectField(choices=[('2', '测外'),('1', '线上')])
    submit = SubmitField('提交',id='btn1')

class MyForm_chart_center(Form):
    select_internet = SelectField(choices = [(str(domain),str(domain)) for domain in rc.smembers('haproxy_topic')])
    select_intranet = SelectField(choices = [(str(domain),str(domain)) for domain in rc.smembers('haproxy2_topic')])
    submit = SubmitField('生成',id='btn1')

class MyForm_dns_conf(Form):
    select_domain = SelectField(choices=[('baihe.com','baihe.com'),('ibaihe.com','ibaihe.com'),('service.baihe','service.baihe')])
    select_type = SelectField(choices=[('A','A'),('CNAME','CNAME'),('MX','MX'),('TEXT','TEXT'),('NS','NS')])
    select_action = SelectField(choices=[ ('query', '查询'),('add', '新增'), ('modify', '修改'), ('del', '删除')])
    select_sys = SelectField(choices=[('cw', '测外'), ('xs', '线上')])
    field = StringField('field', validators=[DataRequired(), Length(1,64)])
    ip = StringField('ip', validators=[DataRequired(), Length(1, 64)])
    submit = SubmitField('提交',id='btn1')

class MyForm_Scheduler(Form):
    job = TextAreaField(validators=[DataRequired()])
    cron = StringField('cron', validators=[DataRequired(),Length(1,50)])
    host = StringField('host', validators=[DataRequired(),Length(1,50)])
    user = SelectField(choices=[ ('work', 'work'),('java', 'java'), ('java2', 'java2'), ('java3', 'java3'), ('java4', 'java4')])
    submit = SubmitField('提交',id='btn1')
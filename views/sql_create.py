#-*- coding: utf-8 -*-
from flask import Blueprint,render_template,g,flash,request
from Modules import produce,check,MyForm,db_op,db_idc,Mysql,loging,main_info
from sqlalchemy import and_
import time
import __init__
app = __init__.app
page_sql_create=Blueprint('sql_create',__name__)
@page_sql_create.route('/sql_create',methods = ['GET', 'POST'])
@main_info.main_info
def sql_create():
    form = MyForm.MyForm_sql_create()
    if form.submit.data:
        try:
            tt = time.strftime('%Y%m',time.localtime())
            db_name = form.db_name.data.strip()
            assert db_name, '数据库库名不能为空!'
            sql_master = form.sql_master.data.strip()
            assert sql_master,'主库服务器地址不能为空'
            db_mysql = db_idc.idc_mysqldb
            master_port = db_mysql.query.with_entities(db_mysql.port).filter(and_(db_mysql.master == '是', db_mysql.ip == sql_master)).all()
            assert master_port, '没有找到主库端口信息!'
            sql_slave = db_mysql.query.with_entities(db_mysql.ip, db_mysql.port).filter(and_(db_mysql.slave == '是', db_mysql.Master_Host == sql_master)).all()
            assert sql_slave,'没有找到相关从库信息!'
            #创建数据库
            master_port = master_port[0][0]
            MYSQL = Mysql.MYSQL(host=sql_master,port=master_port)
            MYSQL.Run("UPDATE `mysql`.`user` SET `Grant_priv` = 'Y' WHERE `Grant_priv` = 'N' AND `User` = 'mysql_op';")
            MYSQL.Run("FLUSH PRIVILEGES;")
            Error_info =  MYSQL.Run('create database %s;' %db_name)
            if Error_info:
                raise flash(Error_info)
            else:
                flash('%s数据库已创建!' % db_name)
            Error_info =MYSQL.Run("GRANT SELECT,DELETE,UPDATE,INSERT ON {0}.* TO '{0}'@'172.16.%' IDENTIFIED BY '{0}@baihe_{1}';".format(db_name,tt))
            MYSQL.Run("FLUSH PRIVILEGES;")
            if Error_info:
                raise flash(Error_info)
            else:
                flash('%s数据库权限已开通!' % db_name)
            MYSQL.Close()
            #写入dns配置库
            db = db_op.dns_innr
            #master
            c = db(domain='sql.baihe', field='%s.master'%db_name.replace('_', '-'), Type='A', ip=sql_master, stats='1', system='xs')
            db_op.DB.session.add(c)
            db_op.DB.session.commit()
            flash('主库DNS解析完毕!')
            #slave
            flash('*'*50)
            flash('用户名:%s' %db_name)
            flash('密码:%s@baihe_%s' % (db_name, tt))
            flash('主库地址:%s   端口:%s' %('%s.master.sql.baihe'%db_name.replace('_', '-'),master_port))
            for slave_ip,slave_port in sql_slave:
                c = db(domain='sql.baihe', field='%s.slave%s' %(db_name.replace('_', '-'),slave_ip.split('.')[-1]), Type='A', ip=slave_ip, stats='1',system='xs')
                db_op.DB.session.add(c)
                db_op.DB.session.commit()
                flash('从库地址:%s   端口:%s' % ('%s.slave%s.sql.baihe'%(db_name.replace('_', '-'),slave_ip.split('.')[-1]),slave_port))
            flash('*' * 50)
            flash('从库DNS解析完毕!')
        except Exception as e:
            if 'old-style'not in str(e):
                flash(e)
    return render_template('mysql_create.html',Main_Infos=g.main_infos,form=form)

@page_sql_create.before_request
@check.login_required(grade=0)
def check_login(error=None):
    produce.Async_log(g.user, request.url)

@page_sql_create.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
    db_idc.DB.session.remove()
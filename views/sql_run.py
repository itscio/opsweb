#-*- coding: utf-8 -*-
from flask import Blueprint,render_template,g,flash,request
from Modules import produce,check,MyForm,db_op,db_idc,Mysql
from sqlalchemy import and_
import os
import chardet
import __init__
app = __init__.app
UPLOAD_FOLDER = '/tmp/'
page_sql_run=Blueprint('sql_run',__name__)
@page_sql_run.route('/sql_run',methods = ['GET', 'POST'])
def sql_run():
    form = MyForm.MyForm_sql_run()
    if form.submit.data:
        #获取页面相关信息
        try:
            db_name = form.db_name.data.strip()
            assert db_name,'数据库库名不能为空!'
            if form.File.data:
                File = request.files['File']
                if File:
                    if File.filename.endswith('.sql') or File.filename.endswith('.txt'):
                        File.save(os.path.join(UPLOAD_FOLDER,File.filename))
                        with open('{0}{1}'.format(UPLOAD_FOLDER,File.filename),'r') as f:
                            cmds = f.read().strip()
                            chart = chardet.detect(cmds)
                            if chart['encoding'].lower() not in ('ascii','utf-8'):
                                raise flash('sql文件当前编码是{0},不是utf-8或者ascii编码!'.format(chart['encoding']))
                    else:
                        raise flash('文件名应以.sql或者.txt结尾!')
            elif form.sql_text.data:
                cmds = form.sql_text.data.strip()
            else:
                raise flash('没有SQL语句可执行!')
            if cmds:
                if cmds.endswith(';'):
                    cmds = cmds.split(';')
                    if len(cmds) > 200:
                        raise flash('SQL语句不能超过200条!')
                    #获取库表对应的主库服务器信息
                    db = db_idc.idc_mysqldb
                    db_table = db_idc.idc_tableinfo
                    for sql_cmd in cmds:
                        if sql_cmd:
                            sql_cmd = sql_cmd.strip()
                            sql_cmd = '%s;'%sql_cmd
                            if 'update' or 'insert' or 'delete'  or 'alter' or 'create' in sql_cmd.lower():
                                if sql_cmd.lower().startswith('update'):
                                    table_name = sql_cmd.split()[1]
                                else:
                                    table_name = sql_cmd.split()[2]
                                table_name = table_name.replace('`','')
                                val_ips = db.query.with_entities(db_table.ip).filter(and_(db_table.database_name == db_name,db_table.table_name == table_name)).all()
                                if sql_cmd.lower().startswith('create'):
                                    if val_ips:
                                        raise flash('{0}在{1}库已存在!'.format(table_name,db_name))
                                    else:
                                        val_ips = db.query.with_entities(db_table.ip).filter(and_(db_table.database_name == db_name)).all()
                                if val_ips:
                                    val_ips = set([ ip[0] for ip in val_ips ])
                                else:
                                    raise flash('没有找到%s表相关数据库信息!'%table_name)
                                val = db.query.with_entities(db.ip,db.port,db.db).filter(and_(db.master == '是',db.ip.in_(val_ips))).all()
                                if val:
                                    for info in val:
                                        #执行sql语句
                                        master_ip,master_port,master_db = info
                                        if db_name in master_db.split('|'):
                                            flash('服务器:{0}  端口:{1}  数据库:{2}'.format(master_ip, master_port,db_name))
                                            result = Mysql.Query_sql(master_ip,master_port,db_name,sql_cmd)
                                            if result:
                                                flash(result)
                                            else:
                                                flash('SQL语句:{0}'.format(sql_cmd))
                                                flash('SQL执行成功!')
                                else:
                                    raise flash('没有找到%s数据库的相关服务器信息!'%db_name)
                            else:
                                raise flash("%s 不符合执行规则!" %sql_cmd)
                else:
                    raise flash("每条sql语句需要以分号结尾!")
        except Exception as e:
            if 'old-style'not in str(e):
                flash(e)
        return render_template('Message_static.html')
    return render_template('mysql_run.html',form=form)

@page_sql_run.before_request
@check.login_required(grade=0)
def check_login(error=None):
    produce.Async_log(g.user, request.url)

@page_sql_run.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
    db_idc.DB.session.remove()
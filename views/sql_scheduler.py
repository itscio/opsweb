#-*- coding: utf-8 -*-
from flask import Blueprint,redirect,render_template,g,flash,url_for,request
from Modules import produce,check,MyForm,db_op,db_idc,loging
from sqlalchemy import and_,desc
import time
page_sql_scheduler=Blueprint('sql_scheduler',__name__)
@page_sql_scheduler.route('/sql_scheduler',methods = ['GET', 'POST'])
def sql_scheduler():
    form = MyForm.MyForm_sql_scheduler()
    #查询前20个计划任务
    tables = ('服务器','端口','库名','执行时间','执行命令','执行状态','执行结果')
    db = db_op.sql_scheduler
    val_scheduler = db.query.with_entities(db.master_ip,db.master_port,db.db,db.time,db.sql_cmd,db.status,db.results).order_by(desc(db.id)).limit(20).all() or None
    if form.submit.data:
        #获取页面相关信息
        if form.sql_text.data:
            db_name = form.db_name.data.strip()
            Year = time.strftime('%Y-%m-%d',time.localtime())
            cmds = form.sql_text.data.strip()
            if cmds:
                try:
                    if cmds.endswith(';'):
                        cmds = cmds.split(';')
                        #获取库表对应的主库服务器信息
                        db = db_idc.idc_mysqldb
                        db_table = db_idc.idc_tableinfo
                        for sql_cmd in cmds:
                            if sql_cmd:
                                sql_cmd = sql_cmd.strip()
                                sql_cmd = '%s;'%sql_cmd
                                if 'update' in sql_cmd.lower() or 'delete' in sql_cmd.lower() or 'alter' in sql_cmd.lower():
                                    if sql_cmd.lower().startswith('update'):
                                        table_name = sql_cmd.split()[1]
                                    else:
                                        table_name = sql_cmd.split()[2]
                                    table_name = table_name.replace('`','')
                                    val_ips = db.query.with_entities(db_table.ip).filter(and_(db_table.database_name == db_name,db_table.table_name == table_name)).all()
                                    if val_ips:
                                        val_ips = set([ ip[0] for ip in val_ips ])
                                    else:
                                        raise flash('没有找到%s表相关数据库信息!'%table_name)
                                    val = db.query.with_entities(db.ip,db.port,db.db).filter(and_(db.master == '是',db.ip.in_(val_ips))).all()
                                    if val:
                                        for info in val:
                                            #将sql计划任务相关信息写入数据库
                                            master_ip,master_port,master_db = info
                                            if db_name in master_db.split('|'):
                                                c = db_op.sql_scheduler(master_ip = master_ip,master_port = master_port,db = db_name,time = Year,sql_cmd=sql_cmd,status='未执行',results='None')
                                                db_op.DB.session.add(c)
                                                db_op.DB.session.commit()
                                    else:
                                        raise flash('没有找到%s数据库的相关服务器信息!'%db_name)
                                else:
                                    raise flash("%s 不符合执行规则!" %sql_cmd)
                    else:
                        raise flash("每条sql语句需要以分号结尾!")
                except Exception as e:
                    #loging.write(e)
                    return render_template('Message_static.html')
            return redirect(url_for("sql_scheduler.sql_scheduler"))
        try:
            produce.Scheduler_sql_run()
        except Exception as e:
            loging.write(e)
    return render_template('mysql_scheduler.html',form=form,val_scheduler=val_scheduler,tables=tables)

@page_sql_scheduler.before_request
@check.login_required(grade=0)
def check_login(error=None):
    produce.Async_log(g.user, request.url)

@page_sql_scheduler.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
    db_idc.DB.session.remove()
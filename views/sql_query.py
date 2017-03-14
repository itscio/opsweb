#-*- coding: utf-8 -*-
from flask import Blueprint,render_template,g,flash,request
from Modules import produce,check,MyForm,db_idc,Mysql,loging
from sqlalchemy import and_
import __init__
app = __init__.app
page_sql_query=Blueprint('sql_query',__name__)
@page_sql_query.route('/sql_query',methods = ['GET', 'POST'])
def sql_query():
    form = MyForm.MyForm_sql_run()
    if form.submit.data:
        #获取页面相关信息
        try:
            db_name = form.db_name.data.strip()
            assert db_name,'数据库库名不能为空!'
            if form.sql_text.data:
                cmds = form.sql_text.data.strip()
            else:
                raise flash('没有SQL语句可执行!')
            if cmds:
                if cmds.endswith(';'):
                    cmds = cmds.split(';')
                    if len(cmds) > 6:
                        raise flash('SQL语句查询一次不能大于5条!')
                    #获取库表对应的主库服务器信息
                    db = db_idc.idc_mysqldb
                    db_table = db_idc.idc_tableinfo
                    for sql_cmd in cmds:
                        if sql_cmd:
                            sql_cmd = sql_cmd.strip()
                            if 'limit' in  sql_cmd:
                                if int(sql_cmd.split()[-1]) >5:
                                    raise flash('SQL语句中limit 的值不能大于5')
                                sql_cmd = '%s;' % sql_cmd
                            else:
                                sql_cmd = '%s limit 5;'%sql_cmd
                            if sql_cmd.lower().startswith('select'):
                                table_name = sql_cmd.split('from')[1]
                                table_name = table_name.split()[0]
                                table_name = table_name.replace('`','')
                                val_ips = db.query.with_entities(db_table.ip).filter(and_(db_table.database_name == db_name,db_table.table_name == table_name)).all()
                                if val_ips:
                                    val_ips = set([ ip[0] for ip in val_ips ])
                                else:
                                    raise flash('没有找到%s表相关信息!'%table_name)
                                val = db.query.with_entities(db.ip,db.port,db.db).filter(and_(db.master == '是',db.ip.in_(val_ips))).all()
                                if val:
                                    for info in val:
                                        #执行sql语句
                                        master_ip,master_port,master_db = info
                                        if db_name in master_db.split('|'):
                                            flash('SQL语句:{0}'.format(sql_cmd))
                                            flash('查询结果:')
                                            results = Mysql.Query_sql(master_ip,master_port,db_name,sql_cmd)
                                            if results:
                                                for  result in results:
                                                    result = [str(re) for re in result]
                                                    flash('\t'.join(result))
                                                produce.Async_log(g.user,sql_cmd)
                                    flash('--'*40)
                                else:
                                    raise flash('没有找到%s数据库的相关服务器信息!'%db_name)
                            else:
                                raise flash("%s 不符合执行规则!" %sql_cmd)
                else:
                    raise flash("每条sql语句需要以分号结尾!")
        except Exception as e:
                loging.write(e)
        return render_template('Message_static.html')
    return render_template('mysql_query.html',form=form)
@page_sql_query.before_request
@check.login_required(grade=10)
def check_login(error=None):
    produce.Async_log(g.user, request.url)

@page_sql_query.teardown_request
def db_remove(error=None):
    db_idc.DB.session.remove()
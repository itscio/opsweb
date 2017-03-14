#-*- coding: utf-8 -*-
from flask import Blueprint,render_template,g,flash,request
from Modules import check,MyForm,db_idc,produce,Mysql,loging
from sqlalchemy import and_,distinct
import time
import __init__
app = __init__.app
user = app.config.get('MYSQL_USER')
password = app.config.get('MYSQL_PASSWORD')
page_mysql_parse=Blueprint('mysql_parse',__name__)
@page_mysql_parse.route('/mysql_parse',methods = ['GET', 'POST'])
def mysql_parse():
    form = MyForm.MyForm_input()
    db = db_idc.idc_mysqldb
    db_table = db_idc.idc_tableinfo
    if form.submit.data:
        if form.text.data and form.input.data:
            mysql_db = form.input.data.strip()
            try:
                if ';' in  form.text.data.strip():
                    sql_lines = form.text.data.strip().replace('\r\n',' ')
                    for Line in sql_lines.split(';'):
                        if '.' in Line:
                            raise flash('%s 语句中不能有库名!' %Line)
                        if Line:
                            Line = '%s ;'%Line.strip()
                            line = Line.lower()
                            if  'delete' in line:
                                table_name = Line.split('from')[1].split()[0]
                            elif 'update' in line:
                                table_name = Line.split()[1]
                            elif 'alter' in line:
                                table_name = Line.split()[2]
                            else:
                                flash(Line)
                                flash('------->该SQL语句不在审查范围内!')
                                continue
                            # 从sql语句中抽取表名
                            val = db_table.query.with_entities(db_table.ip, db_table.port, db_table.Engine_name, db_table.Rows).filter(and_(db_table.database_name == mysql_db, db_table.table_name == table_name.replace('`',''))).all()
                            if val:
                                mysql_ip, mysql_port, Engine_name, Rows = val[0]
                                flash('----' * 24)
                                flash('数据库IP:{0},数据库端口:{1},表引擎:{2},表行数:{3}'.format(mysql_ip,mysql_port,Engine_name,Rows))
                                flash('----' * 24)
                                MYSQL = Mysql.MYSQL(user,password,mysql_ip,mysql_port)
                                cmd = "explain %s" %Line
                                flash(Line)
                                result = MYSQL.Run(cmd)
                                if isinstance(result,list):
                                    flash('------->语法检查通过!')
                                else:
                                    raise flash('------->语法有错误! %s' %str(result))
                                MYSQL.Close()
                                if (int(Rows) >= 10000 and Engine_name == 'MyISAM') or (int(Rows) >= 50000 and Engine_name == 'InnoDB'):
                                    result = 'SQL语句建议进行定时执行!'
                                else:
                                    result = 'SQL语句可以直接执行!'
                                flash('----' * 24)
                                flash('审核结果:{0}'.format(result))
                                flash('----' * 24)
                            else:
                                raise flash('没有找到%s数据库的相关服务器信息!' % mysql_db)
                else:
                    flash('SQL语句没有以分号结尾!')
                    return render_template('Message.html')
            except Exception as e:
                if 'old-style' not in str(e):
                    flash(e)
            return render_template('Message_static.html')
        else:
            flash('输入框内容不能为空!')
            return render_template('Message.html')
    return render_template('mysql_parse.html',form=form)
@page_mysql_parse.before_request
@check.login_required(grade=10)
def check_login(error=None):
    produce.Async_log(g.user, request.url)
@page_mysql_parse.teardown_request
def db_remove(error=None):
    db_idc.DB.session.remove()
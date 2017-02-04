#-*- coding: utf-8 -*-
from flask import Blueprint,render_template,g,flash,request
from Modules import check,MyForm,db_idc,produce,Mysql
from sqlalchemy import and_
import __init__
app = __init__.app
user = app.config.get('MYSQL_USER')
password = app.config.get('MYSQL_PASSWORD')
page_mysql_parse=Blueprint('mysql_parse',__name__)
@page_mysql_parse.route('/mysql_parse',methods = ['GET', 'POST'])
def mysql_parse():
    form = MyForm.MyForm_input()
    db = db_idc.idc_tableinfo
    if form.submit.data:
        if form.text.data and form.input.data:
            mysql_db = form.input.data.strip()
            try:
                if ';' in  form.text.data.strip():
                    sql_lines = form.text.data.strip().replace('\r\n',' ').replace('`','')
                    for Line in sql_lines.split(';'):
                        if '.' in Line:
                            raise flash('%s 语句中不能有库名!' %Line)
                        table_name = None
                        Line = '%s;'%Line.strip()
                        line = Line.lower()
                        if 'select' in line or 'delete' in line:
                            table_name = Line.split()[0].split('from')[1]
                        elif 'update' in line:
                            table_name = Line.split()[1]
                        elif 'alter' in line:
                            table_name = Line.split()[2]
                        if not table_name:
                            flash(Line)
                            raise flash('------->该SQL语句不在审查范围内!')
                        # 从sql语句中抽取表名
                        val = db.query.with_entities(db.ip, db.port, db.Engine_name, db.Rows).filter(and_(db.database_name == mysql_db, db.table_name == table_name)).all()
                        if val:
                            mysql_ip, mysql_port, Engine_name, Rows = val[0]
                            MYSQL = Mysql.MYSQL(user,password,mysql_ip,mysql_port)
                            cmd = 'explain %s' %Line
                            flash(Line)
                            result = MYSQL.Run(cmd)
                            if isinstance(result,list):
                                flash('------->语法检查通过!')
                            else:
                                raise flash('------->语法有错误! %s' %str(result))
                            flash('----' * 24)
                            MYSQL.Close()
                            flash('数据库IP:{0},数据库端口:{1},表引擎:{2},表行数:{3}'.format(mysql_ip,mysql_port,Engine_name,Rows))
                            flash('----' * 24)
                            if (int(Rows) >= 10000 and Engine_name == 'MyISAM') or (
                                    int(Rows) >= 50000 and Engine_name == 'InnoDB'):
                                result = 'SQL语句建议进行定时执行!'
                            else:
                                result = 'SQL语句可以直接执行!'
                            flash('审核结果:{0}'.format(result))
                else:
                    flash('SQL语句没有以分号结尾!')
                    return render_template('Message.html')
            except Exception as e:
                if 'old-style' not in str(e):
                    flash(e)
            return render_template('Message_static.html')
    return render_template('mysql_parse.html',form=form)
@page_mysql_parse.before_request
@check.login_required(grade=0)
def check_login(error=None):
    produce.Async_log(g.user, request.url)
@page_mysql_parse.teardown_request
def db_remove(error=None):
    db_idc.DB.session.remove()
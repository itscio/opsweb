#-*- coding: utf-8 -*-
from flask import Blueprint,render_template,g,flash,request
from Modules import produce,check,MyForm,Mysql,main_info
import __init__
app = __init__.app
page_sql_kill=Blueprint('sql_kill',__name__)
@page_sql_kill.route('/sql_kill',methods = ['GET', 'POST'])
@main_info.main_info
def sql_kill():
    user = app.config.get('MYSQL_USER')
    password = app.config.get('MYSQL_PASSWORD')
    form = MyForm.MyForm_sql_kill()
    if form.submit.data:
        try:
            if form.ip.data and form.port.data:
                # 获取页面相关信息
                ip = form.ip.data.strip()
                port = form.port.data.strip()
                keyword = form.select_action.data
                MYSQL = Mysql.MYSQL(user,password,ip,port)
                cmd = 'show processlist;'
                i = 0
                for pid in MYSQL.Run(cmd):
                    if keyword in pid:
                        pid = pid[0]
                        cmd = 'kill %s;' % pid
                        MYSQL.Run(cmd)
                        i = i+1
                MYSQL.Close()
                flash('清理完毕,共清除%i个sql连接......' %i)
        except Exception as e:
            flash(e)
        finally:
            return render_template('Message_static.html',Main_Infos=g.main_infos)
    return render_template('mysql_kill.html',Main_Infos=g.main_infos,form=form)
@page_sql_kill.before_request
@check.login_required(grade=0)
def check_login(error=None):
    produce.Async_log(g.user, request.url)
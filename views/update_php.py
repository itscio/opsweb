#-*- coding: utf-8 -*-
import redis
import time
from flask import Blueprint,redirect,url_for,render_template,render_template_string,g,request
from Modules import check,MyForm,Mysql,produce
import __init__
app = __init__.app
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
Redis = redis.StrictRedis(host=redis_host, port=redis_port)
page_update_php = Blueprint('update_php',__name__)
@page_update_php.route('/update_query',methods = ['GET', 'POST'])
@check.login_required(grade=2)
def update_query():
    K = '%s_%s' %(g.user,g.secret_key)
    Key = '%s_update_php' %K
    return render_template_string(Redis.rpop(Key) or "")

@page_update_php.route('/update_php',methods = ['GET', 'POST'])
@check.login_required(grade=0)
def update_php():
    produce.Async_log(g.user, request.url)
    K = '%s_%s' %(g.user,g.secret_key)
    Key = '%s_update_php' %K
    form = MyForm.MyForm_php()
    if form.submit.data:
        try:
            tm = time.strftime('%Y%m%d%H%M%S',time.localtime())
            Key_file_list ='file_list_%s' %tm
            if form.text.data:
                List = form.text.data.strip().splitlines()
                Action = form.selectaction.data
                Gray = form.Gray.data
            else:
                return redirect(url_for('update_php.update_php'))
            lines = [line.strip() for line in List]
            lines = str(lines)
            Redis.set(Key_file_list,lines)
            Redis.expire(Key_file_list,1800)
            Info = {}
            Type = 1
            Info['arg'] = Type
            Info['action'] = Action
            Info['key'] = Key
            Info['Key_file_lis'] = Key_file_list
            Info['gray'] = Gray
            Redis.delete(Key)
            Redis.rpush('update_php',str(Info))
            mysql_operation = Mysql.mysql_op(g.user,Action,Type,lines,Gray)
            mysql_operation.op_operation()
            Scheduler = produce.Scheduler_publish()
            Scheduler = Scheduler.Scheduler_mem(Scheduler.job_update_php)
            Scheduler.start()
        except Exception as e:
            Redis.lpush(Key,e)
        return render_template('php_update_show.html')
    return render_template('php_update.html',form=form)
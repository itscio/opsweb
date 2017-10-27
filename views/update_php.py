#-*- coding: utf-8 -*-
import redis
import time
from flask import Blueprint,redirect,url_for,render_template,render_template_string,g,request,flash
from Modules import check,MyForm,Mysql,produce,php_update,main_info
import __init__
app = __init__.app
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
Redis = redis.StrictRedis(host=redis_host, port=redis_port)
page_update_php = Blueprint('update_php',__name__)
@page_update_php.route('/update_query',methods = ['GET', 'POST'])
@check.login_required(grade=10)
def update_query():
    K = '%s_%s' %(g.user,g.secret_key)
    Key = '%s_update_php' %K
    Key_incr = '%s_incr' % Key
    Redis.expire(Key,30)
    if Redis.lrange(Key,0,-1):
        data = Redis.rpop(Key)
        if '_End_' in data:
            Redis.expire(Key,3)
        return render_template_string(data)
    else:
        Redis.incr(Key_incr, 1)
        if int(Redis.get(Key_incr)) > 10000:
            Redis.delete(Key_incr)
            return render_template_string("_End_")
        return render_template_string("")

@page_update_php.route('/update_php',methods = ['GET', 'POST'])
@check.login_required(grade=0)
@main_info.main_info
def update_php():
    produce.Async_log(g.user, request.url)
    K = '%s_%s' %(g.user,g.secret_key)
    Key = '%s_update_php' %K
    publish_key = '%s_update_key' %K
    form = MyForm.MyForm_php()
    if form.submit.data:
        try:
            if Redis.exists(Key):
                raise flash('上线操作过于频繁,请稍等%s秒......' %Redis.ttl(Key))
            Redis.lpush(Key, 'check env......')
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
            Info['Key_file_lis'] = Key_file_list
            Info['gray'] = Gray
            Redis.rpush(publish_key,str(Info))
            Redis.lpush(Key, '    --->check env pass!')
            Redis.lpush(Key, '-' * 80 + '\n')
            mysql_operation = Mysql.mysql_op(g.user,Action,Type,lines,Gray)
            mysql_operation.op_operation()
            Scheduler = produce.Scheduler_publish()
            Scheduler = Scheduler.Scheduler_mem(php_update.php_update,publish_key,Key)
            Scheduler.start()
        except Exception as e:
            Redis.lpush(Key,e)
        return render_template('php_update_show.html',Main_Infos=g.main_infos)
    return render_template('php_update.html',Main_Infos=g.main_infos,form=form)
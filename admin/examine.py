#-*- coding: utf-8 -*-
from flask import Blueprint,request,render_template,g,flash
from Modules import check,db_op,produce,loging,ip_area,main_info
from sqlalchemy import desc
import redis
import time
import __init__
app = __init__.app
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
Redis = redis.StrictRedis(host=redis_host, port=redis_port)
page_examine = Blueprint('examine', __name__)
@page_examine.route('/admin/examine')
@check.login_required(grade=0)
@main_info.main_info
def operation():
    produce.Async_log(g.user, request.url)
    db = db_op.op_operation
    try:
        val = db.query.with_entities(db.date,db.time,db.user,db.project,db.version,db.grade,db.action,db.Type).order_by(desc(db.id)).limit(50).all()
        if val:
            tables = ['日期','时间','操作人','项目','版本号','等级','操作','发布']
            return render_template('examine.html',Main_Infos=g.main_infos,tables = tables,values = val)
        else:
            flash('获取数据错误!')
            return render_template('Message_static.html', Main_Infos=g.main_infos)
    except Exception as e:
        flash(e)
        return render_template('Message_static.html',Main_Infos=g.main_infos)

@page_examine.route('/admin/op_log')
@check.login_required(grade=0)
@main_info.main_info
def op_log():
    produce.Async_log(g.user, request.url)
    db = db_op.op_log
    try:
        val = db.query.with_entities(db.date,db.time,db.ip,db.user,db.access).order_by(desc(db.id)).limit(50).all()
        if val:
            tables = ['日期','时间','IP','用户','访问页面']
            return render_template('examine.html',Main_Infos=g.main_infos,tables = tables,values = val)
        else:
            flash('获取数据错误!')
            return render_template('Message_static.html', Main_Infos=g.main_infos)
    except Exception as e:
        flash(e)
        return render_template('Message_static.html',Main_Infos=g.main_infos)

@page_examine.route('/admin/code')
@check.login_required(grade=0)
@main_info.main_info
def code():
    produce.Async_log(g.user, request.url)
    db = db_op.publish_code
    try:
        val = db.query.with_entities(db.project,db.code,db.platfrom,db.user,db.Time).order_by(desc(db.id)).limit(30).all()
        if val:
            tables = ['项目','验证码','平台环境','使用人','使用时间']
            return render_template('examine.html',Main_Infos=g.main_infos,tables = tables,values = val)
        else:
            flash('获取数据错误!')
            return render_template('Message_static.html', Main_Infos=g.main_infos)
    except Exception as e:
        flash(e)
        return render_template('Message_static.html',Main_Infos=g.main_infos)

@page_examine.route('/admin/black_list')
@page_examine.route('/admin/black_list/<int:del_id>')
@check.login_required(grade=0)
@main_info.main_info
def black_list(del_id=None):
    produce.Async_log(g.user, request.url)
    db = db_op.haproxy_blacklist
    VAL = []
    try:
        val = db.query.with_entities(db.id,db.addtime,db.ip,db.rule,db.expire).filter(db.stats=='0').order_by(desc(db.id)).limit(1000).all()
        if val:
            tables = ['触发日期','异常IP','IP归属地','触发规则','自动解封日期',' 操作']
            if del_id:
                db.query.filter(db.id == str(del_id)).update({db.stats: '2'})
                db_op.DB.session.commit()
                val = db.query.with_entities(db.id, db.addtime,db.ip,db.rule,db.expire).filter(db.stats == '0').order_by(desc(db.addtime)).limit(1000).all()
            for va in val:
                va = list(va)
                va.insert(3,ip_area.Search(str(va[2])))
                VAL.append(va)
            return render_template('black_list.html',Main_Infos=g.main_infos,tables = tables,values = VAL)
        else:
            flash('获取数据错误!')
            return render_template('Message_static.html', Main_Infos=g.main_infos)
    except Exception as e:
        flash(e)
        return render_template('Message_static.html',Main_Infos=g.main_infos)

@page_examine.route('/admin/backup_mysql_results')
@check.login_required(grade=0)
@main_info.main_info
def backup_mysql_results():
    produce.Async_log(g.user, request.url)
    try:
        if Redis.exists('finish_backup'):
            Infos = Redis.lrange('finish_backup',0,-1)
            if Infos:
                Infos = [eval(info) for info in set(Infos)]
                tt = time.strftime('%Y-%m-%d', time.localtime())
                tables = ('日期','备份服务器','MYSQL服务器','服务器端口',' 状态')
                return render_template('backup_mysql_results.html',Main_Infos=g.main_infos,Infos=Infos,tt=tt,tables=tables)
            else:
                raise flash('检查结果:线上数据库备份异常!')
        else:
           raise flash('检查结果:线上数据库备份异常!')
    except Exception as e:
        if 'old' not in str(e):
            flash(str(e))
        return render_template('Message_static.html',Main_Infos=g.main_infos)
@page_examine.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
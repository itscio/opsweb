#-*- coding: utf-8 -*-
from flask import Blueprint,request,render_template,g,flash,render_template_string
from Modules import check,db_op,produce
from sqlalchemy import desc
page_examine = Blueprint('examine', __name__)
@page_examine.route('/admin/examine')
def operation():
    db = db_op.op_operation
    try:
        val = db.query.with_entities(db.date,db.time,db.user,db.project,db.version,db.action,db.Type).order_by(desc(db.id)).limit(50).all()
        if val:
            tables = ['日期','时间','操作人','项目','版本号','操作','发布']
            return render_template('examine.html',tables = tables,values = val)
        else:
            return render_template_string('获取数据错误!')
    except Exception as e:
        flash(e)
        return render_template('Message.html')

@page_examine.route('/admin/op_log')
def op_log():
    db = db_op.op_log
    try:
        val = db.query.with_entities(db.date,db.time,db.ip,db.user,db.access).order_by(desc(db.id)).limit(50).all()
        if val:
            tables = ['日期','时间','IP','用户','访问页面']
            return render_template('examine.html',tables = tables,values = val)
        else:
            return render_template_string('获取数据错误!')
    except Exception as e:
        flash(e)
        return render_template('Message.html')

@page_examine.route('/admin/code')
def code():
    db = db_op.publish_code
    try:
        val = db.query.with_entities(db.project,db.code,db.platfrom,db.user,db.Time).order_by(desc(db.id)).limit(10).all()
        if val:
            tables = ['项目','验证码','平台环境','申请人','申请时间']
            return render_template('examine.html',tables = tables,values = val)
        else:
            return render_template_string('获取数据错误!')
    except Exception as e:
        flash(e)
        return render_template('Message.html')

@page_examine.before_request
@check.login_required(grade=0)
def check_login(error=None):
    produce.Async_log(g.user, request.url)

@page_examine.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
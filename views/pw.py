#-*- coding: utf-8 -*-
from flask import Blueprint,redirect,url_for,render_template,flash,make_response,g,request
from sqlalchemy import and_
from Modules import db_op,produce, MyForm, Md5,check
page_pw = Blueprint('pw',__name__)
timestamp = check.timestamp(7)
@page_pw.route('/pw',methods = ['GET', 'POST'])
def pw():
    form = MyForm.MyForm_pw()
    if form.submit.data:
        pw = Md5.Md5_make(form.password.data)
        pw1 = form.new_password1.data
        pw2 = form.new_password2.data
        try:
            db = db_op.idc_users
            va = db.query.filter(and_(db.name == g.user, db.passwd == pw)).first()
            if pw1 == pw2:
                if va:
                    va.passwd = Md5.Md5_make(pw1)
                    db_op.DB.session.commit()
                    db_op.DB.session.close()
                    flash('密码修改成功,请重新登录!')
                    app_resp = make_response( redirect(url_for('index.index')))
                    return app_resp
                else:
                    flash('旧密码错误!')
            else:
                flash('新密码不一致!')
        except Exception as e:
            flash(e)
    return render_template('password.html',form=form)

@page_pw.before_request
@check.login_required(grade=2)
def check_login(error=None):
    produce.Async_log(g.user, request.url)

@page_pw.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()

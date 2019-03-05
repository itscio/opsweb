#-*- coding: utf-8 -*-
from flask import Flask,Blueprint,request,render_template,g,url_for,redirect,flash,render_template_string
from Modules import db_op,check,produce,loging,MyForm,tools,Md5
from sqlalchemy import and_,desc
import time,datetime
import string
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)
app.config.from_pyfile('../conf/sql.conf')
DB = SQLAlchemy(app)
logging = loging.Error()
page_approval = Blueprint('approval', __name__)
#新用户申请权限
@page_approval.route('/apply',methods = ['GET', 'POST'])
@check.login_required(grade=11)
def apply():
    try:
        produce.Async_log(g.user, request.url)
        dt = time.strftime('%Y-%m-%d', time.localtime())
        ym = time.strftime('%Y', time.localtime())
        db_approval = db_op.user_approval
        # 判断游客身份
        if '11' in g.grade:
            form = MyForm.MyForm_apply()
            val = db_approval.query.filter(and_(db_approval.dingId == g.dingId,db_approval.status == '待审批')).all()
            if val:
               raise flash('权限还未审批,请耐心等待!')
            val = db_approval.query.filter(and_(db_approval.dingId == g.dingId,db_approval.status == '审批拒绝')).all()
            if val:
               raise flash('权限审批未通过!')
            if form.submit.data:
                grade = form.select.data
                v = db_approval(name=g.user,openid=g.openid,dingId=g.dingId,apply_time=dt,approval_time='',approval_person='',apply_grade=grade,status='待审批')
                db_op.DB.session.add(v)
                db_op.DB.session.commit()
                raise flash('权限申请提交完成、请等待审批!')
            return render_template('apply.html',form=form,ym=ym)
    except Exception as e:
        if 'old-style' not in str(e):
            flash(str(e))
    return redirect(url_for('login.login'))

#权限申请审批
@page_approval.route('/approval',methods = ['GET', 'POST'])
@check.login_required(grade=0)
def approval():
    try:
        produce.Async_log(g.user, request.url)
        dt = time.strftime('%Y-%m-%d', time.localtime())
        db_approval = db_op.user_approval
        db_auth = db_op.user_auth
        db_permission = db_op.permission
        tables = ('申请人', '申请日期', '申请权限', '审批状态', '操作')
        action = tools.http_args(request,'action')
        id = tools.http_args(request,'id')
        status = {'allow': '审批通过', 'deny': '审批拒绝'}
        # 判断访问参数
        if action in ('allow', 'deny') and id:
            #验证操作人是否真实
            val = db_auth.query.filter(and_(db_auth.name == g.user, db_auth.dingId == g.dingId)).all()
            if val:
                # 修改申请权限表状态
                db_approval.query.filter(and_(db_approval.id == id)).update({db_approval.status: status[action], db_approval.approval_time: dt,db_approval.approval_person: g.user})
                db_op.DB.session.commit()
                if action == 'allow':
                    # 写入授权列表
                    vals = db_approval.query.with_entities(db_approval.name, db_approval.openid, db_approval.dingId,
                                                           db_approval.apply_grade).filter(db_approval.id == id).all()
                    name, openid, dingId, grade = vals[0]
                    if int(grade) == 1:
                        c = db_auth(name=name, openid=openid, dingId=dingId,
                                    grade=','.join([str(x) for x in range(1, 11)]),token='',update_time='')
                    else:
                        c = db_auth(name=name, openid=openid, dingId=dingId, grade='%s,10' % grade,token='',update_time='')
                    db_op.DB.session.add(c)
                    db_op.DB.session.commit()
    except  Exception as e:
        logging.error(e)
        db_op.DB.session.rollback()
    finally:
        # 获取权限列表
        auths = db_permission.query.with_entities(db_permission.authid, db_permission.auth).all()
        auths = {val[0]: val[1] for val in auths}
        values = db_approval.query.with_entities(db_approval.id, db_approval.name, db_approval.apply_time,db_approval.apply_grade, db_approval.status).filter(db_approval.status == '待审批').all()
    return render_template('approval.html', tables=tables, values=values, auths=auths)

#颁发token
@page_approval.route('/platform_token')
@page_approval.route('/platform_token/<action>/<int:id>')
@page_approval.route('/platform_token/<action>/<int:id>/<args>')
@check.login_required(grade=1)
def platform_token(action=None,id=None,args=None):
    produce.Async_log(g.user, request.url)
    db_token = db_op.platform_token
    tm = time.strftime('%Y-%m-%d', time.localtime())
    form = MyForm.Form_platform_token()
    tables = ['第三方平台', '连接方式', 'Token', '颁发日期', '失效日期', '管理']
    if action == 'add':
        expire_date = "2999-12-30"
        if id >0:
            expire_date = datetime.datetime.now() + datetime.timedelta(days=id)
            expire_date = expire_date.strftime('%Y-%m-%d')
        try:
            c = db_token(platform=args,channel='api',token=Md5.Md5_make(tools.Produce(8,string.digits)),award=tm,expire=expire_date)
            db_op.DB.session.add(c)
            db_op.DB.session.commit()
            return render_template_string('success')
        except Exception as e:
            logging.error(e)
            return render_template_string('fail')
    if action == 'modify':
        try:
            db_token.query.filter(db_token.id==id).update({db_token.expire:args})
            db_op.DB.session.commit()
            return render_template_string('success')
        except Exception as e:
            logging.error(e)
            return render_template_string('fail')
    if action == 'drop':
        try:
            v = db_token.query.filter(db_token.id==id).all()
            for c in v:
                db_op.DB.session.delete(c)
                db_op.DB.session.commit()
            return render_template_string('success')
        except Exception as e:
            logging.error(e)
            return render_template_string('fail')
    vals = db_token.query.with_entities(db_token.id, db_token.platform, db_token.channel, db_token.token,
                                            db_token.award, db_token.expire).order_by(desc(db_token.id)).all()
    return render_template('platform_token.html',form=form,vals = vals,tables=tables,tm=tm)
@page_approval.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
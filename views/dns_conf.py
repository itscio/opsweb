#-*- coding: utf-8 -*-
from sqlalchemy import and_
from flask import Blueprint,render_template,g,flash,request
from Modules import MyForm,db_op,produce,check
import re
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
app = Flask(__name__)
app.config.from_pyfile('../conf/sql.conf')
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/redis.conf')
page_dns_conf = Blueprint('dns_conf',__name__)
@page_dns_conf.route('/dns_conf',methods = ['GET', 'POST'])
def dns_conf():
    form = MyForm.MyForm_dns_conf()
    if form.submit.data:
        try:
            domain = form.select_domain.data.strip()
            Type = form.select_type.data.strip()
            action = form.select_action.data.strip()
            field = form.field.data.strip()
            system = form.select_sys.data.strip()
            ip = form.ip.data.strip()
            db = db_op.dns_innr
            if field:
                if  field.endswith('.xxxx.com') or field.endswith('.service.xxxx') or field.endswith('.sql.xxxx'):
                    raise flash("二级域名格式错误!")
                value = db.query.with_entities(db.ip).filter(and_(db.domain == domain, db.Type == Type, db.field == field,db.system == system)).all()
                if action == 'add':
                    if system == 'cw' and domain != 'xxxx.com':
                        raise flash('测外只可以操作moji.com域名!')
                    if value:
                            raise flash('%s  IN  %s  %s 该DNS记录已存在' % (field, Type,str(value[0][0])))
                    if ip:
                        if Type == 'CNAME' and not ip.endswith('.'):
                            raise flash('CNAME 主机名格式错误!')
                        if Type == 'A' and not re.search('\.\d{1,3}$',ip):
                            raise flash('A IP地址格式错误!')
                        c = db(domain=domain, field=field, Type=Type, ip=ip,stats='1',system=system)
                        db_op.DB.session.add(c)
                        db_op.DB.session.commit()
                        flash(' %s  IN  %s  %s 添加完成!' % (field, Type, ip))
                    else:
                        flash('IP地址/主机名不能为空!')
                elif value:
                    if action == 'modify':
                        if ip:
                            if Type == 'CNAME' and not ip.endswith('.'):
                                raise flash('CNAME 主机名格式错误!')
                            if Type == 'A' and not re.search('\.\d{1,3}$',ip):
                                raise flash('A IP地址格式错误!')
                            db.query.filter(and_(db.domain == domain,db.Type == Type,db.field == field,db.system == system)).update({db.ip:ip,db.stats:'1'})
                            db_op.DB.session.commit()
                            flash(' %s  IN  %s  %s 修改完成!' %(field, Type,ip))
                        else:
                            flash('IP地址/主机名不能为空!')
                    if action == 'query':
                        ip = str(value[0][0])
                        flash('查询结果: {0}  IN  {1}   {2}'.format(field,Type,ip))
                    if action == 'del':
                        v = db.query.filter(and_(db.domain == domain, db.Type == Type, db.field == field,db.system == system)).all()
                        for c in v:
                            db_op.DB.session.delete(c)
                            db_op.DB.session.commit()
                        flash('%s记录已删除!' %(field))
                else:
                    flash('没有找到相关数据!')
            else:
                flash('二级域名不能为空!')
        except Exception as e:
            if 'old-style' not in str(e):
                flash(e)
    return render_template('dns_conf.html',form=form)
@page_dns_conf.before_request
@check.login_required(grade=1)
def check_login(exception = None):
    produce.Async_log(g.user, request.url)
@page_dns_conf.teardown_request
def db_remove(exception):
    db_op.DB.session.remove()

#-*- coding: utf-8 -*-
from imp import reload
import re
from sqlalchemy import and_
from flask import Blueprint,render_template,g,flash,request
from Modules import MyForm,check,db_op,produce,loging,main_info
import __init__
app = __init__.app
logging = loging.Error()
page_java_list = Blueprint('java_list',__name__)
@page_java_list.route('/java_list',methods = ['GET', 'POST'])
@main_info.main_info
def List():
    reload(MyForm)
    form = MyForm.MyFrom_java_list()
    g.Type = None
    if form.submit_query.data:
        try:
            db = db_op.java_list
            Type = int(form.select.data)
            Project = form.Project.data
            val = db.query.with_entities(db.user, db.ip).filter(and_(db.project == Project, db.type == Type)).all()
            db_project = db_op.project_level
            project_val = db_project.query.with_entities(db_project.level).filter(db_project.project == Project).all()
            if val:
                val = set(val)
                v = [(v[0].encode('UTF-8'), v[1].encode('UTF-8')) for v in val if v]
                values = '%s = %s' % (Project, str(v))
                if project_val and Type == 1:
                    flash('项目等级为%s级,查询结果:' %project_val[0][0])
                else:
                    flash('查询结果:')
                flash(values)
            else:
                flash('%s 没有找到!' % Project)
        except Exception as e:
            logging.error(e)
            flash('查询数据失败!')
    if form.submit_modify.data:
        try:
            db = db_op.java_list
            db_pool = db_op.server_pool
            va = []
            Type = int(form.select.data)
            if g.grade == 0:
                line = form.text.data
                Ma = re.match('.*\.war',line)
                if not Ma:
                    flash("the project must be *.war with begin!")
                    return render_template('Message_static.html')
                line = line.split('=')
                Project = line[0]
                ips = eval(line[1])
                Info = db.query.with_entities(db.ip, db.user).filter(and_(db.project == Project, db.type == Type)).all()
                v = db.query.filter(and_(db.project == Project, db.type == Type)).all()
                for c in v:
                    db_op.DB.session.delete(c)
                    db_op.DB.session.commit()
                if ips:
                    for v in ips:
                        user = v[0]
                        ip = v[1]
                        if '172.16.9.' not in ip and Type == 2:
                            flash('测外不允许使用{0}该IP地址！'.format(ip))
                            break
                        c = db_op.java_list(project = Project,user = user,ip = ip,type = Type,Gray='0',operation = 'baihe')
                        db_op.DB.session.add(c)
                        db_op.DB.session.commit()
                        val = db.query.with_entities(db.user,db.ip).filter(and_(db.project == Project,db.user == user,db.ip == ip,db.type == Type)).all()
                        if val:
                            val = val[0]
                            user = val[0].encode('UTF-8')
                            ip = val[1].encode('UTF-8')
                            v = (user,ip)
                            va.append(v)
                    va = str(va)
                    # 修改资源池表
                    db_pool.query.filter(and_(db_pool.user == user, db_pool.ip == ip)).update({db_pool.status: '1'})
                    db_op.DB.session.commit()
                    flash('修改结果:')
                    flash('%s = %s' %(Project,va))
                else:
                    if Info:
                        for info in Info:
                            ip, user = info
                            db_pool.query.filter(and_(db_pool.user == user, db_pool.ip == ip)).update({db_pool.status:'0'})
                            db_op.DB.session.commit()
                    flash('%s 已删除!' %Project)
            else:
                flash("没有权限进行该操作!")
        except Exception as e:
            flash(e)
            flash('修改数据失败!')
    return render_template('java_list.html',Main_Infos=g.main_infos,form=form)
@page_java_list.before_request
@check.login_required(grade=10)
def check_login(error=None):
    produce.Async_log(g.user, request.url)
@page_java_list.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
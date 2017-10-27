#-*- coding: utf-8 -*-
from imp import reload
from sqlalchemy import and_
from flask import Blueprint,render_template,g,flash,request
from Modules import MyForm,check,loging,db_op,produce,main_info
import __init__
app = __init__.app
logging = loging.Error()
page_php_list = Blueprint('php_list',__name__)
@page_php_list.route('/php_list',methods = ['GET', 'POST'])
@main_info.main_info
def List():
    reload(MyForm)
    form = MyForm.MyFrom_php_list()
    if form.submit_query.data:
        try:
            db = db_op.php_list
            Type = int(form.select.data)
            project = form.Project.data
            if project == 'baihePhpGlobalLibrary_publish':
                val = db.query.with_entities(db.ip).filter(db.type == Type).all()
            else:
                val = db.query.with_entities(db.ip).filter(and_(db.project == project, db.type == Type)).all()
            if val:
                val = set(val)
                v = [v[0].encode('UTF-8') for v in val if v]
                values = '%s = %s' % (project, str(v))
                db_project = db_op.project_level
                project_val = db_project.query.with_entities(db_project.level).filter(db_project.project == project).all()
                if project_val and Type == 1:
                    flash('项目等级为%s级,查询结果:' %project_val[0][0])
                else:
                    flash('查询结果:')
                flash(values)
            else:
                flash('%s 没有找到!' % project)
        except Exception as e:
            logging.error(e)
            flash('查询数据失败!')
    if form.submit_modify.data:
        try:
            db = db_op.php_list
            db_pool = db_op.server_pool
            Type = int(form.select.data)
            if g.grade == 0:
                line=form.text.data
                line = line.split('=')
                project = line[0]
                ips = eval(line[1])
                if 'baihePhpGlobalLibrary' == project:
                    flash("%s Without modification!" %project)
                    return render_template('Message_static.html',Main_Infos=g.main_infos)
                Info = db.query.filter(and_(db.project == project,db.type == Type)).all()
                for c in Info:
                    db_op.DB.session.delete(c)
                    db_op.DB.session.commit()
                if ips:
                    va = []
                    for ip in ips:
                        c = db_op.php_list(project = project,user = 'work',ip = ip,type = Type,Gray='0',operation = 'baihe')
                        db_op.DB.session.add(c)
                        db_op.DB.session.commit()
                        val = db.query.filter(and_(db.project == project,db.ip == ip,db.type == Type )).all()
                        if val:
                            v = str(val[0]).split(',')
                            va.append(v[2])
                    va = str(va)
                    db_pool.query.filter(and_(db_pool.user == 'work', db_pool.ip == ip)).update({db_pool.status: '1'})
                    db_op.DB.session.commit()
                    flash('修改结果:')
                    flash('%s = %s' %(project,va))
                else:
                    if Info:
                        for info in Info:
                            ip, user = info
                            db_pool.query.filter(and_(db_pool.user == user,db_pool.ip == ip)).update({db_pool.status: '0'})
                            db_op.DB.session.commit()
                    flash('%s 已删除!' %project)
            else:
                flash("没有权限进行该操作!")
        except Exception as e:
            logging.error(e)
            flash('修改数据失败!')
    return render_template('php_list.html',Main_Infos=g.main_infos,form=form)
@page_php_list.before_request
@check.login_required(grade=10)
def check_login(error=None):
    produce.Async_log(g.user, request.url)
@page_php_list.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
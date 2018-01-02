#-*- coding: utf-8 -*-
from flask import Blueprint,render_template,g,request
from Modules import check,produce,main_info,loging,db_op
import time
import __init__
app = __init__.app
page_project_show = Blueprint('project_show',__name__)
@page_project_show.route('/project_show')
@main_info.main_info
def project_show():
    db = db_op.project_show
    tm = time.strftime('%Y%m%d', time.localtime())
    Infos = db.query.with_entities(db.project,db.dev_time,db.last_tag,db.test_time,db.pub_time).filter().all()
    Projects = {}
    for info in Infos:
        test_time = pub_time = None
        project = info[0]
        if info[3]:
            dev_time = int(info[3])-int(info[1])
        else:
            dev_time = int(tm)-int(info[1])+1
        if info[4]:
            test_time = int(info[4])-int(info[3])
            pub_time = int(tm) - int(info[4])+1
        else:
            if info[2]:
                test_time = int(tm)-int(info[3])+1
        Projects[project] = [dev_time,test_time,pub_time,info[2]]
    return render_template('project_show.html',Main_Infos=g.main_infos,Projects = Projects)
@page_project_show.before_request
@check.login_required(grade=10)
def check_login(error=None):
    produce.Async_log(g.user, request.url)
@page_project_show.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
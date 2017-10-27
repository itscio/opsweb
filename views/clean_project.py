#-*- coding: utf-8 -*-
from imp import reload
from flask import Blueprint,render_template,g,flash,request
from Modules import check,loging,MyForm,db_op,produce,SSH,db_idc,main_info
from sqlalchemy import and_ ,distinct
import __init__
import requests
app = __init__.app
HA_API = app.config.get('HAPROXY_API')
logging = loging.Error()
page_Clean_project = Blueprint('clean_project',__name__)
@page_Clean_project.route('/clean_project',methods = ['GET', 'POST'])
@main_info.main_info
def clean_project():
    form_php = MyForm.MyFrom_php_list()
    form_java = MyForm.MyFrom_java_list()
    def _CURL_API():
        try:
            #调用API接口
            URLS = ["%s?type=cw&ip=127.0.0.1:80&domain=test.baihe.com&intranet=True" %HA_API,"%s?type=cw&ip=127.0.0.1:80&domain=test.baihe.com" %HA_API]
            for URL in URLS:
                requests.request('get', URL, timeout=10)
        except Exception as e:
            flash(e)
    def clean_php(form):
        try:
            App = form.Project.data
            Type = int(form.select.data)
            user = 'work'
            if Type == 1:
                raise AssertionError('暂时不支持该选择!')
            db = db_op.php_list
            project_db = db_op.project_level
            db_haproxy = db_op.haproxy_conf
            val = db.query.with_entities(db.ip).filter(and_(db.project == '%s' % App, db.type == '%i' % Type)).all()
            if val:
                v = db.query.filter(and_(db.project == '%s' % App, db.type == '%i' % Type)).all()
                for c in v:
                    db_op.DB.session.delete(c)
                    db_op.DB.session.commit()
                p = project_db.query.filter(project_db.project == '%s' %App).all()
                for c in p:
                    db_op.DB.session.delete(c)
                    db_op.DB.session.commit()
                flash('上线配置表中的{0}相关配置清除完成!'.format(App))
                sip = [v[0].encode('UTF-8') for v in val if v]
                # 删除应用部署表
                dbidc = db_idc.idc_app
                val = dbidc.query.with_entities(distinct(dbidc.domainName)).filter(dbidc.appName == '%s' %App).all()
                Domains = [v[0].encode('UTF-8') for v in val if v]
                v = dbidc.query.filter(dbidc.appName == '%s' % App).all()
                for c in v:
                    db_idc.DB.session.delete(c)
                    db_idc.DB.session.commit()
                for ip in sip:
                    for Domain in Domains:
                        cmds = ['/bin/rm -f /home/work/local/nginx/conf/servers/{0}'.format(Domain),
                                '/bin/mv /home/work/baihe/{0} /home/work/baihe/{0}.bak'.format(App)]
                        Ssh = SSH.ssh(user,ip)
                        Ssh.Run(cmds)
                        flash('{0}主机中的{1}相关nginx配置清除完成!'.format(ip,App))
                        if Type == 2:
                            v = db_haproxy.query.filter(and_(db_haproxy.ip == ip,db_haproxy.domain == Domain,db_haproxy.Type== 'cw')).all()
                            for c in v:
                                db_op.DB.session.delete(c)
                                db_op.DB.session.commit()
                            _CURL_API()
                            flash('{0}主机的{1}相关测外haporxy配置清除完毕!'.format(ip, App))
                            val = dbidc.query.filter(dbidc.ip == '%s' % ip).all()
                            if not val:
                                db_server_pool = db_op.server_pool
                                db_server_pool.query.filter(and_(db_server_pool.ip == ip, db_server_pool.user == user,db_server_pool.target == 'cw')).update({db_server_pool.status: '0'})
                                db_op.DB.session.commit()
                                flash('{0}主机已重新放入资源池!'.format(ip))
                        if Type == 1:
                            flash('后续需要手动清除线上haporxy中的{0}的相关配置！'.format(App))
            else:
                flash('%s not fond!' % App)
        except Exception as e:
            flash(e)
    def clean_jboss(form):
        try:
            App = form.Project.data
            Type = int(form.select.data)
            if Type == 1:
                raise AssertionError('暂时不支持该选择!')
            db = db_op.java_list
            project_db = db_op.project_level
            db_haproxy = db_op.haproxy_conf
            val = db.query.with_entities(db.ip,db.user).filter(and_(db.project == '%s' % App, db.type == '%i' % Type)).all()
            v = db.query.filter(and_(db.project == '%s' % App, db.type == '%i' % Type)).all()
            for c in v:
                db_op.DB.session.delete(c)
                db_op.DB.session.commit()
            p = project_db.query.filter(project_db.project == '%s' % App).all()
            for c in p:
                db_op.DB.session.delete(c)
                db_op.DB.session.commit()
            flash('上线配置表中的{0}相关配置清除完成!'.format(App))
            Info = [(v[0].encode('UTF-8'),v[1].encode('UTF-8')) for v in val if v]
            #删除应用部署表
            dbidc = db_idc.idc_app
            val = dbidc.query.with_entities(distinct(dbidc.domainName)).filter(dbidc.appName == '%s' % App).all()
            Domains = [v[0].encode('UTF-8') for v in val if v]
            v = dbidc.query.filter(dbidc.appName == '%s' % App).all()
            for c in v:
                db_idc.DB.session.delete(c)
                db_idc.DB.session.commit()
            for ip,user in Info:
                ssh = SSH.ssh(user, ip)
                cmd = 'cd /home/' + user + ' && ls |grep jboss-'
                Results = ssh.Run(cmd)
                jbossName = Results['stdout']
                count = len(jbossName)
                if count == 1:
                    War_Path = '/home/%s/%s/server/default/deploy/' % (user, jbossName[0])
                    cmds = ['/bin/rm -rf {0}/{1}'.format(War_Path, App), '/bin/bash  /home/java/stopJboss.sh',
                            '/usr/bin/pkill -9 java']
                    ssh.Run(cmds)
                    flash('{0}主机中的{1}相关配置清除完成!'.format(ip, App))
                else:
                    flash('ERROR:{0}主机中jboss目录有多个!'.format(ip, App))
                for Domain in Domains:
                    if Type == 2:
                        v = db_haproxy.query.filter(and_(db_haproxy.ip == ip, db_haproxy.domain == Domain, db_haproxy.Type == 'cw')).all()
                        for c in v:
                            db_op.DB.session.delete(c)
                            db_op.DB.session.commit()
                        _CURL_API()
                        flash('{0}主机的{1}相关测外haporxy配置清除完毕!'.format(ip,App))
                        db_server_pool = db_op.server_pool
                        db_server_pool.query.filter(and_(db_server_pool.ip == ip, db_server_pool.user == user,db_server_pool.target == 'cw')).update({db_server_pool.status:'0'})
                        db_op.DB.session.commit()
                        flash('{0}主机已重新放入资源池!'.format(ip))
                    if Type == 1:
                        flash('后续需要手动清除线上haporxy中的{0}的相关配置！'.format(App))
        except Exception as e:
            flash(e)
    if form_php.submit_modify.data:
        clean_php(form_php)
    if form_java.submit_modify.data:
        clean_jboss(form_java)
    return render_template('clean_project.html',Main_Infos=g.main_infos,form_php=form_php,form_java=form_java)

@page_Clean_project.before_request
@check.login_required(grade=0)
def check_login(error=None):
    reload(MyForm)
    produce.Async_log(g.user, request.url)

@page_Clean_project.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
    db_idc.DB.session.remove()
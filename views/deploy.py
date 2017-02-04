#-*- coding: utf-8 -*-
from flask import Blueprint,render_template,g,flash,request
from Modules import check,MyForm,SSH,db_op,produce,db_idc
from sqlalchemy import and_
import requests
import os
import __init__
app = __init__.app
page_deploy = Blueprint('deploy',__name__)
page_haproxy_reload = Blueprint('haproxy_reload',__name__)
@page_deploy.route('/deploy_jboss',methods = ['GET', 'POST'])
def deploy_jboss():
    reload(MyForm)
    form = MyForm.MyForm_deploy_jboss()
    try:
        if form.submit_produce.data and form.input_produce.data:
            Warname = form.input_produce.data.strip()
            Info = form.select_produce.data.strip()
            Type = '1'
        elif form.submit_test.data and form.input_test.data:
            Warname = form.input_test.data.strip()
            Info = form.select_test.data.strip()
            Type = '2'
        else:
            return render_template('deploy_jboss.html', form=form)
        assert Info,'服务器选择不能为空!'
        assert Warname.endswith('.war') ,'war包名称应以.war结尾'
        #判断测外环境
        if Type == '2':
            assert form.input_domain.data,'项目域名不能为空!'
            Domain = form.input_domain.data.strip()
            if not form.haproxy.data and not form.haproxy_intranet.data:
                raise AssertionError, 'HAPROXY选择不能为空!'
        Info = Info.split(':')
        user = Info[1]
        ip = Info[0]
        db = db_op.java_list
        val = db.query.filter(and_(db.project == Warname,db.ip == ip,db.user == user, db.type == Type)).all()
        if val:
            flash('{0}在{1}的{2}环境已存在!'.format(Warname,ip,user))
        else:
            Ssh = SSH.ssh(user,ip)
            os.system('/usr/bin/wget -P /tmp/ http://172.16.4.138/software/jboss/{0}.zip'.format(user))
            Ssh.Scp('/tmp/{0}.zip'.format(user),'/home/{0}/{0}.zip'.format(user))
            os.system('/bin/rm -f /tmp/{0}.zip'.format(user))
            cmds = ['cd /home/{0} && /usr/bin/unzip -qo {0}.zip && /bin/rm -f {0}.zip'.format(user),
                    '/bin/rm -f /home/{0}/{0}.zip'.format(user),
                    'mkdir -p /home/{0}/jboss-baihe/server/default/deploy/{1}'.format(user,Warname),
                    '/usr/bin/pkill -9 java',
                    'source ~/.bash_profile && /bin/bash /home/{0}/startJboss.sh'.format(user)]
            for cmd in cmds:
                Ssh.Run(cmd)
            Ssh.Close()
            c = db(project=Warname, user=user, ip=ip, type=Type, Gray='0',operation = 'baihe')
            db_op.DB.session.add(c)
            db_op.DB.session.commit()
            # 修改资源池表
            db = db_op.server_pool
            db.query.filter(and_(db.user == user,db.ip == ip)).update({db.status:'1'})
            db_op.DB.session.commit()
            flash('{0} 在{1}的{2}环境部署成功,上线操作后可正常访问!'.format(Warname, ip, user))
            # 测外发布
            if Type == '2':
                # 调取api接口生成haproxy配置文件
                Type = 'cw'
                ports = {'java': '18080', 'java2': '28080', 'java3': '38080', 'java4': '48080'}
                def _CURL_API(Domain,internet=None):
                    Domains = [Domain]
                    if ',' in Domain:
                        Domains = Domain.split(',')
                    for Domain in Domains:
                        # 修改应用部署表
                        dbidc = db_idc.idc_app
                        c = dbidc(ip=ip, user=user,appName=Warname,domainName=Domain)
                        db_idc.DB.session.add(c)
                        db_idc.DB.session.commit()
                        # 调用haproxy APi接口
                        URL = "https://"
                        Params = {'type':Type, 'ip':'{0}:{1}'.format(ip,ports[user]),'domain':Domain}
                        if internet:
                            Params['intranet'] = 'True'
                            Arg = '内部'
                        else:
                            Arg = '外部'
                        f = requests.request('get', URL,params=Params, timeout=10)
                        if 'result' in f.json():
                            flash('信息:{0} {1}HAPROXY配置{2}'.format(Domain,Arg,f.json()['result']))
                if form.haproxy_intranet.data:
                    _CURL_API(Domain,internet=True)
                if form.haproxy.data:
                    _CURL_API(Domain)
    except Exception as e:
        flash(e)
    return render_template('deploy_jboss.html',form=form)
@page_deploy.route('/deploy_nginx',methods = ['GET', 'POST'])
def deploy_nginx():
    form = MyForm.MyForm_deploy_nginx()
    if form.submit.data:
        try:
            Type = int(form.select.data)
            assert form.input_domain.data,'项目域名不能为空!'
            domains = form.input_domain.data.strip()
            assert form.input_root.data,'项目路径不能为空!'
            root_path = form.input_root.data.strip()
            project = root_path.split('/')
            if len(project) < 5:
                raise ImportError,'非法项目路径!'
            else:
                project = project[4]
            assert form.ip.data,'服务器IP不能为空!'
            ips = form.ip.data.strip()
            if not form.haproxy.data and not form.haproxy_intranet.data and Type == 2:
                raise AssertionError,'HAPROXY选择不能为空!'
            for ip in ips.splitlines():
                if g.grade == 2 and '172.16.9.' not in ip:
                    flash('非法IP地址,请确认测外服务器IP!')
                else:
                    db = db_op.php_list
                    val = db.query.filter(and_(db.ip == ip, db.project == project, db.type == Type)).all()
                    if val:
                        flash('{0} {1} nginx虚拟主机配置文件已部署!'.format(ip,project))
                    else:
                        ssh = SSH.ssh('work',ip)
                        try:
                            # 生成配置文件
                            for domain in domains.strip().split(','):
                                # 修改应用部署表
                                dbidc = db_idc.idc_app
                                c = dbidc(ip=ip, user='work', appName=project, domainName=domain)
                                db_idc.DB.session.add(c)
                                db_idc.DB.session.commit()
                                # 调用haproxy APi接口
                                Dst_path = '/tmp/{0}'.format(domain)
                                mod_path = "{0}/../conf/nginx_template.cfg".format(page_deploy.root_path)
                                if os.path.exists(Dst_path):
                                    os.remove(Dst_path)
                                with open(mod_path, 'r') as f:
                                    for line in f:
                                        line = line.strip().replace('DOMAIN', domain).replace('ROOT_PATH', root_path)
                                        with open(Dst_path, 'a+') as F:
                                            F.write('{0}\n'.format(line))
                                ssh.Scp(Dst_path,'/home/work/local/nginx/conf/servers/{0}'.format(domain))
                                flash('{0} {1} nginx虚拟主机部署完毕!'.format(ip, domain))
                        except Exception as e:
                            flash(e)
                        else:
                            cmds = ["[ -z $(/bin/netstat -lntp|grep nginx|awk '{print $1}') ] && /home/work/local/nginx/sbin/nginx","/home/work/local/nginx/sbin/nginx -s reload"]
                            for cmd in cmds:
                                ssh.Run(cmd)
                            #在上线配置表中插入数据
                            c = db(project=project,user='work',ip=ip,type=Type,Gray='0',operation = 'baihe')
                            db_op.DB.session.add(c)
                            db_op.DB.session.commit()
                            if Type == 2:
                                # 调取api接口生成haproxy配置文件
                                Type = 'cw'
                                def _CURL_API(Domain, internet=None):
                                    Domains = [Domain]
                                    if ',' in Domain:
                                        Domains = Domain.split(',')
                                    for Domain in Domains:
                                        URL = "https://"
                                        Params = {'type': Type, 'ip': '{0}:80'.format(ip),'domain': Domain}
                                        if internet:
                                            Params['intranet'] = 'True'
                                            Arg = '内部'
                                        else:
                                            Arg = '外部'
                                        f = requests.request('get', URL,params=Params,timeout=10)
                                        if 'result' in f.json():
                                            flash('信息:{0} {1}HAPROXY配置{2}'.format(Domain, Arg, f.json()['result']))
                                if form.haproxy_intranet.data:
                                    _CURL_API(domain, internet=True)
                                if form.haproxy.data:
                                    _CURL_API(domain)
        except Exception as e:
            flash(e)
    return render_template('deploy_nginx.html', form=form)
@page_deploy.route('/deploy_php',methods = ['GET', 'POST'])
def deploy_php():
    reload(MyForm)
    form = MyForm.MyForm_deploy_php()
    try:
        if form.submit_produce.data:
            Info = form.select_produce.data.strip()
            Ver = form.ver_produce.data.strip()
            Type = '1'
        elif form.submit_test.data:
            Info = form.select_test.data.strip()
            Ver = form.ver_test.data.strip()
            Type = '2'
        else:
            return render_template('deploy_php.html', form=form)
        assert Info, '服务器选择不能为空!'
        Info = Info.split(':')
        user = Info[1]
        ip = Info[0]
        db = db_op.php_list
        val = db.query.filter(and_(db.ip == ip,db.type == Type)).all()
        if val:
            flash('{0}的PHP环境已存在!'.format(ip))
        else:
            os.system('/usr/bin/wget -P /tmp/ http://172.16.16.160/dw/lnmp/lnmp_{0}.tgz'.format(Ver))
            Ssh = SSH.ssh(user, ip)
            Ssh.Scp('/tmp/lnmp_{0}.tgz'.format(Ver),'/home/work/lnmp_{0}.tgz'.format(Ver))
            os.system('/bin/rm -f /tmp/lnmp_{0}.tgz'.format(Ver))
            cmds = ['/bin/rm -rf /home/work/local',
                    'cd /home/work && /bin/tar -zxvf lnmp_{0}.tgz'.format(Ver),
                    '/bin/rm -f /home/work/lnmp_{0}.tgz'.format(Ver),
                    '/usr/bin/pkill -9 {php,nginx}',
                    '/home/work/local/php/sbin/php-fpm',
                    '/home/work/local/nginx/sbin/nginx']
            for cmd in cmds:
                Ssh.Run(cmd)
            Ssh.Close()
            #修改资源池表
            db = db_op.server_pool
            db.query.filter(and_(db.user == user, db.ip == ip)).update({db.status: '1'})
            db_op.DB.session.commit()
            flash('PHP环境在{0}部署成功,NGINX虚拟主机部署后可正常访问!'.format(ip))
    except Exception as e:
        flash(e)
    return render_template('deploy_php.html', form=form)
@page_haproxy_reload.route('/haproxy_reload')
@page_haproxy_reload.route('/haproxy_reload/<Type>')
def haproxy_reload(Type=None):
    if Type:
        if Type == 'internet':
            URL = "https://"
        else:
            URL = "https://"
        f = requests.request('get', URL, timeout=10)
        Info = f.json()
        if 'result' in f.json():
            Info = f.json()['result']
        return render_template('qrcode.html', INFO=Info)
    return render_template('haproxy_reload.html')
@page_deploy.before_request
@check.login_required(grade=0)
def check_login(error=None):
    produce.Async_log(g.user, request.url)
@page_deploy.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
    db_idc.DB.session.remove()
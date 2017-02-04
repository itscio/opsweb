#-*- coding: utf-8 -*-
from flask import Blueprint,redirect,url_for,render_template,render_template_string,g,request
from sqlalchemy import func,desc ,and_
import redis
from Modules import check,db_idc,loging,MyForm,produce,Mysql
import __init__
app = __init__.app
page_mysql = Blueprint('sql_app',__name__)
page_mysql_op = Blueprint('sql_app_op',__name__)
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
Redis = redis.StrictRedis(host=redis_host, port=redis_port)
@page_mysql.route('/mysql',methods = ['GET', 'POST'])
def mysqldb():
    try:
        t=('主库','端口','数据库','从库')
        db = db_idc.idc_mysqldb
        master_val = db.query.with_entities(db.ip,db.port,db.db).filter(
            db_idc.idc_mysqldb.master == '是').all()
        master_val = [list(v) for v in master_val]
        slave_val = db.query.with_entities(db.ip,db.port,db.Master_Host,db.Master_Port).filter(db.slave == '是').all()
        slave_val = [list(v) for v in slave_val]
        val = []
        for i in xrange(len(master_val)):
            slave=[]
            for l in xrange(len(slave_val)):
                M_ip_port=master_val[i][0:2]
                S_ip_port=slave_val[l][2:]
                if M_ip_port == S_ip_port:
                    slave_info = ':'.join(slave_val[l][0:2])
                    slave.append(slave_info)
            info=master_val[i]
            info.append(slave)
            val.append(info)
        return render_template('mysqldb.html',values=val,tables=t)
    except Exception as e:
            loging.write(e)
            return render_template_string('获取数据错误!')

@page_mysql.route('/servers',methods = ['GET', 'POST'])
def servers():
    form = MyForm.MyForm_server()
    if form.submit.data:
        try:
            db = db_idc.idc_servers
            t=('机柜号','SN','服务器型号','操作系统','CPU核数','内存','磁盘大小','ip','公司部门','使用状态','部署应用','备注')
            ts = form.text.data.strip().splitlines()
            ts = set(ts)
            va = []
            for vv in ts:
                if form.select.data=='ip':
                    val = db.query.filter(db.ip == vv).all()
                elif form.select.data=='cid':
                    val = db.query.filter(db.cid == vv).all()
                elif form.select.data=='sn':
                    val = db.query.filter(db.sn == vv).all()
                elif form.select.data=='deparment':
                    val = db.query.filter(db.department == vv).all()
                elif form.select.data=='status':
                    val = db.query.filter(db.status == vv).all()
                else:
                    return redirect(url_for('mysql.servers'))
                v = [str(i).encode('UTF-8').split(',') for i in val if i]
                va.append(v)
            return render_template('server_show.html',values=va,tables=t)
        except Exception as e:
            loging.write(e)
            return render_template_string('获取数据错误!')
    return render_template('server.html',form=form)

@page_mysql.route('/app',methods = ['GET', 'POST'])
def app():
    form = MyForm.MyForm_app()
    if form.submit.data:
        try:
            ts = form.text.data.strip().splitlines()
            ts = set(ts)
            t=('ip','账号','应用部署','域名')
            va=[]
            for vv in ts:
                if form.select.data=='ip':
                    val = db_idc.idc_app.query.filter(db_idc.idc_app.ip == vv).all()
                elif form.select.data=='app':
                    val = db_idc.idc_app.query.filter(db_idc.idc_app.appName == vv).all()
                elif form.select.data=='domain':
                    val = db_idc.idc_app.query.filter(db_idc.idc_app.domainName == vv).all()
                else:
                    return redirect(url_for('mysql.app'))
                v = [str(v).encode('UTF-8').split(',') for v in val if v]
                if v:
                    va.append(v)
            return render_template('user_show.html',values=va,tables=t)
        except Exception as e:
            loging.write(e)
            return render_template_string('获取数据错误!')
    return render_template('app.html',form=form)

@page_mysql.route('/twemproxy')
def twemproxy():
    try:
        t=('代理TYPE','代理GROUP','后端IP','后端PORT','DB','KEYS','备注')
        val = db_idc.idc_twemproxy.query.order_by(db_idc.idc_twemproxy.serviceGroup).all()
        v = [str(v).encode('UTF-8').split(',') for v in val if v]
        return render_template('twemproxy.html',values=v,tables=t)
    except Exception as e:
        loging.write(e)
        return render_template_string('获取数据错误!')

@page_mysql.route('/kestrel')
def kestrel():
    try:
        db = db_idc.idc_kestrel
        t=('IP','PORT','KEY','ITEMS')
        val = db.query.order_by(desc(db.kestrel_num)).all()
        v = [str(v).encode('UTF-8').split(',') for v in val]
        return render_template('kestrel.html',values=v,tables=t)
    except Exception as e:
        loging.write(e)
        return render_template_string('获取数据错误!')
        
@page_mysql.route('/tables',methods = ['GET', 'POST'])
def tables():
    form = MyForm.MyForm_input()
    if form.submit.data:
        try:
            ts = form.text.data.strip().splitlines()
            db_name = form.text2.data.strip()
            if ts and db_name:
                ts = set(ts)
                tt=('ip','port','数据库','表名','引擎','表行数','编码','版本')
                vv=[]
                Indexs = []
                INDEXS = []
                db = db_idc.idc_tableinfo
                for t_name in ts:
                    val = db.query.filter(and_(db.database_name == db_name,db.table_name == t_name)).all()
                    if val:
                        v = [str(v).encode('UTF-8').split(',') for v in val if v]
                        vv.append(v)
                        v = v[0]
                        cmds = ("show create table %s;" %v[3],"show index from %s;" %v[3])
                        for cmd in cmds:
                            Indexs.append(Mysql.Query_sql(v[0],v[1],v[2],cmd))
                    else:
                        return render_template_string('没有找到库{0}或者表{1}!'.format(db_name,t_name))
                for index in Indexs:
                    INDEX = []
                    for info in index:
                        info = [str(i).encode('UTF-8') for i in info]
                        INDEX.append(info)
                    INDEXS.append(INDEX)
                return render_template('tables_show.html',values=vv,tables=tt,INDEXS=INDEXS)
        except Exception as e:
            loging.write(e)
            return render_template_string('获取数据错误!')
    return render_template('tables.html',form=form)

@page_mysql.before_request
@check.login_required(grade=2)
def check_login(error=None):
    produce.Async_log(g.user, request.url)

@page_mysql.teardown_request
def db_remove(error=None):
    db_idc.DB.session.remove()

@page_mysql_op.route('/network')
def network():
    try:
        t=('机柜号','设备型号','ip','使用状态','备注')
        val = db_idc.idc_networks.query.all()
        v = [str(v).encode('UTF-8').split(',') for v in val if v]
        return render_template('mysql.html',values=v,tables=t)
    except Exception as e:
        loging.write(e)
        return render_template_string('获取数据错误!')

@page_mysql_op.route('/rack')
def rack():
    try:
        t=('机柜','服务器数量')
        db = db_idc.idc_servers
        val = db.query.with_entities(db.cid,func.count(db.cid)).group_by(db.cid).order_by(func.count(db.cid)).all()
        return render_template('mysql.html',values=val,tables=t)
    except Exception as e:
        loging.write(e)
        return render_template_string('获取数据错误!')

@page_mysql_op.route('/store')
def store():
    try:
        t=('机柜','型号','IP','公司部门','使用状态','备注')
        val = db_idc.idc_store.query.all()
        v = [str(v).encode('UTF-8').split(',') for v in val if v]
        return render_template('mysql.html',values=v,tables=t)
    except Exception as e:
        loging.write(e)
        return render_template_string('获取数据错误!')

@page_mysql_op.before_request
@check.login_required(grade=0)
def check_login(error=None):
    produce.Async_log(g.user, request.url)
@page_mysql_op.teardown_request
def db_remove(error=None):
    db_idc.DB.session.remove()
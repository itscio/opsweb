#-*- coding: utf-8 -*-
from flask import Blueprint,render_template,g,request,flash
from sqlalchemy import and_
import redis
from Modules import check,db_idc,loging,produce,Mysql
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from influxdb import InfluxDBClient
import datetime
from pyecharts import Line
from  collections import OrderedDict
app = Flask(__name__)
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/sql.conf')
logging = loging.Error()
DB = SQLAlchemy(app)
page_Assets = Blueprint('Assets',__name__)
page_mysql_info = Blueprint('mysql_info',__name__)
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
Redis = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
MYSQL_HOST = app.config.get('MYSQL_HOST')
MYSQL_PORT = app.config.get('MYSQL_PORT')
MYSQL_USER = app.config.get('MYSQL_USER')
MYSQL_PW = app.config.get('MYSQL_PASSWORD')
MYSQL_INFO_USER = app.config.get('MYSQL_INFO_USER')
MYSQL_INFO_PW = app.config.get('MYSQL_INFO_PASSWORD')
influxdb_host = app.config.get('INFLUXDB_HOST')
influxdb_port = app.config.get('INFLUXDB_PORT')
influxdb_user = app.config.get('INFLUXDB_USER')
influxdb_pw = app.config.get('INFLUXDB_PASSWORD')
influxdb_db = app.config.get('INFLUXDB_DB')
@page_mysql_info.route('/mysql',methods = ['GET', 'POST'])
def mysqldb():
    try:
        t=('主库','端口','数据库','从库')
        db = db_idc.idc_mysqldb
        master_val = db.query.with_entities(db.ip,db.port,db.db).filter(db.master == '是').all()
        master_val = [list(v) for v in master_val]
        slave_val = db.query.with_entities(db.ip,db.port,db.Master_Host,db.Master_Port).filter(db.slave == '是').all()
        slave_val = [list(v) for v in slave_val]
        values = []
        for i in range(len(master_val)):
            slave=[]
            for l in range(len(slave_val)):
                M_ip_port=[str(info) for info in master_val[i][0:2]]
                S_ip_port=[str(info) for info in slave_val[l][2:]]
                if M_ip_port == S_ip_port:
                    slave_info = ':'.join([str(info) for info in slave_val[l][0:2]])
                    slave.append(slave_info)
            infos=master_val[i]
            infos.append(slave)
            values.append(infos)
        return render_template('mysqldb.html',values=values,tables=t)
    except Exception as e:
        logging.error(e)
        flash('获取数据错误!',"error")
        return render_template('Message.html')
        
@page_mysql_info.route('/tables/<db_name>')
@page_mysql_info.route('/tables/<host_info>/<db_name>/<table_name>')
def tables(db_name=None,table_name=None,host_info=None):
    table_infos = {}
    tb_index = ('Non_unique', 'Key_name', 'Seq_in_index', 'Column_name', 'Collation', 'Cardinality', 'Sub_part', 'Packed',
    'Null', 'Index_type', 'Comment', 'Index_comment')
    tb_columns = ('Field','Type','Collation','Null','Key','Default','Extra','Comment')
    tables = ('ip', 'port', '主从', '数据库', '表名', '引擎', '行数', '大小', '编码', '版本')
    Indexs = None
    values = None
    Columns = None
    create_table = None
    #数据库表列表
    if db_name and not table_name and not host_info:
        try:
            db_tableinfo = db_idc.idc_tableinfo
            db_mysqldb = db_idc.idc_mysqldb
            values = db_tableinfo.query.with_entities(db_tableinfo.ip,db_tableinfo.port,db_tableinfo.database_name,
                                                      db_tableinfo.table_name,db_tableinfo.Engine_name,db_tableinfo.Rows,db_tableinfo.size,db_tableinfo.Charset
                                                      ,db_tableinfo.version).filter(db_tableinfo.database_name == db_name).all()
            if values:
                values = [list(v) for v in values]
                ips = [val[:2] for val in values]
                for info in ips:
                    ip,port = info
                    ms_infos = db_mysqldb.query.with_entities(db_mysqldb.master,db_mysqldb.slave).filter(and_(db_mysqldb.ip==ip,db_mysqldb.port==port)).all()
                    if ms_infos[0][0] == '是':
                        table_infos['%s:%s' %(ip,port)] = '主库'
                    elif ms_infos[0][1] == '是':
                        table_infos['%s:%s' %(ip,port)] = '从库'
                    else:
                        table_infos['%s:%s' % (ip, port)] = '未知'
        except Exception as e:
            logging.error(e)
    #表结构和索引详情
    if table_name and host_info and db_name:
        try:
            ip,app_port = host_info.split(':')
            INFO_MySql = Mysql.MYSQL(MYSQL_INFO_USER, MYSQL_INFO_PW,ip,app_port, 'mysql')
            Columns= INFO_MySql.Run("SHOW full COLUMNS FROM %s.%s;" %(db_name,table_name))
            Indexs = INFO_MySql.Run("SHOW INDEX FROM %s.%s;" %(db_name,table_name))
            create_table = INFO_MySql.Run("SHOW CREATE TABLE %s.%s;" % (db_name, table_name))
            create_table = create_table[0][1]
        except Exception as e:
            logging.error(e)
        finally:
            INFO_MySql.Close
    return render_template('tables_show.html', values=values, tables=tables, db_name=db_name, table_name=table_name,
                               table_infos=table_infos,Columns=Columns,tb_columns=tb_columns,tb_index=tb_index,Indexs=Indexs,create_table=create_table)

@page_mysql_info.route('/mysql_status')
@page_mysql_info.route('/mysql_status/<ip_app_port>')
def mysql_status(ip_app_port=None):
    if  ip_app_port:
        Lines = []
        INFOS = OrderedDict()
        nt = datetime.datetime.now()
        sat = nt.strftime('%Y-%m-%dT00:00:00Z')
        snt = nt.strftime('%Y-%m-%dT%H:%M:%SZ')
        ip,app_port = ip_app_port.split(':')
        Influx_cli = InfluxDBClient(influxdb_host, influxdb_port, influxdb_user, influxdb_pw, 'mysqld_status')
        cmd = "select * from " + ' "performance" ' + "WHERE time >= '%s' and time <= '%s' and ip='%s' and port='%s'" % (sat,snt, ip, app_port)
        result = Influx_cli.query(cmd)
        infos = [infos for infos in result.get_points() if infos]
        if infos:
            for values in infos:
                time = values['time'].split('T')[-1].replace('Z','')
                vals = {'QPS':values['QPS'],'TPS':values['TPS'],'R/W':values['R/W'],'S/Q':values['S/Q'],'Bytes_r':values['Bytes_r'],'Bytes_s':values['Bytes_s'],'Connections':values['Connections']}
                INFOS[time] = vals
            #QPS统计
            line_attrs = [tt for tt in INFOS]
            line_vals = [float('%.2f'%INFOS[tt]['QPS']) for tt in line_attrs]
            line = Line('', width='110%',height='230px',title_pos='center',title_text_size=14)
            line.add('QPS', line_attrs, line_vals, is_toolbox_show=False, is_smooth=True,
                     mark_point=["max", "min"], mark_point_symbolsize=80, legend_pos='center', legend_top='top',
                     is_datazoom_show=True,
                     datazoom_range=[v for v in range(100, 1)], datazoom_type='both', xaxis_rotate=5)
            # TPS统计
            line_attrs = [tt for tt in INFOS]
            line_vals = [float('%.2f'%INFOS[tt]['TPS']) for tt in line_attrs]
            line.add('TPS', line_attrs, line_vals, is_toolbox_show=False, is_smooth=True,
                     mark_point=["max", "min"], mark_point_symbolsize=80, legend_pos='center', legend_top='top',
                     is_datazoom_show=True,
                     datazoom_range=[v for v in range(100, 1)], datazoom_type='both', xaxis_rotate=5)
            Lines.append(line)
            # R/W统计
            line_attrs = [tt for tt in INFOS]
            line_vals = [float('%.2f' % INFOS[tt]['R/W']) for tt in line_attrs]
            line = Line('', width='110%', height='230px', title_pos='center', title_text_size=14)
            line.add('读写比', line_attrs, line_vals, is_toolbox_show=False, is_smooth=True,
                     mark_point=["max", "min"], mark_point_symbolsize=80, legend_pos='center', legend_top='top',
                     is_datazoom_show=True,
                     datazoom_range=[v for v in range(100, 1)], datazoom_type='both', xaxis_rotate=5,yaxis_formatter='%',is_random=True)
            # S/Q统计
            line_attrs = [tt for tt in INFOS]
            line_vals = [float('%.2f' % INFOS[tt]['S/Q']) for tt in line_attrs]
            line.add('慢查询占比', line_attrs, line_vals, is_toolbox_show=False, is_smooth=True,
                     mark_point=["max", "min"], mark_point_symbolsize=80, legend_pos='center', legend_top='top',
                     is_datazoom_show=True,
                     datazoom_range=[v for v in range(100, 1)], datazoom_type='both', xaxis_rotate=5,yaxis_formatter='%',is_random=True)
            Lines.append(line)
            # Bytes_r统计
            line_attrs = [tt for tt in INFOS]
            line_vals = [float('%.2f' %(float(INFOS[tt]['Bytes_r'])/3000)) for tt in line_attrs]
            line = Line('', width='110%', height='230px', title_pos='center', title_text_size=14)
            line.add('接收流量', line_attrs, line_vals, is_toolbox_show=False, is_smooth=True,
                     mark_point=["max", "min"], mark_point_symbolsize=80, legend_pos='center', legend_top='top',
                     is_datazoom_show=True,
                     datazoom_range=[v for v in range(100, 1)], datazoom_type='both', xaxis_rotate=5,
                     yaxis_formatter='kb/s',is_random=True)
            # Bytes_s统计
            line_attrs = [tt for tt in INFOS]
            line_vals = [float('%.2f' % (float(INFOS[tt]['Bytes_s'])/3000)) for tt in line_attrs]
            line.add('发送流量', line_attrs, line_vals, is_toolbox_show=False, is_smooth=True,
                     mark_point=["max", "min"], mark_point_symbolsize=80, legend_pos='center', legend_top='top',
                     is_datazoom_show=True,
                     datazoom_range=[v for v in range(100, 1)], datazoom_type='both', xaxis_rotate=5,
                     yaxis_formatter='kb/s',is_random=True)
            Lines.append(line)
            # Connections统计
            line_attrs = [tt for tt in INFOS]
            line_vals = [INFOS[tt]['Connections'] for tt in line_attrs]
            line = Line('', width='110%', height='230px', title_pos='center', title_text_size=14)
            line.add('活动连接数', line_attrs, line_vals, is_toolbox_show=False, is_smooth=True,
                     mark_point=["max", "min"], mark_point_symbolsize=80, legend_pos='center', legend_top='top',
                     is_datazoom_show=True,
                     datazoom_range=[v for v in range(100, 1)], datazoom_type='both', xaxis_rotate=5)
            Lines.append(line)
        return render_template('mysql_status.html',Lines=Lines,ip_app_port=ip_app_port)
    return render_template('dev.html')
@page_mysql_info.before_request
@check.login_required(grade=5)
def check_login(error=None):
    produce.Async_log(g.user, request.url)

@page_mysql_info.teardown_request
def db_remove(error=None):
    db_idc.DB.session.remove()
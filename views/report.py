#-*- coding: utf-8 -*-
from flask import Flask,Blueprint,request,render_template,g,redirect,url_for
from module import user_auth,db_op,db_idc,loging,MyForm,tools
from sqlalchemy import func,and_,desc
from pyecharts import Bar,Pie,Line
import redis
from functools import reduce
from flask_sqlalchemy import SQLAlchemy
import datetime,time
app = Flask(__name__)
app.config.from_pyfile('../conf/redis.conf')
DB = SQLAlchemy(app)
logging = loging.Error()
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
RC = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
redis_data = app.config.get('REDIS_DATA')
RC_CLUSTER = redis.StrictRedis(host=redis_data, port=redis_port,decode_responses=True)
page_report = Blueprint('report', __name__)
@page_report.route('/resource_report')
def resource_report():
    try:
        form =  MyForm.FormResourceReport()
        days = tools.http_args(request,'days')
        date = datetime.datetime.now()
        db_server = db_idc.idc_servers
        if days:
            days = int(days)
            update_date = date - datetime.timedelta(days=days)
        else:
            days = 30
            update_date = date - datetime.timedelta(days=30)
        datazoom = True
        if days == 30:
            datazoom = False
        Bars = {}
        titles = {30:'近一个月',90:'近三个月',180:'近六个月',360:'近一年内'}
        db_third = db_idc.third_resource
        db_project = db_op.project_list
        vals = db_project.query.with_entities(db_project.update_date, func.count(db_project.update_date)).filter(
            and_(db_project.resource == 'tomcat', db_project.update_date != '',db_project.update_date >=update_date)).group_by(db_project.update_date).all()
        if vals:
            attrs = [val[0] for val in vals]
            datas = [val[-1] for val in vals]
            tomcat_bar = Bar("tomcat(%s)" %titles[days], width='110%', height='100%', title_pos='center', title_text_size=14)
            tomcat_bar.add("", attrs, datas, is_label_show=True, is_toolbox_show=False, legend_orient='vertical',
                           legend_pos='right', xaxis_interval=0, is_random=True, xaxis_rotate=15, is_datazoom_show=datazoom,
                           datazoom_type='both')
            Bars['tomcat'] = tomcat_bar
        vals = db_third.query.with_entities(db_third.update_date,func.count(db_third.update_date)).filter(and_(db_third.resource_type=='redis',db_third.update_date != '',db_third.update_date >=update_date)).group_by(db_third.update_date).all()
        if vals:
            attrs = [val[0] for val in vals]
            datas = [val[-1] for val in vals]
            redis_bar = Bar("redis(%s)" %titles[days], width='110%', height='100%', title_pos='center', title_text_size=14)
            redis_bar.add("", attrs, datas, is_label_show=True, is_toolbox_show=False, legend_orient='vertical',legend_pos='right',
                          xaxis_interval=0,is_random=True,xaxis_rotate=15,is_datazoom_show=datazoom,datazoom_type='both')
            Bars['redis'] =redis_bar
        vals = db_third.query.with_entities(db_third.update_date, func.count(db_third.update_date)).filter(
            and_(db_third.resource_type == 'redis', db_third.update_date != '')).group_by(db_third.update_date).all()
        if vals:
            attrs = [val[0] for val in vals]
            datas = [val[-1] for val in vals]
            mysql_bar = Bar("mysql(%s)" %titles[days], width='110%', height='100%', title_pos='center', title_text_size=14)
            mysql_bar.add("", attrs, datas, is_label_show=True, is_toolbox_show=False, legend_orient='vertical',
                          legend_pos='right', xaxis_interval=0, is_random=True, xaxis_rotate=15, is_datazoom_show=datazoom,
                          datazoom_type='both')
            Bars['mysql'] =mysql_bar
        vals = db_third.query.with_entities(db_third.update_date, func.count(db_third.update_date)).filter(
            and_(db_third.resource_type == 'redis', db_third.update_date != '')).group_by(db_third.update_date).all()
        if vals:
            attrs = [val[0] for val in vals]
            datas = [val[-1] for val in vals]
            nginx_bar = Bar("nginx(%s)" %titles[days], width='110%', height='100%', title_pos='center', title_text_size=14)
            nginx_bar.add("", attrs, datas, is_label_show=True, is_toolbox_show=False, legend_orient='vertical',
                          legend_pos='right', xaxis_interval=0, is_random=True, xaxis_rotate=15, is_datazoom_show=datazoom,
                          datazoom_type='both')
            Bars['nginx'] =nginx_bar
        try:
            td = time.strftime("%Y-%m-%d", time.localtime())
            std = datetime.datetime.now() - datetime.timedelta(days=180)
            std = std.strftime("%Y-%m-%d")
            if RC.exists('op_web_vm_vales_%s' % td) and RC.exists('op_web_py_vales_%s' % td):
                vm_vals = eval(RC.get('op_web_vm_vales_%s' % td))
                py_vals = eval(RC.get('op_web_py_vales_%s' % td))
            else:
                vm_vals = db_server.query.with_entities(db_server.purch_date, func.count(db_server.purch_date)).filter(
                    and_(db_server.host_type == 'vm', db_server.purch_date > std)).group_by(db_server.purch_date).all()
                RC.set('op_web_vm_vales_%s' % td, vm_vals)
                RC.expire('op_web_vm_vales_%s', 86400)
                py_vals = db_server.query.with_entities(db_server.purch_date, func.count(db_server.purch_date)).filter(
                    and_(db_server.host_type == 'physical', db_server.purch_date > std)).group_by(
                    db_server.purch_date).all()
                RC.set('op_web_py_vales_%s' % td, py_vals)
                RC.expire('op_web_py_vales_%s', 86400)
        except Exception as e:
            logging.error(e)
        server_bar = Bar("近6个月新增服务器数量", title_pos='center', title_text_size=12, width='110%', height='230px')
        try:
            attrs = sorted(set([val[0] for val in vm_vals if val] + [val[0] for val in py_vals if val]))
            vm_vals = {val[0]: val[1] for val in vm_vals}
            py_vals = {val[0]: val[1] for val in py_vals}
            for attr in attrs:
                if attr not in vm_vals:
                    vm_vals[attr] = 0
                if attr not in py_vals:
                    py_vals[attr] = 0
            vm_vals = sorted(vm_vals.items(), key=lambda item: item[0])
            vm_vals = [val[1] for val in vm_vals]
            py_vals = sorted(py_vals.items(), key=lambda item: item[0])
            py_vals = [val[1] for val in py_vals]
            attrs = ['-'.join(val.split('-')[1:]) for val in attrs]
            vm_counts = reduce(lambda x, y: x + y, vm_vals)
            server_bar.add('虚拟机%s台' % vm_counts, attrs, vm_vals, is_label_show=True, is_toolbox_show=False,
                    xaxis_interval=0, xaxis_rotate=25, legend_pos='70%')
            py_counts = reduce(lambda x, y: x + y, py_vals)
            server_bar.add('物理机%s台' % py_counts, attrs, py_vals, is_label_show=True, is_toolbox_show=False,
                    xaxis_interval=0, xaxis_rotate=25, legend_pos='70%')
        except Exception as e:
            logging.error(e)
        return render_template('resource_report.html', Bars=Bars, form=form, days=days, server_bar=server_bar)
    except Exception as e:
        logging.error(e)
        return redirect(url_for('error'))


@page_report.route('/server_used')
def server_used():
    try:
        PIES = []
        INFOS = []
        ATTRS = []
        free_list = []
        host_count = 0
        try:
            if RC_CLUSTER.exists('op_zabbix_server_load_top'):
                dict_load = eval(RC_CLUSTER.get('op_zabbix_server_load_top'))
                bar_load = Bar("线上服务器cpu使用率TOP20", width='110%', height='100%', title_pos='center', title_text_size=14)
                attrs = [val[0] for val in dict_load]
                vals = [int(val[1]) for val in dict_load]
                ATTRS.extend(attrs)
                bar_load.add("", attrs,vals, is_label_show=True, is_toolbox_show=False, legend_orient='vertical',
                            legend_pos='right', xaxis_interval=0, is_random=True,yaxis_formatter='%',xaxis_rotate=15)
                INFOS.append(bar_load)
            if RC_CLUSTER.exists('op_zabbix_server_mem_top'):
                dict_mem = eval(RC_CLUSTER.get('op_zabbix_server_mem_top'))
                bar_mem = Bar("线上服务器内存使用率TOP20", width='110%', height='100%', title_pos='center', title_text_size=14)
                attrs = [val[0] for val in dict_mem]
                vals = [int(val[1]) for val in dict_mem]
                ATTRS.extend(attrs)
                bar_mem.add("", attrs,vals, is_label_show=True, is_toolbox_show=False, legend_orient='vertical',
                             legend_pos='right', xaxis_interval=0, is_random=True,yaxis_formatter='%',xaxis_rotate=15)
                INFOS.append(bar_mem)
            if RC_CLUSTER.exists('op_zabbix_server_openfile_top'):
                dict_openfile = eval(RC_CLUSTER.get('op_zabbix_server_openfile_top'))
                bar_openfile = Bar("线上服务器openfile值TOP20", width='110%', height='100%', title_pos='center', title_text_size=14)
                attrs = [val[0] for val in dict_openfile]
                vals = [int(val[1]) for val in dict_openfile]
                ATTRS.extend(attrs)
                bar_openfile.add("", attrs, vals, is_label_show=True, is_toolbox_show=False, legend_orient='vertical',
                            legend_pos='right', xaxis_interval=0, is_random=True,xaxis_rotate=15)
                INFOS.append(bar_openfile)
        except Exception as e:
            logging.error(e)
        try:
            free_list = []
            if RC_CLUSTER.exists('op_zabbix_free_servers'):
                free_servers = eval(RC_CLUSTER.get('op_zabbix_free_servers'))
                free_servers = [host for host in free_servers]
                free_servers.sort()
                # 导出服务器主机列表
                tables = ['主机名']
                search_key = 'search_results_%s' % g.token
                export_values = [[host] for host in free_servers]
                export_values.insert(0, tables)
                RC.set(search_key, export_values)
                host_count = len(free_servers)
                # 服务器列表展示
                free_list = [free_servers[i*5:(i+1)*5] for i in range(len(free_servers)//5)]
        except Exception as e:
            logging.error(e)
        if ATTRS:
            db_project = db_op.project_list
            db_third = db_idc.third_resource
            db_server = db_idc.idc_servers
            db_project_third = db_op.project_third
            hosts = db_server.query.with_entities(db_server.ip).filter(db_server.hostname.in_(tuple(set(ATTRS)))).all()
            if hosts:
                try:
                    # 应用服务占比
                    hosts = tuple([host[0] for host in hosts])
                    selfs = db_project.query.with_entities(db_project.resource, func.count(db_project.resource)).filter(db_project.ip.in_(hosts)).group_by(db_project.resource).all()
                    thirds = db_third.query.with_entities(db_third.resource_type,func.count(db_third.resource_type)).filter(db_third.ip.in_(hosts)).group_by(db_third.resource_type).all()
                    vals = selfs+thirds
                    if vals:
                        pie_app = Pie("TOP20应用服务占比", width='100%', height='100%', title_pos='center',title_text_size=14)
                        attrs = [val[0] for val in vals]
                        vals = [int(val[1]) for val in vals]
                        pie_app.add("", attrs, vals, is_label_show=True, is_toolbox_show=False,is_legend_show  = False, xaxis_interval=0, is_random=True)
                        PIES.append(pie_app)
                    # 线上项目占比
                    self_id = db_project.query.with_entities(db_project.id).filter(db_project.ip.in_(hosts)).all()
                    third_id = db_third.query.with_entities(db_third.id).filter(db_third.ip.in_(hosts)).all()
                    ids = self_id+third_id
                    ids = tuple([id[0] for id in ids])
                    vals = db_project_third.query.with_entities(db_project_third.project,func.count(db_project_third.project)).filter(and_(db_project_third.project_id.in_(ids),db_project_third.third_id.in_(ids))).group_by(db_project_third.project).all()
                    if vals:
                        pie_project = Pie("TOP20线上项目占比", width='100%', height='100%', title_pos='center', title_text_size=14)
                        attrs = [val[0] for val in vals]
                        vals = [int(val[1]) for val in vals]
                        pie_project.add("", attrs, vals, is_label_show=True, is_toolbox_show=False, legend_orient='vertical',
                                    legend_pos='left', xaxis_interval=0, is_random=True)
                        PIES.append(pie_project)
                except Exception as e:
                    logging.error(e)
        return render_template('server_used.html', INFOS=INFOS, PIES=PIES, host_count=host_count, free_list=free_list)
    except Exception as e:
        logging.error(e)
        return redirect(url_for('error'))

@page_report.route('/alarm_report')
def alarm_report():
    try:
        INFOS = []
        total_key = 'op_totals_alarms_tmp'
        def counts_alarm(key,total_key = None):
            vals = []
            for i in range(7):
                count_key = 'op_counts_alarms_tmp'
                data_now = datetime.datetime.now() - datetime.timedelta(days=i)
                dd = data_now.strftime('%Y-%m-%d')
                alarm_count_key = '%s_%s' %(key,dd)
                if RC_CLUSTER.exists(alarm_count_key):
                    vals = RC_CLUSTER.hgetall(alarm_count_key)
                    vals = sorted(vals.items(), key=lambda item: int(item[1]))
                    for val in vals:
                        RC_CLUSTER.hincrby(count_key,val[0],val[1])
                        if total_key:
                            RC_CLUSTER.hincrby(total_key,dd, val[1])
            if RC_CLUSTER.exists(count_key):
                vals = RC_CLUSTER.hgetall(count_key)
                RC_CLUSTER.delete(count_key)
                vals = sorted(vals.items(), key=lambda item: int(item[1]),reverse=True)
            if len(vals) >10:
                return vals[:10]
            else:
                return vals
        alarm_count = counts_alarm('op_business_alarm_count',total_key=total_key)
        vals = counts_alarm('op_business_alarm_perf')
        if vals:
            pie_perf = Pie("近7天报警接口性能统计TOP10", width='100%', height='100%', title_pos='center', title_text_size=14)
            attrs = [val[0] for val in vals]
            vals = [int(val[1]) for val in vals]
            pie_perf.add("", attrs, vals, is_label_show=True, is_toolbox_show=False,legend_orient='vertical',legend_pos='left', xaxis_interval=0, is_random=True,rosetype = 'area')
            INFOS.append(pie_perf)
        vals = counts_alarm('op_business_alarm_busi')
        if vals:
            pie_busi = Pie("近7天报警业务归属统计TOP10", width='100%', height='100%', title_pos='center', title_text_size=14)
            attrs = [val[0] for val in vals]
            vals = [int(val[1]) for val in vals]
            pie_busi.add("", attrs, vals, is_label_show=True, is_toolbox_show=False,legend_orient='vertical',legend_pos='left',xaxis_interval=0, is_random=True,rosetype = 'radius',radius=[35, 75])
            INFOS.append(pie_busi)
        if RC_CLUSTER.exists(total_key):
            vals = RC_CLUSTER.hgetall(total_key)
            vals = sorted(vals.items(), key=lambda item: item[0],reverse=True)
            RC_CLUSTER.delete(total_key)
            line = Line("近7天业务接口每日报警统计", width='100%', height='100%', title_pos='center', title_text_size=14)
            attrs = [val[0] for val in vals]
            vals = [int(val[1]) for val in vals]
            line.add("", attrs, vals, is_label_show=True, is_toolbox_show=False,is_legend_show  = False, xaxis_interval=0, is_random=True)
            INFOS.append(line)
    except Exception as e:
        logging.error(e)
        return redirect(url_for('error'))
    return render_template('alarm_report.html',INFOS=INFOS,alarm_count=alarm_count)

@page_report.route('/work_order_report_show')
def work_order_report_show():
    form = MyForm.MyFormWorkOrderReport()
    tm = datetime.datetime.now() - datetime.timedelta(days=90)
    start_time = tm.strftime('%Y-%m-%d')
    end_time = time.strftime('%Y-%m-%d', time.localtime())
    return render_template('work_order_report_show.html',form=form,tt=(start_time,end_time))

@page_report.route('/work_order_report')
@page_report.route('/work_order_report/<start_time>/<end_time>/<source>')
def work_order_report(start_time=None,end_time=None,source='all_order'):
    INFOS = []
    db_sso = db_op.user_sso
    db_work_order = db_op.work_order
    dm_key = 'op_work_order_report_dm'
    stat_key = 'op_work_order_report_status'
    dep_key = 'op_work_order_report_department'
    if not start_time or not end_time:
        tm = datetime.datetime.now() - datetime.timedelta(days=7)
        start_time = tm.strftime('%Y-%m-%d')
        end_time = time.strftime('%Y-%m-%d',time.localtime())
    try:
        infos = db_sso.query.with_entities(db_sso.dingunionid, db_sso.department,db_sso.realName).all()
        departments = {info[0]: info[1] for info in infos}
        users = {info[0]: info[-1] for info in infos}
        #统计运维工单状态
        try:
            if source != 'all_order':
                vals = db_work_order.query.with_entities(db_work_order.status,func.count(db_work_order.status)).filter(and_(
                db_work_order.source == source,db_work_order.date >=start_time,db_work_order.date<=end_time)).group_by(db_work_order.status).all()
            else:
                vals = db_work_order.query.with_entities(db_work_order.status,func.count(db_work_order.status)).filter(and_(
                    db_work_order.date >=start_time,db_work_order.date<=end_time)).group_by(db_work_order.status).all()
            pie = Pie("运维工单状态统计", width='100%', height='100%', title_pos='center', title_text_size=14)
            pie_vals = [val[0] for val in vals]
            pie_counts = [int(val[1]) for val in vals]
            pie.add("", pie_vals, pie_counts, is_label_show=True, is_toolbox_show=False, legend_orient='vertical',
                           legend_pos='right',radius=[1, 65], is_random=True)
            INFOS.append(pie)
        except Exception as e:
            logging.error(e)
        #统计月度工单数量及受理率
        try:
            if source != 'all_order':
                vals = db_work_order.query.with_entities(db_work_order.date,db_work_order.status).filter(and_(
                db_work_order.source == source,db_work_order.date >=start_time,db_work_order.date<=end_time)).all()
            else:
                vals = db_work_order.query.with_entities(db_work_order.date, db_work_order.status).filter(and_(
                    db_work_order.date >= start_time,db_work_order.date <= end_time)).all()
            if vals:
                for val in vals:
                    dm,status = val
                    dm = dm.split('-')[1]
                    RC.hincrby(dm_key,dm)
                    if status not in ('未受理', '未审核'):
                        RC.hincrby(stat_key,dm)
            line = Line("月度工单数量及受理率统计", width='100%', height='100%', title_pos='center',title_text_size=14)
            total_vals = RC.hgetall(dm_key)
            vals = sorted(total_vals.items(), key=lambda item: int(item[0]))
            dm_vals = [val[0] for val in vals]
            dm_counts = [int(val[1]) for val in vals]
            line.add('工单数量', dm_vals, dm_counts, is_label_show=True, is_toolbox_show=False,
                         legend_orient='vertical', legend_pos='right', xaxis_interval=0, is_random=True, xaxis_rotate=15)
            stat_vals = RC.hgetall(stat_key)
            stat_counts = [round((float(stat_vals[val])/float(total_vals[val]))*100,1) for val in stat_vals]
            line.add('受理率', dm_vals, stat_counts, is_label_show=True, is_toolbox_show=False,
                         legend_orient='vertical', legend_pos='right', xaxis_interval=0, is_random=True, xaxis_rotate=15)
            RC.delete(stat_key)
            RC.delete(dm_key)
            INFOS.append(line)
        except Exception as e:
            logging.error(e)
        #工单申请数量部门排名
        try:
            if source != 'all_order':
                vals = db_work_order.query.with_entities(db_work_order.applicant).filter(and_(
                db_work_order.source == source,db_work_order.date >=start_time,db_work_order.date<=end_time)).all()
            else:
                vals = db_work_order.query.with_entities(db_work_order.applicant).filter(and_(
                db_work_order.date >=start_time,db_work_order.date<=end_time)).all()
            if vals:
                for val in vals:
                    RC.hincrby(dep_key,departments[val[0]])
            bar = Bar("部门提交工单统计", width='100%', height='100%', title_pos='center', title_text_size=14)
            vals = RC.hgetall(dep_key)
            dep_vals = [val for val in vals]
            dep_counts = [int(vals[val]) for val in vals]
            bar.add('', dep_vals, dep_counts, is_label_show=True, is_toolbox_show=False,
                         legend_orient='vertical', legend_pos='right', xaxis_interval=0, is_random=True, xaxis_rotate=15)
            RC.delete(dep_key)
            INFOS.append(bar)
        except Exception as e:
            logging.error(e)
        #工单申请数量个人排名
        try:
            if source != 'all_order':
                vals = db_work_order.query.with_entities(db_work_order.applicant,func.count(db_work_order.applicant)).filter(and_(
                db_work_order.source == source,db_work_order.date >=start_time,db_work_order.date<=end_time)).group_by(
                db_work_order.applicant).order_by(desc(func.count(db_work_order.applicant))).limit(15).all()
            else:
                vals = db_work_order.query.with_entities(db_work_order.applicant,
                                                         func.count(db_work_order.applicant)).filter(and_(
                    db_work_order.date >= start_time,db_work_order.date <= end_time)).group_by(
                    db_work_order.applicant).order_by(desc(func.count(db_work_order.applicant))).limit(15).all()
            vals = [list(val) for val in vals]
            for val in vals:
                val[0] = users[val[0]]
            bar = Bar("个人提交工单统计", width='100%', height='100%', title_pos='center', title_text_size=14)
            dep_vals = [val[0] for val in vals]
            dep_counts = [int(val[1]) for val in vals]
            bar.add('', dep_vals, dep_counts, is_label_show=True, is_toolbox_show=False,
                    legend_orient='vertical', legend_pos='right', xaxis_interval=0, is_random=True, xaxis_rotate=15)
            INFOS.append(bar)
        except Exception as e:
            logging.error(e)
    except Exception as e:
        logging.error(e)
    return render_template('work_order_report.html',INFOS=INFOS,tt=(start_time,end_time))

@page_report.before_request
@user_auth.login_required(grade=1)
def check_login(exception = None):
    tools.Async_log(g.user, request.url)

@page_report.teardown_request
def db_remove(error=None):
    db_idc.DB.session.remove()
    db_op.DB.session.remove()
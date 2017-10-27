#-*- coding: utf-8 -*-
from flask import Flask
import redis
from flask import Blueprint,request,render_template,g,flash
from Modules import produce,check ,MyForm,loging,main_info
from rediscluster import RedisCluster
def _RC_Run(key, port, action):
    Tpyes = dict(hash="RC.hgetall(key)", list="RC.lrange(key,0,-1)", string="RC.get(key)",
                 zset="RC.zrange(key,0,-1,withscores=True)", set="RC.smembers(key)")
    if port == 6379:
        app = Flask(__name__)
        app.config.from_pyfile('../conf/redis.conf')
        nodes = app.config.get('NODES_PRODUCE')
        RC = RedisCluster(startup_nodes=nodes, decode_responses=True)
    else:
        RC = redis.StrictRedis(host='redis.service.baihe', port=port)
    T = RC.type(key)
    if T == 'none':
        flash('存储数据:{0}'.format(T))
    else:
        if action == 'clear':
            RC.delete(key)
            flash('存储数据清除完毕!')
        return eval(Tpyes.get(T))
page_clear_redis=Blueprint('clear_redis',__name__)
@page_clear_redis.route('/clear_redis',methods = ['GET', 'POST'])
@main_info.main_info
def clear_redis():
    form = MyForm.MyForm_clear_redis()
    if form.submit.data:
        Keys = form.text.data.strip().splitlines()
        Keys = set(Keys)
        port = form.select_port.data
        action = form.select_action.data
        if Keys:
            for key in Keys:
                flash('获取Key:%s信息......'%key)
                vv = _RC_Run(key,port,action)
                flash('存储数据:{0}'.format(vv))
            return render_template('Message_static.html',Main_Infos=g.main_infos)
    return render_template('clear_redis.html',Main_Infos=g.main_infos,form = form)
@page_clear_redis.before_request
@check.login_required(grade=0)
def check_login(error=None):
    produce.Async_log(g.user, request.url)
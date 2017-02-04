#-*- coding: utf-8 -*-
from flask import Blueprint,render_template_string,render_template,g,request
from Modules import loging,check,produce
import pymongo
import __init__
app = __init__.app
page_mongodb_info=Blueprint('mongodb_info',__name__)
Host = app.config.get('MONGODB_HOST')
Port = app.config.get('MONGODB_PORT')
@page_mongodb_info.route('/mongodb')
def mongodb_info():
    try:
        def Mongo_cli(ip,port):
            client = pymongo.MongoClient(ip,port,socketTimeoutMS=3000)
            return client
        mongo_client = Mongo_cli(Host,int(Port))
        mongo_db = mongo_client.config
        shards = {}
        #获取shard信息
        for info in mongo_db.shards.find():
            host_infos = info['host'].split('/')[1]
            shard = [host_info.split(':') for host_info in host_infos.split(',')]
            New_shard = []
            for host_info in shard:
                ip, port = host_info
                Mclient = Mongo_cli(ip,int(port))
                #判断primary状态
                if Mclient.is_primary:
                    host_info.append('primary')
                else:
                    host_info.append('slave')
                New_shard.append(host_info)
            shards[info['_id']] = New_shard
    except Exception as e:
        loging.write(e)
        return  render_template_string('数据获取错误!')
    return render_template('mongodb_show.html', shards=shards)
@page_mongodb_info.before_request
@check.login_required(grade=2)
def check_login(error=None):
    produce.Async_log(g.user, request.url)
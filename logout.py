#-*- coding: utf-8 -*-
from flask import Blueprint,redirect,make_response,request,jsonify
from module import tools,user_auth
from xml.dom.minidom import parseString
from collections import defaultdict
import os
import redis
import time
import conf
app = conf.app
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
Redis = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
service_url = app.config.get('SERVICE_URL')
ENV = None
if os.path.exists('/etc/opweb.conf'):
    with open('/etc/opweb.conf','r') as f:
        ENV = f.read().strip()
if ENV:
    service_url = app.config.get('TEST_URL')
page_logout = Blueprint('logout',__name__)
@page_logout.route('/logout')
def logout():
    tm = time.strftime('%Y%m%d',time.localtime())
    dingId = Redis.get('OP_dingId_%s' % request.cookies.get('dingId'))
    if dingId:
        #清除用户计数
        Redis.srem('op_active_users_%s' %tm, dingId)
    #清除用户票据
    ticket = Redis.get('OP_ticket_%s' % request.cookies.get('ticket'))
    Redis.delete('OP_logout_ticket_%s' % ticket)
    timestamp = tools.timestamp(0)
    #在cas服务器上注销
    cas_client = user_auth.cas_logout()
    logout_url = cas_client.get_logout_url(service_url=service_url)
    app_resp = make_response(redirect(logout_url))
    #清除cookie
    for key in request.cookies:
        app_resp.set_cookie(key, expires=timestamp)
    return app_resp

@page_logout.route('/sso_logout',methods = ['POST'])
def sso_logout():
    result = defaultdict()
    try:
        vals = request.form
        if vals:
            # 获取用户票据
            xml_document = parseString(vals['logoutRequest'])
            for node in xml_document.getElementsByTagName('samlp:SessionIndex'):
                for child in node.childNodes:
                    if child.nodeType == child.TEXT_NODE:
                        result['session_index'] = str(child.nodeValue.strip())
        # 清除用户票据
        if result['session_index']:
            tm = time.strftime('%Y%m%d', time.localtime())
            dingId = Redis.get('OP_dingid_ticket_%s' % result['session_index'])
            if dingId:
                # 清除用户计数
                Redis.srem('op_active_users_%s' % tm, dingId)
            Redis.delete('OP_logout_ticket_%s' % result['session_index'])
            return jsonify({'results':'success'})
        return jsonify({'results': 'fail'})
    except Exception as e:
        return jsonify({'results': e})
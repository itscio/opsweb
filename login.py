#-*- coding: utf-8 -*-
from flask import Blueprint,redirect,url_for,render_template,make_response,request,json,flash,session
from sqlalchemy import and_
from Modules import db_op, check,loging,Md5,tools
import string
import redis
import time
from Modules import init
import requests
import os
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
app = Flask(__name__)
app.config.from_pyfile('conf/redis.conf')
app.config.from_pyfile('conf/main.conf')
app.config.from_pyfile('conf/redis.conf')
DB = SQLAlchemy(app)
ENV = None
if os.path.exists('/etc/opweb.conf'):
    with open('/etc/opweb.conf','r') as f:
        ENV = f.read().strip()
limiter = init.web_limiter()
limiter = limiter.limiter
logging = loging.Error()
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
Redis = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
page_login = Blueprint('login', __name__)
@page_login.route('/login',methods = ['GET', 'POST'])
@limiter.limit("60/minute")
def login():
    try:
        try:
            token = tools.Produce(length=24, chars=string.hexdigits)
        except Exception as e:
            logging.error(e)
        ym = time.strftime('%Y',time.localtime())
        session['Menu'] = {}
        #钉钉验证授权
        if tools.http_args(request,'code') and tools.http_args(request,'state') == 'STATE':
            db_auth = db_op.user_auth
            code = tools.http_args(request,'code')
            #获取token
            try:
                url = "https://oapi.dingtalk.com/sns/gettoken?appid=dingoadq3qon8zb34vzdff&appsecret=Tu6IlXjTn1m4vqrOA580xLOt2VbOK26bVu3sBOtvp0MnqIp2zpcwkL3qVpqAT7rG"
                if ENV == 'dev':
                    url = "https://oapi.dingtalk.com/sns/gettoken?appid=dingoa7wymhx6dbeffjels&appsecret=I-v3OXL1hFKYZlJ3b6pqABmoNGYREXePpdzQ5JaSK8DqJdQyn_1J3wEUYBTpdiE_"
                r = requests.get(url)
                access_token = r.json()['access_token']
                r = requests.post("https://oapi.dingtalk.com/sns/get_persistent_code?access_token=%s" %access_token,data=json.dumps({"tmp_auth_code":code}))
                openid = r.json()['openid']
                persistent_code = r.json()['persistent_code']
                r = requests.post("https://oapi.dingtalk.com/sns/get_sns_token?access_token=%s" %access_token,data=json.dumps({"openid": openid,"persistent_code": persistent_code}))
                sns_token = r.json()['sns_token']
                #获取用户信息
                r = requests.get('https://oapi.dingtalk.com/sns/getuserinfo?sns_token=%s' %sns_token)
                user_info = r.json()['user_info']
                nick = user_info['nick']
                dingId = user_info['dingId']
            except Exception as e:
                logging.error(e)
            #授权用户登陆
            if nick and dingId:
                try:
                    val = db_auth.query.filter(and_(db_auth.dingId == dingId, db_auth.openid == openid)).all()
                    if val:
                        db_auth.query.filter(and_(db_auth.dingId == dingId, db_auth.openid == openid)).update({db_auth.token:token,db_auth.update_time:time.strftime('%Y-%m-%d %H:%M:%S',time.localtime())})
                        db_op.DB.session.commit()
                        URL = url_for('main')
                        timestamp = check.timestamp(7)
                    else:
                        #跳转至权限申请页
                        URL = url_for('approval.apply')
                        timestamp = check.timestamp(1)
                except Exception as e:
                    logging.error(e)
                app_resp = make_response(redirect(URL))
                try:
                    app_resp.set_cookie('user', Md5.Md5_make(nick), expires=timestamp,path='/')
                    app_resp.set_cookie('openid', Md5.Md5_make(openid), expires=timestamp,path='/')
                    app_resp.set_cookie('dingId', Md5.Md5_make(dingId), expires=timestamp,path='/')
                    app_resp.set_cookie('token', Md5.Md5_make(token), expires=timestamp,path='/')
                except Exception as e:
                    logging.error(e)
                else:
                    Redis.set('OP_verify_%s' %dingId,token)
                    Redis.set('OP_token_%s' % Md5.Md5_make(token), token)
                    Redis.set('OP_dingId_%s' % Md5.Md5_make(dingId), dingId)
                    Redis.set('OP_user_%s' %Md5.Md5_make(nick),nick)
                    Redis.set('OP_openid_%s' % Md5.Md5_make(openid), openid)
                return app_resp
    except Exception as e:
        flash('登录失败!')
        logging.error(e)
    finally:
        db_op.DB.session.remove()
    return render_template('login.html',ym=ym,ENV=ENV)
@page_login.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()


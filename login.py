#-*- coding: utf-8 -*-
from flask import Flask,Blueprint,redirect,url_for,make_response,request
from module import db_op,loging,Md5,tools
import redis
import time
import os
from sso_cas import CASClient
from flask_sqlalchemy import SQLAlchemy
import conf
app = Flask(__name__)
DB = SQLAlchemy(app)
app.config.from_pyfile('conf/redis.conf')
app.config.from_pyfile('conf/cas.conf')
limiter = conf.WebLimiter()
limiter = limiter.limiter
logging = loging.Error()
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
Redis = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
cas_url = app.config.get('CAS_URL')
service_url = app.config.get('SERVICE_URL')
ENV = tools.check_env()
if ENV == 'dev':
    service_url = app.config.get('SERVICE_TEST_URL')
cas_client = CASClient(cas_url)
page_login = Blueprint('login', __name__)
@page_login.route('/login')
@limiter.limit("60/minute")
def login():
    try:
        db_sso = db_op.user_sso
        ticket = tools.http_args(request,'ticket')
        if ticket:
            try:
                cas_resp = cas_client.perform_service_validate(ticket=ticket,service_url=service_url)
                if cas_resp and cas_resp.success:
                    try:
                        infos = cas_resp.attributes
                        departmentName = infos['departmentName']
                        mail = infos['mail']
                        mobilePhone = infos['mobilePhone']
                        userName = infos['userName']
                        realName = infos['realName']
                        dingunionid = infos['dingunionid']
                        token = tools.Produce(24)
                        update_time = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime())
                    except Exception as e:
                        logging.error(e)
                    else:
                        try:
                            val = db_sso.query.filter(db_sso.dingunionid == dingunionid).all()
                            if val:
                                db_sso.query.filter(db_sso.dingunionid == dingunionid).update({db_sso.department:departmentName,
                                                                                               db_sso.mail:mail,
                                                                                               db_sso.mobilePhone:mobilePhone,
                                                                                               db_sso.userName: userName,
                                                                                               db_sso.ticket: ticket,
                                                                                               db_sso.realName: realName,
                                                                                               db_sso.update_time:update_time})
                                db_op.DB.session.commit()
                            else:
                                c =db_sso(userName=userName,realName=realName,mail=mail,mobilePhone=mobilePhone,department=departmentName,
                                          dingunionid=dingunionid,ticket=ticket,grade='9,10',update_time=update_time)
                                db_op.DB.session.add(c)
                                db_op.DB.session.commit()
                        except Exception as e:
                            logging.error(e)
                        else:
                            URL = url_for('main')
                            app_resp = make_response(redirect(URL))
                            app_resp.set_cookie('user', Md5.Md5_make(realName),path='/')
                            app_resp.set_cookie('dingId', Md5.Md5_make(dingunionid),path='/')
                            app_resp.set_cookie('ticket', Md5.Md5_make(ticket),path='/')
                            app_resp.set_cookie('token',token,path='/')
                            Redis.set('OP_dingId_%s' % Md5.Md5_make(dingunionid), dingunionid)
                            Redis.set('OP_user_%s' % Md5.Md5_make(realName), realName)
                            Redis.set('OP_token_%s' %dingunionid,token)
                            Redis.set('OP_ticket_%s' %Md5.Md5_make(ticket),ticket)
                            Redis.set('OP_logout_ticket_%s' %ticket, ticket)
                            Redis.set('OP_dingid_ticket_%s' %ticket, dingunionid)
                            return app_resp
            except Exception as e:
                logging.error(e)
    except Exception as e:
        logging.error(e)
        return redirect(url_for('error'))
    return redirect(cas_client.get_login_url(service_url=service_url))

@page_login.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
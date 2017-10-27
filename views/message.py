#-*- coding: utf-8 -*-
from flask import Blueprint,render_template,g,flash,request,redirect,url_for
from Modules import main_info
import redis
import __init__
app = __init__.app
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
Redis = redis.StrictRedis(host=redis_host, port=redis_port)
page_message = Blueprint('message',__name__)
@page_message.route('/message')
@main_info.main_info
def message():
    user = request.cookies.get('user')
    ID = request.cookies.get('ID')
    Error_Key = '%s:%s' % (user, ID)
    Error_info = Redis.get(Error_Key)
    if Error_info:
        return render_template('Message.html',Main_Infos=g.main_infos,Error_info=Error_info)
    else:
        return redirect(url_for('login.login'))
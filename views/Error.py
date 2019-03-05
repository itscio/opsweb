#-*- coding: utf-8 -*-
from flask import Blueprint,request,render_template
import redis
from flask import Flask
from Modules import check
app = Flask(__name__)
app.config.from_pyfile('../conf/redis.conf')
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
Redis = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
page_error = Blueprint('error',__name__)
@page_error.route('/error')
@check.login_required(grade=10)
def error():
    ID = request.cookies.get('ID')
    Error_Key = 'error_%s' % ID
    Error_info = Redis.get(Error_Key)
    return render_template('error.html',Error_info=Error_info)
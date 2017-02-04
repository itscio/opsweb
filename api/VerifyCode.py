#-*- coding: utf-8 -*-
from flask import Blueprint,session
from Modules import ImagesChar
import StringIO
import redis
import __init__
app = __init__.app
limiter = __init__.limiter
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
Redis = redis.StrictRedis(host=redis_host, port=redis_port)
page_VerifyCode = Blueprint('VerifyCode', __name__)
@page_VerifyCode.route('/verifycode')
@limiter.limit("10/minute")
def VerifyCode():
    #把strs发给前端,或者在后台使用session保存
    ic = ImagesChar.ImageChar(fontColor=(100,211, 90))
    strs,code_img = ic.randChinese(4)
    buf = StringIO.StringIO()
    code_img.save(buf,'JPEG',quality=70)
    buf_str = buf.getvalue()
    response = app.make_response(buf_str)
    response.headers['Content-Type'] = 'image/jpeg'
    session['verify_code'] = strs
    return response
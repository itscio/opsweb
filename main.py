#-*- coding: utf-8 -*-
from flask import redirect,url_for,make_response,render_template
from flask_wtf.csrf import CsrfProtect
import index,login,logout
from flask_qrcode import QRcode
from flask_moment import Moment
import __init__
app = __init__.app
app.debug = True
CsrfProtect(app)
moment = Moment(app)
qrcode = QRcode(app)
limiter = __init__.limiter
app.config.get('TRAP_HTTP_EXCEPTIONS')
app.register_blueprint(login.page_login)
app.register_blueprint(logout.page_logout)
app.register_blueprint(index.page_index)
@app.route('/')
@limiter.exempt
def main():
    return redirect(url_for('index.index'))
@app.errorhandler(404)
def page_not_found(error):
     resp = make_response(render_template('404.html'),404)
     return resp
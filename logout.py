#-*- coding: utf-8 -*-
from flask import Blueprint,redirect,make_response,request
from Modules import check
page_logout = Blueprint('logout',__name__)
@page_logout.route('/logout')
def logout():
    timestamp = check.timestamp(0)
    app_resp = make_response(redirect('/login'))
    for key in request.cookies:
        app_resp.set_cookie(key, expires=timestamp)
    return app_resp
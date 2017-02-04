#-*- coding: utf-8 -*-
from flask import Blueprint,redirect,make_response
from Modules import check
page_logout = Blueprint('logout',__name__)
@page_logout.route('/logout')
def logout():
    timestamp = check.timestamp(0)
    app_resp = make_response(redirect('/'))
    app_resp.set_cookie('user', expires=timestamp)
    app_resp.set_cookie('ID', expires=timestamp)
    return app_resp
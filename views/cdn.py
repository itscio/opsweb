#-*- coding: utf-8 -*-
from flask import Blueprint,request,render_template,g,flash
from Modules import purge, MyForm,check,produce,main_info
page_cdn = Blueprint('cdn', __name__)
@page_cdn.route('/cdn',methods = ['GET', 'POST'])
@main_info.main_info
def curl():
    form = MyForm.MyForm_input()
    if form.submit.data:
        urls = form.text.data.strip().splitlines()
        urls = set(urls)
        for url in urls:
            Purge = purge.Purged()
            if not url or url.startswith('#'):
                continue
            else:
                url = url.strip()
            if not url.startswith('http'):
                flash('url begin with http(s)://')
                return render_template('Message_static.html',Main_Infos=g.main_infos)
            url_rep=Purge.purge_cdn(url)
            flash(url+' purge CDN '+url_rep)
        return render_template('Message_static.html',Main_Infos=g.main_infos)
    return render_template('cdn.html',form=form,Main_Infos=g.main_infos)
@page_cdn.before_request
@check.login_required(grade=9)
def check_login(error=None):
    produce.Async_log(g.user, request.url)
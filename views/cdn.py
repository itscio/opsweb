#-*- coding: utf-8 -*-
from flask import Blueprint,request,render_template,g,flash
from Modules import purge, MyForm,check,produce
page_cdn = Blueprint('cdn', __name__)
@page_cdn.route('/cdn',methods = ['GET', 'POST'])
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
            if not url.startswith('http://'):
                flash('url begin with http://')
                return render_template('Message.html')
            #clear ats cache
            '''
            ips = Purge.purge_ats(url)
            if ips is None:
                flash(url+' purge ATS success')
            else:
                flash(url+' purge ATS fail from %s' %str(ips))
            '''
            #clear cdn cache
            url_rep=Purge.purge_cdn(url)
            flash(url+' purge CDN '+url_rep)
        return render_template('Message.html')
    return render_template('cdn.html',form=form)
@page_cdn.before_request
@check.login_required(grade=0)
def check_login(error=None):
    produce.Async_log(g.user, request.url)
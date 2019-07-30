#-*- coding: utf-8 -*-
from flask import Flask
from flask.templating import Environment
from pyecharts.engine import ECHAERTS_TEMPLATE_FUNCTIONS
from pyecharts.conf import PyEchartsConfig
from flask_limiter import Limiter
from flask_limiter.util import get_ipaddr
from flask_assets import Bundle
class web_limiter(object):
    def __init__(self,global_limits=["1000/minute"]):
        self.app = Flask(__name__)
        self.global_limits = global_limits
        self.limiter = Limiter(self.app,key_func=get_ipaddr,global_limits=self.global_limits)

class FlaskEchartsEnvironment(Environment):
    def __init__(self, *args, **kwargs):
        super(FlaskEchartsEnvironment, self).__init__(*args, **kwargs)
        self.pyecharts_config = PyEchartsConfig()
        self.globals.update(ECHAERTS_TEMPLATE_FUNCTIONS)

def js_files():
    js = Bundle('js/jquery.cookie.js',
                'js/jquery.SuperSlide.js',
                'js/menu.js',
                'js/autocomplete.js',
                'js/spop.js',
                'js/function.js',
                'js/fishBone.js',
                'js/dropdown.js',
                'js/tooltip.min.js',
                'js/clipboard.min.js',
                'js/Modal.js',
                'js/minigrid.js',
                'js/dynamics.js',
                'js/zh.js',
                filters='jsmin',
                output='js/js_packed.js'
                )
    return js

def css_files():
    css = Bundle('css/material_blue.css',
                'css/mstyle.css',
                'css/style.css',
                'css/menu.css',
                'css/spop.css',
                'css/fishBone.css',
                'css/buttons.css',
                'css/radar.css',
                'css/font-awesome.min.css',
                filters='cssmin',
                output='css/css_packed.css'
                )
    return css
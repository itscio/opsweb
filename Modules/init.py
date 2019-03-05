#-*- coding: utf-8 -*-
from flask import Flask
from flask.templating import Environment
from pyecharts.engine import ECHAERTS_TEMPLATE_FUNCTIONS
from pyecharts.conf import PyEchartsConfig
from flask_limiter import Limiter
from flask_limiter.util import get_ipaddr
app = Flask(__name__)
class web_limiter(object):
    def __init__(self,global_limits=["1000/minute"]):
        self.global_limits = global_limits
        self.limiter = Limiter(app,key_func=get_ipaddr,global_limits=self.global_limits)
class FlaskEchartsEnvironment(Environment):
    def __init__(self, *args, **kwargs):
        super(FlaskEchartsEnvironment, self).__init__(*args, **kwargs)
        self.pyecharts_config = PyEchartsConfig(jshost='https://cdnjs.cloudflare.com/ajax/libs/echarts/4.1.0')
        self.globals.update(ECHAERTS_TEMPLATE_FUNCTIONS)
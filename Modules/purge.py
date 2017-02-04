#-*- coding: utf-8 -*-
from httplib import HTTPConnection
import loging
import hashlib
import urllib
import requests
import binascii
import hmac
import copy
import random
import sys
import time
import __init__
app = __init__.app
class Purged(object):
    def __init__(self):
        self.servers = app.config.get('ATS_SERVERS')
        self.name = app.config.get('CDN_NAME')
        self.password = app.config.get('CDN_PASSWORD')

    def purge_ats(self,url):
        self.url = url.strip()
        self.ips=[]
        for self.ip in self.servers:
            try:
                self.conn = HTTPConnection(self.ip)
                self.conn.request('PURGE',self.url)
                self.response = self.conn.getresponse()
                if self.response.status not in (200,404):
                    self.ips.append(self.ip)
            except Exception as self.e:
                loging.write(self.e)
        if self.ips:
            return self.ips
        else:
            return None

    def purge_cdn(self,url):
        null = None
        self.url = url.strip()
        self.action = 'RefreshCdnUrl'
        if self.url.endswith('/'):
            self.action = 'RefreshCdnDir'
        class Sign:
            def __init__(self, secretId, secretKey):
                self.secretId = secretId
                self.secretKey = secretKey

            def make(self, requestHost, requestUri, params, method = 'GET'):
                srcStr = method.upper() + requestHost + requestUri + '?' + "&".join(k.replace("_",".") + "=" + str(params[k]) for k in sorted(params.keys()))
                hashed = hmac.new(self.secretKey, srcStr, hashlib.sha1)
                return binascii.b2a_base64(hashed.digest())[:-1]

        class Request:
            timeout = 10
            version = 'SDK_PYTHON_1.1'
            def __init__(self, secretId, secretKey):
                self.secretId = secretId
                self.secretKey = secretKey

            def generateUrl(self, requestHost, requestUri, params, method = 'GET'):
                params['RequestClient'] = Request.version
                sign = Sign(self.secretId, self.secretKey)
                params['Signature'] = sign.make(requestHost, requestUri, params, method)
                params = urllib.urlencode(params)

                url = 'https://%s%s' % (requestHost, requestUri)
                if (method.upper() == 'GET'):
                    url += '?' + params
                return url

            def send(self, requestHost, requestUri, params, files = {}, method = 'GET'):
                params['RequestClient'] = Request.version
                sign = Sign(self.secretId, self.secretKey)
                params['Signature'] = sign.make(requestHost, requestUri, params, method)
                url = 'https://%s%s' % (requestHost, requestUri)
                if (method.upper() == 'GET'):
                    req = requests.get(url, params=params, timeout=Request.timeout)
                else:
                    req = requests.post(url, data=params, files=files, timeout=Request.timeout)
                if req.status_code != requests.codes.ok:
                    req.raise_for_status()
                return req.text

        class Cdn:
            requestHost = ''
            requestUri = ''
            _params = {}
            def __init__(self, config):
                self.secretId = config['secretId']
                self.secretKey = config['secretKey']
                self.defaultRegion = config['Region']
                self.method = config['method']
            def _checkParams(self, action, params):
                self._params = copy.deepcopy(params)
                self._params['Action'] = action[0].upper() + action[1:]
                if (self._params.has_key('Region') != True):
                    self._params['Region'] = self.defaultRegion

                if (self._params.has_key('SecretId') != True):
                    self._params['SecretId'] = self.secretId

                if (self._params.has_key('Nonce') != True):
                    self._params['Nonce'] = random.randint(1, sys.maxint)

                if (self._params.has_key('Timestamp') != True):
                    self._params['Timestamp'] = int(time.time())
                return self._params

            def generateUrl(self, action, params):
                self._checkParams(action, params)
                request = Request(self.secretId, self.secretKey)
                return request.generateUrl(self.requestHost, self.requestUri, self._params, self.method)

            def call(self, action, params, files = {}):
                self._checkParams(action, params)
                request = Request(self.secretId, self.secretKey)
                return request.send(self.requestHost, self.requestUri, self._params, files, self.method)
        #config配置
        self.config = {
            'Region': '',
            'secretId': '',
            'secretKey': '',
            'method': ''
        }
        #params 请求参数
        self.params = {
            'urls.0':self.url,
        }
        if self.action == 'RefreshCdnDir':
            self.params = {
                'dirs.0':self.url,
            }
        try:
            self.service = Cdn(self.config)
            #调用接口，发起请求
            self.results = eval(self.service.call(self.action,self.params))
            if self.results['code'] == 0:
                return 'success'
            else:
                return self.results['message']
        except Exception as e:
            loging.write(e)
            return 'fail'







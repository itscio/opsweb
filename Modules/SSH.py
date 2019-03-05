#-*- coding: utf-8 -*-
import paramiko
from flask import Flask
app = Flask(__name__)
app.config.from_pyfile('../conf/ssh.conf')
username = app.config.get('USER')
password = app.config.get('SSH_PW')
keyfile = app.config.get('KEY_FILE')
ssh_port = app.config.get('SSH_PORT')
key_type = app.config.get('KEY_TYPE')
from scp import SCPClient
class ssh(object):
    def __init__(self,username=username,ip=None,ssh_port=ssh_port,keyfile=keyfile,password=password,key_type=key_type):
        self.username = username
        self.ip = str(ip)
        self.ssh_port= int(ssh_port)
        self.keyfile = keyfile
        self.password = password
        self._ssh = paramiko.SSHClient()
        self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if self.keyfile:
            if key_type == 'rsa':
                self.key = paramiko.RSAKey.from_private_key_file(self.keyfile)
            if key_type == 'dsa' or key_type == 'dss':
                self.key = paramiko.DSSKey.from_private_key_file(self.keyfile)
            self._ssh.connect(self.ip, self.ssh_port, self.username, pkey=self.key, timeout=5)
        else:
            if self.username == 'root':
                self._ssh.connect(hostname=self.ip,port=self.ssh_port,username=self.username,password=self.password,timeout=5)
    def Run(self,cmd):
        try:
            if isinstance(cmd,str):
                stdin, stdout, stderr = self._ssh.exec_command(cmd.strip())
            else:
                for Cmd in cmd:
                    stdin, stdout, stderr = self._ssh.exec_command(Cmd.strip())
        except Exception as e:
            return({'stderr':e})
        return {'stdout':stdout.readlines(),'stderr':stderr.readlines()}
    def Close(self):
        self._ssh.close()
    def Scp(self,src,dst):
        scp = SCPClient(self._ssh.get_transport())
        stderr = scp.put(src,dst,recursive=True)
        if stderr:
            return stderr
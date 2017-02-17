#-*- coding: utf-8 -*-
import paramiko
from scp import SCPClient
class ssh(object):
    def __init__(self,username,ip,keyfile=None):
        self.username = username
        self.ip = ip
        self._ssh = paramiko.SSHClient()
        self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if keyfile:
            self.key_file = keyfile
            self.key = paramiko.RSAKey.from_private_key_file(self.key_file)
            if 'dsa' or 'dss' in self.key_file:
                self.key = paramiko.DSSKey.from_private_key_file(self.key_file)
            self._ssh.connect(self.ip, 22, self.username, pkey=self.key, timeout=30)
        else:
            self.pw = '{0}@baihe.op'.format(username)
            self._ssh.connect(self.ip, 22, self.username, password=self.pw, timeout=30)
    def Run(self,cmd):
        if isinstance(cmd,str):
            stdin, stdout, stderr = self._ssh.exec_command(cmd)
        else:
            for Cmd in cmd:
                stdin, stdout, stderr = self._ssh.exec_command(Cmd)
        return {'stdout':stdout.readlines(),'stderr':stderr.readlines()}
    def Close(self):
        self._ssh.close()
    def Scp(self,src,dst):
        scp = SCPClient(self._ssh.get_transport())
        stderr = scp.put(src,dst,recursive=True)
        if stderr:
            return stderr
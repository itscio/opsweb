#-*- coding: utf-8 -*-
from rediscluster import RedisCluster
from kafka import KafkaConsumer
import time
import sys
import requests
#import loging
nodes = [{"host": "", "port": "6379"},{"host": "", "port": "6379"},{"host": "", "port": "6379"}]
rc = RedisCluster(startup_nodes=nodes,decode_responses=True)
def internet_topic():
    H_key = 'haproxy_topic'
    R_key = 'rtime_topic'
    pv_key = 'baihe_pv'
    uv_key = 'baihe_uv'
    area_key = 'Area_Keys'
    traffic_Key = 'traffic_Keys'
    tt = int(time.strftime('%Y%m%d%H%M', time.localtime()))
    consumer = KafkaConsumer('haproxy_logs',
                             group_id='haproxy_logs',
                             bootstrap_servers=[':9092', ':9092', ':9092'])
    def Get_Area(ip):
        # 获取ip对应地区信息
        ip = ip.strip().split('.')
        if len(ip) == 4:
            ip = '%s.0' % '.'.join(ip[:3])
            area = rc.hget('Ip_Area', ip)
            if not area:
                # 获取新地区地址
                URL = "http://int.dpool.sina.com.cn/iplookup/iplookup.php?format=json&ip={0}".format(ip)
                f = requests.request('get', URL, timeout=3)
                area = f.json()['province']
            if area:
                Area_Key = 'Op_Area_%s' % area
                rc.hset('Ip_Area', ip, area)
                rc.sadd(area_key, Area_Key)
                rc.incr(Area_Key)
    for message in consumer:
        try:
            mm = int(time.strftime('%S', time.localtime()))
            Msg = message.value.strip()
            if Msg:
                rc.incr(pv_key)
                traffic_cli = traffic_ser = None
                if len(Msg.split()) > 16:
                    traffic_cli = Msg.split()[10]
                    traffic_ser = Msg.split()[11]
                val = Msg.split('{')
                if len(val) >= 2:
                    Topic = val[1].split('|')[0]
                    IP =val[0].split()[5]
                    Rtime = val[0].split()[8]
                    Rtime = int(Rtime.split('/')[4])
                    try:
                        if rc.sadd(uv_key, IP) == 1:
                            Get_Area(IP)
                    except:
                        pass
                    if ':' in Topic:
                        Topic = str(Topic.split(':')[0])
                    if '.baihe.com' in Topic:
                        Ha_Key = 'haproxy_logs_%s' % Topic
                        Rt_Key = 'Rtime_%s' % Topic
                        Tra_cli_Key = 'traffic.client_%s' % Topic
                        Tra_ser_Key = 'traffic.server_%s' % Topic
                        rc.sadd(traffic_Key,Tra_cli_Key)
                        rc.sadd(traffic_Key,Tra_ser_Key)
                        rc.sadd(H_key,Topic)
                        rc.incr(Ha_Key)
                        if mm == 59:
                            for Key in rc.smembers(traffic_Key):
                                if rc.exists(Key):
                                    rc.set('{0}_old'.format(Key),rc.lrange(Key, 0, -1))
                                    rc.delete(Key)
                        TT = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                        if traffic_cli:
                            rc.lpush(Tra_cli_Key,int(traffic_cli))
                        if traffic_ser:
                            rc.lpush(Tra_ser_Key,int(traffic_ser))
                        for key in (Tra_ser_Key,Tra_cli_Key):
                            Tra_key = '{0}_old'.format(key)
                            if rc.exists(Tra_key):
                                data = eval(str(rc.get(Tra_key)))
                                if data and isinstance(data,list):
                                    va = int(reduce(lambda x, y: int(x) + int(y),data))
                                    v = va * 8 / 1024 / 1024
                                    if v > 1:
                                        rc.rpush('Topic.%s' % key,[TT,v])
                        if Rtime:
                            rc.lpush(Rt_Key,Rtime)
            ts = time.strftime('%H:%M',time.localtime())
            tsi = int(time.strftime('%Y%m%d%H%M', time.localtime()))
            if '23:5' in  ts:
                for key in ('haproxy_logs_*','Rtime_*','traffic.*','Topic.*'):
                    for Key in rc.keys(key):
                        rc.delete(Key)
                for K in (area_key,pv_key,uv_key,H_key,R_key,traffic_Key):
                    rc.delete(K)
        except Exception as e:
            #loging.write(e)
            continue
def intranet_topic():
    H_key = 'haproxy2_topic'
    tt = int(time.strftime('%Y%m%d%H%M', time.localtime()))
    consumer = KafkaConsumer('haproxy_logs',
                             group_id='haproxy_logs',
                             bootstrap_servers=[':9092', ':9092', ':9092'])
    for message in consumer:
        Msg = message.value.strip()
        try:
            if Msg:
                val = Msg.split('{')
                if len(val) >= 2:
                    Topic = val[1].split('}')[0]
                    Rtime = val[0].split()[8]
                    Rtime = int(Rtime.split('/')[4])
                    if ':' in Topic:
                        Topic = str(Topic.split(':')[0])
                    if '|' in Topic:
                        Topic = str(Topic.split('|')[0])
                    if '.baihe.com' in Topic:
                        Key = 'haproxy2_logs_%s' % Topic
                        Rt_Key = 'Rtime2_%s' % Topic
                        rc.sadd(H_key,Topic)
                        rc.incr(Key)
                        if Rtime:
                            rc.lpush(Rt_Key, Rtime)
        except Exception as e:
            #loging.write()
            continue
        ts = int(time.strftime('%Y%m%d%H%M',time.localtime()))
    sys.exit()

def kafka_web():
    H_keys = ('haproxy_topic','haproxy2_topic')
    for  H_key in H_keys:
        for Topic in rc.smembers(H_key):
            try:
                if H_key == 'haproxy_topic':
                    Key = 'haproxy_logs_%s' % Topic
                    web_key = 'internet_access_%s' %Topic
                    Rt_Key = 'Rtime_%s' % Topic
                    web_rt_key = 'internet_rt_%s' %Topic
                if H_key == 'haproxy2_topic':
                    Key = 'haproxy2_logs_%s' % Topic
                    web_key = 'intranet_access_%s' %Topic
                    Rt_Key = 'Rtime2_%s' % Topic
                    web_rt_key = 'intranet_rt_%s' %Topic
                va = int(rc.getset(Key,0))
                Rt_va = rc.lrange(Rt_Key, 0, -1)
                Rt_va = reduce(lambda x,y:int(x)+int(y),Rt_va)/len(Rt_va)
                rc.delete(Rt_Key)
                tt = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                ts = time.strftime("%H:%M", time.localtime())
                if "23:5" in ts:
                    for key in (Key,web_key,web_rt_key):
                        rc.delete(key)
                Rt_data = [tt,Rt_va]
                rc.rpush(web_rt_key,Rt_data)
                data = [tt, va]
                rc.rpush(web_key, data)
            except Exception as e:
                #loging.write(e)
                continue
#-*- coding: utf-8 -*-
from flask import Blueprint,render_template_string,render_template,g,request
from Modules import loging,check,produce
from kafka.client import KafkaClient
import json
import __init__
app = __init__.app
page_kafka_info=Blueprint('kafka_info',__name__)
host = app.config.get('KAFKA_HOST')
port = app.config.get('KAFKA_PORT')
@page_kafka_info.route('/kafka')
@page_kafka_info.route( '/kafka/<topic_info>')
def kafka_info(topic_info = None):
    try:
        kafka = KafkaClient('%s:%s' %(host,port))
        Brokers = kafka.brokers
        Brokers = [(str(Brokers[k]).split(',')[1].split("'")[1]) for k in Brokers ]
        if topic_info:
            partitions = kafka.topic_partitions
            partitions = eval(json.dumps(partitions))
            partitions = partitions[topic_info]
            return render_template('kafka_partition_show.html',topic_info=topic_info,partition_info = partitions)
        else:
            return render_template('kafka_show.html',topics = kafka.topics,brokes = Brokers )
    except Exception as e:
        loging.write(e)
        return  render_template_string('数据获取错误!')
@page_kafka_info.before_request
@check.login_required(grade=10)
def check_login(error=None):
    produce.Async_log(g.user, request.url)
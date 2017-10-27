#-*- coding: utf-8 -*-
from flask import Blueprint,flash,render_template,g,request
from Modules import loging,check,produce,main_info
from pykafka import KafkaClient
import __init__
app = __init__.app
logging = loging.Error()
page_kafka_info=Blueprint('kafka_info',__name__)
KAFKA_HOSTS = app.config.get('KAFKA_HOSTS_PRODUCE')
@page_kafka_info.route('/kafka')
@page_kafka_info.route( '/kafka/<Topic>')
@main_info.main_info
def kafka_info(Topic = None):
    try:
        kafka_client = KafkaClient(hosts=KAFKA_HOSTS)
        # kafka节点
        BROKERS = [kafka_client.brokers[id].host for id in kafka_client.brokers]
        # kafka主题
        TOPICS = [t for t in kafka_client.topics]
        if Topic:
            TOPIC = kafka_client.topics[str(Topic)]
            # kafka ISR
            ISR = {id:[host.host for host in TOPIC.partitions[id].isr] for id in TOPIC.partitions}
            #kafka 副本
            replicas = {id:[host.host for host in TOPIC.partitions[id].replicas] for id in TOPIC.partitions}
            #kafka LRADER
            LEADER = {id:TOPIC.partitions[id].leader.host for id in TOPIC.partitions}
            # kafka latest_offset
            latest_offset = {id:TOPIC.partitions[id].latest_available_offset() for id in TOPIC.partitions}
            # kafka earliest_offset
            earliest_offset = {id:TOPIC.partitions[id].earliest_available_offset() for id in TOPIC.partitions}
            return render_template('kafka_partition_show.html',Main_Infos=g.main_infos,Topic=Topic,ISR = ISR,replicas=replicas,LEADER=LEADER,latest_offset=latest_offset,earliest_offset=earliest_offset)
        else:
            return render_template('kafka_show.html',Main_Infos=g.main_infos,topics = TOPICS,brokes = BROKERS )
    except Exception as e:
        logging.error(e)
        flash('获取数据错误!')
        return render_template('Message_static.html', Main_Infos=g.main_infos)
@page_kafka_info.before_request
@check.login_required(grade=10)
def check_login(error=None):
    produce.Async_log(g.user, request.url)
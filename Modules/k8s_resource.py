#-*- coding: utf-8 -*-
from flask import Flask
from Modules import loging,tools,db_op
from kubernetes import client
import os
import shutil
import docker
import oss2
import time
import redis
from sqlalchemy import and_,desc
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)
app.config.from_pyfile('../conf/sql.conf')
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/oss.conf')
app.config.from_pyfile('../conf/docker.conf')
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
docker_user = app.config.get('USER')
docker_password = app.config.get('PASSWORD')
docker_base_url = app.config.get('BASE_URL')
dockerfile_path = app.config.get('DOCKERFILE_PATH')
oss_id = app.config.get('ID')
oss_key = app.config.get('KEY')
Redis = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
logging = loging.Error()
config,contexts,config_file = tools.k8s_conf()
namespace = "default"
def download_war(dm_name,version,redis_key):
    #下载对应项目的最新war包
    try:
        #包名需要规范
        Redis.lpush(redis_key, '%s-%s.war package download from oss ......' %(dm_name,version))
        auth = oss2.Auth(oss_id, oss_key)
        bucket = oss2.Bucket(auth, 'oss-cn-beijing.aliyuncs.com', 'mojiops')
        file_war = None
        for obj in oss2.ObjectIterator(bucket, prefix='tomcat-'):
            if '%s-%s'%(dm_name,version) in obj.key:
                file_war = obj.key
                break
        if not os.path.exists('%s/%s' %(dockerfile_path,dm_name)):
            os.mkdir('%s/%s' %(dockerfile_path,dm_name))
        if file_war:
            object = file_war.split('/')[-1]
            project_path = '%s/%s/%s.war' %(dockerfile_path,dm_name,dm_name.split('-')[0])
            if os.path.exists(project_path):
                os.remove(project_path)
            #尝试3次下载
            for i in range(3):
                try:
                    oss2.resumable_download(bucket, file_war, project_path)
                except Exception as e:
                    logging.error(e)
                else:
                    if os.path.exists(project_path):
                        #生成dockerfile文件
                        #
                        Redis.lpush(redis_key, '%s package download success!' % object)
                        return object
        else:
            Redis.lpush(redis_key, '%s package not fond!' % object)
            return None
        if not os.path.exists(project_path):
            Redis.lpush(redis_key, '%s package download fail!' % object)
            return None
    except Exception as e:
        logging.error(e)
        Redis.lpush(redis_key, '%s package download fail!' % object)
        return None

def make_image(image,redis_key):
    try:
        Redis.lpush(redis_key, 'start build image %s......' % image)
        dockerfile = "%s/%s" %(dockerfile_path,image.split('/')[-1].split(':')[0])
        if os.path.exists(dockerfile):
            try:
                client = docker.APIClient(base_url=docker_base_url)
                response = [line for line in client.build(path=dockerfile, rm=True, tag=image)]
                result = eval(response[-1])
                if 'Successfully' in str(result):
                    Redis.lpush(redis_key,"docker build %s success!" %image)
                else:
                    Redis.lpush(redis_key,'fail:%s'%result)
                    return False
            except Exception as e:
                logging.error(e)
                if 'BaseException' not in str(e):
                    Redis.lpush(redis_key, 'fail:%s' % e)
            else:
                try:
                    response = [line for line in client.push(image, stream=True,auth_config={'username':docker_user,'password':docker_password})]
                    result = eval(response[-1])['aux']['Tag']
                    version = image.split(':')[-1]
                    if version == result:
                        Redis.lpush(redis_key,"docker push %s success!" % image)
                        return True
                    else:
                        Redis.lpush(redis_key, 'fail:%s' %result)
                        return False
                except Exception as e:
                    logging.error(e)
                    Redis.lpush(redis_key, 'fail:%s' %e)
                    return False

        else:
            Redis.lpush(redis_key,'dockerfile %s path not exists!' %dockerfile, 'fail')
            return False
    except Exception as e:
        logging.error(e)
        if 'BaseException' not in str(e):
            Redis.lpush(redis_key, 'fail:%s' % e)
        return False

class k8s_object(object):
    def __init__(self,dm_name,image,container_port,replicas,re_requests={},re_limits={}):
        config.load_kube_config(config_file, context=contexts[0])
        self.config_file = config_file
        self.dm_name = dm_name
        self.image = image
        self.container_port = container_port
        self.replicas = replicas
        self.re_requests = {'cpu':2,'memory': '4G'}
        self.re_limits = {'cpu':6,'memory': '8G'}
        if re_requests and re_limits:
            self.re_requests = re_requests
            self.re_limits = re_limits
    def export_deployment(self):
        # Configureate Pod template container
        container = client.V1Container(
            name=self.dm_name,
            image=self.image,
            ports=[client.V1ContainerPort(container_port=int(port)) for port in self.container_port],
            image_pull_policy='Always',
            env= [client.V1EnvVar(name='LANG',value='en_US.UTF-8'),
                  client.V1EnvVar(name='LC_ALL', value='en_US.UTF-8')
                  ],
            resources=client.V1ResourceRequirements(limits=self.re_limits,
                                                    requests=self.re_requests),
            volume_mounts = [client.V1VolumeMount(mount_path='/opt/logs',name='logs')],
            liveness_probe=client.V1Probe(initial_delay_seconds=5,
                tcp_socket=client.V1TCPSocketAction(port=int(self.container_port[0]))
            )
        )
        # Create and configurate a spec section
        secrets = client.V1LocalObjectReference('registrysecret')
        volume = client.V1Volume(name='logs', host_path=client.V1HostPathVolumeSource(path='/opt/logs'))
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"project": self.dm_name}),
            spec=client.V1PodSpec(containers=[container],
                                  image_pull_secrets=[secrets],volumes=[volume])
        )
        selector = client.V1LabelSelector(match_labels={"project": self.dm_name})
        # Create the specification of deployment
        spec = client.ExtensionsV1beta1DeploymentSpec(
            replicas=int(self.replicas),
            template=template,
            selector=selector,
            min_ready_seconds=3
        )
        # Instantiate the deployment object
        deployment = client.ExtensionsV1beta1Deployment(
            api_version="extensions/v1beta1",
            kind="Deployment",
            metadata=client.V1ObjectMeta(name=self.dm_name),
            spec=spec)
        return deployment

    def export_service(self):
        ports = [client.V1ServicePort(port=int(port),target_port=int(port)) for port in self.container_port]
        spec = client.V1ServiceSpec(ports=ports,selector={'project':self.dm_name})
        service = client.V1Service(
            api_version = 'v1',
            kind = 'Service',
            metadata=client.V1ObjectMeta(name=self.dm_name),
            spec=spec)
        return service

    def export_ingress(self,ingress_domain,ingress_port):
        try:
            Rules = []
            db_ingress = db_op.k8s_ingress
            Rules_infos = db_ingress.query.with_entities(db_ingress.domain,db_ingress.serviceName,db_ingress.servicePort).all()
            if Rules_infos:
                for infos in Rules_infos:
                    domain,serviceName,servicePort = infos
                    Rules.append(client.V1beta1IngressRule(host=domain,
                                      http=client.V1beta1HTTPIngressRuleValue(
                                          paths=[client.V1beta1HTTPIngressPath(client.V1beta1IngressBackend(
                                              service_name=serviceName,
                                              service_port=int(servicePort)
                                          ))])
                                      ))
        except Exception as e:
            logging.error(e)
        else:
            Rules.append(client.V1beta1IngressRule(host=ingress_domain,
                                      http=client.V1beta1HTTPIngressRuleValue(
                                          paths=[client.V1beta1HTTPIngressPath(client.V1beta1IngressBackend(
                                              service_name=self.dm_name,
                                              service_port=int(ingress_port)
                                          ))])
                                      ))
            spec = client.V1beta1IngressSpec(rules=Rules)
            ingress = client.V1beta1Ingress(
                api_version='extensions/v1beta1',
                kind='Ingress',
                metadata=client.V1ObjectMeta(name='nginx-ingress',
                                             namespace=namespace,
                                             annotations={'kubernetes.io/ingress.class': 'nginx'}),
                spec=spec
            )
            return ingress
        finally:
            db_op.DB.session.remove()

    def delete_deployment(self):
        try:
            api_instance = client.ExtensionsV1beta1Api()
            body = client.V1DeleteOptions(propagation_policy='Foreground', grace_period_seconds=5)
            api_instance.delete_namespaced_deployment(name=self.dm_name, namespace=namespace, body=body)
            return True
        except Exception as e:
            logging.error(e)
            return False

def check_pod(dm_name,replicas,old_pods):
    api_instance = client.CoreV1Api()
    # 判断pod是否部署成功
    try:
        for t in range(30):
            phases = []
            ret = api_instance.list_namespaced_pod(namespace=namespace)
            if ret:
                for i in ret.items:
                    if dm_name in i.metadata.name:
                        if i.metadata.name not in old_pods:
                            if i.status.container_statuses[-1].state.running:
                                phase = 'Running'
                                phases.append(phase)
            if len(phases) >= int(replicas):
                return True
            time.sleep(2)
    except Exception as e:
        logging.error(e)
    return False
def delete_pod(dm_name):
    try:
        api_instance = client.CoreV1Api()
        ret = api_instance.list_namespaced_pod(namespace=namespace)
        for i in ret.items:
            if dm_name in i.metadata.name:
                api_instance.delete_namespaced_pod(name=i.metadata.name,
                                                   namespace=namespace,
                                                   body=client.V1DeleteOptions())
        return True
    except Exception as e:
        logging.error(e)
        return False
def object_deploy(args):
    try:
        project, object, version, image, container_port, ingress_port, replicas, domain,re_requests, re_limits,redis_key = args
        dm_name = object.split('.')[0]
        db_k8s = db_op.k8s_deploy
        values = db_k8s.query.filter(db_k8s.image == image).all()
        if values:
            raise Redis.lpush(redis_key, '%s image already exists!' %image)
        war = download_war(object,version,redis_key)
        if war:
            # 制作docker镜像并上传至仓库
            if make_image(image,redis_key):
                db_k8s = db_op.k8s_deploy
                #部署deployment
                Redis.lpush(redis_key,'start deploy deployment %s......' %dm_name)
                k8s = k8s_object(dm_name, image, container_port, replicas, re_requests, re_limits)
                api_instance = client.ExtensionsV1beta1Api()
                try:
                    deployment = k8s.export_deployment()
                    api_instance.create_namespaced_deployment(body=deployment, namespace=namespace)
                except Exception as e:
                    logging.error(e)
                    Redis.lpush(redis_key, 'fail:%s' % e)
                else:
                    try:
                        Redis.lpush(redis_key, '......deploy deployment success!')
                        Redis.lpush(redis_key,'start deploy service %s......' %dm_name)
                        service = k8s.export_service()
                        old_pods = []
                        if check_pod(dm_name, replicas,old_pods):
                            #部署service
                            try:
                                api_instance = client.CoreV1Api()
                                api_instance.create_namespaced_service(body=service,namespace=namespace)
                            except Exception as e:
                                logging.error(e)
                                if 'BaseException' not in str(e):
                                    Redis.lpush(redis_key, 'fail:%s' % e)
                            else:
                                #部署ingress
                                Redis.lpush(redis_key, '......deploy service success!')
                                if ingress_port and domain:
                                    api_instance = client.ExtensionsV1beta1Api()
                                    for Domain in domain.split(','):
                                        Redis.lpush(redis_key,'start deploy ingress %s......' % Domain)
                                        try:
                                            ingress = k8s.export_ingress(ingress_domain=Domain.strip(),ingress_port=int(ingress_port))
                                            api_instance.replace_namespaced_ingress(body=ingress,namespace=namespace,
                                                                                    name='nginx-ingress')
                                        except Exception as e:
                                            logging.error(e)
                                            Redis.lpush(redis_key, 'fail:%s'%e)
                                        else:
                                            Redis.lpush(redis_key, '......deploy ingress success!')
                                            #ingress信息写入数据库
                                            db_ingress = db_op.k8s_ingress
                                            v = db_ingress(name='nginx-ingress',namespace=namespace,domain=domain,
                                                           serviceName=dm_name,servicePort=int(ingress_port))
                                            db_op.DB.session.add(v)
                                            db_op.DB.session.commit()
                                #部署日志记录
                                try:
                                    v = db_k8s(project=project, deployment=dm_name, image=image,war = war,
                                               container_port=','.join([str(port) for port in container_port]),
                                               replicas=replicas,
                                               re_requests=str(re_requests).replace("'",'"'),
                                               re_limits=str(re_limits).replace("'",'"'), action='create',
                                               update_date=time.strftime('%Y-%m-%d', time.localtime()),
                                               update_time=time.strftime('%H:%M:%S', time.localtime()))
                                    db_op.DB.session.add(v)
                                    db_op.DB.session.commit()
                                except Exception as e:
                                    logging.error(e)
                                    if 'BaseException' not in str(e):
                                        Redis.lpush(redis_key, 'fail:%s' % e)
                        else:
                            #自动删除deployment
                            k8s.delete_deployment()
                            Redis.lpush(redis_key,"......create deployment %s fail!" %dm_name)
                    except Exception as e:
                        logging.error(e)
                        if 'BaseException' not in str(e):
                            Redis.lpush(redis_key, 'fail:%s' % e)
    except Exception as e:
        logging.error(e)
        if 'BaseException' not in str(e):
            Redis.lpush(redis_key, 'fail:%s' % e)
    finally:
        db_op.DB.session.remove()
        Redis.lpush(redis_key,'_End_')

def object_update(args):
    try:
        new_image, new_replicas,version,redis_key = args
        if new_image and redis_key:
            db_k8s = db_op.k8s_deploy
            dm_name = new_image.split('/')[-1].split(':')[0]
            #生成新镜像
            values = db_k8s.query.with_entities(db_k8s.project, db_k8s.container_port, db_k8s.image,
                                                db_k8s.replicas,db_k8s.re_requests, db_k8s.re_limits).filter(and_(
                db_k8s.deployment == dm_name, db_k8s.action != 'delete')).order_by(desc(db_k8s.id)).limit(1).all()
            project, container_port,image,replicas, re_requests, re_limits = values[0]
            war = download_war(dm_name,version,redis_key)
            if not war:
                raise Redis.lpush(redis_key, "params error,update fail!")
            if not make_image(new_image,redis_key):
                raise Redis.lpush(redis_key, "image record not exists,update fail!")
            try:
                Redis.lpush(redis_key, 'start deploy image %s   ......' % new_image)
                re_requests = eval(re_requests)
                re_limits = eval(re_limits)
                container_port = container_port.split(',')
                k8s = k8s_object(dm_name, image, container_port, replicas, re_requests, re_limits)
                deployment = k8s.export_deployment()
                # Update container image
                deployment.spec.template.spec.containers[0].image = new_image
                if new_replicas:
                    deployment.spec.replicas = int(new_replicas)
                    replicas = new_replicas
                # Update the deployment
                try:
                    api_instance = client.CoreV1Api()
                    ret = api_instance.list_namespaced_pod(namespace=namespace)
                    old_pos = [i.metadata.name for i in ret.items if dm_name in i.metadata.name]
                    if image == new_image:
                        if not delete_pod(dm_name):
                            raise Redis.lpush(redis_key,'delete old pod fail!')
                    api_instance = client.ExtensionsV1beta1Api()
                    api_instance.patch_namespaced_deployment(name=dm_name, namespace=namespace,
                                                         body=deployment)
                except Exception as e:
                    logging.error(e)
                    Redis.lpush(redis_key,'deployment parameter fail!')
                else:
                    Redis.lpush(redis_key, 'start check deploy result......')
                    if check_pod(dm_name, replicas,old_pos):
                        v = db_k8s(project=project, deployment=dm_name, image=new_image,war=war,
                                   container_port=container_port,
                                   replicas=replicas, re_requests=str(re_requests).replace("'", '"'),
                                   re_limits=str(re_limits).replace("'", '"'), action='update',
                                   update_date=time.strftime('%Y-%m-%d', time.localtime()),
                                   update_time=time.strftime('%H:%M:%S', time.localtime()))
                        db_op.DB.session.add(v)
                        db_op.DB.session.commit()
                        Redis.lpush(redis_key, '%s image deploy success!' % new_image)
                    else:
                        deployment.spec.template.spec.containers[0].image = image
                        if image == new_image:
                            delete_pod(dm_name)
                        api_instance = client.ExtensionsV1beta1Api()
                        api_instance.patch_namespaced_deployment(name=dm_name, namespace=namespace,
                                                                 body=deployment)
                        Redis.lpush(redis_key,'%s image deploy fail,auto rolled back!' % new_image)
            except Exception as e:
                logging.error(e)
                Redis.lpush(redis_key, 'fail:%s' % e)
    except Exception as e:
        logging.error(e)
        if 'BaseException' not in str(e):
            Redis.lpush(redis_key, 'fail:%s' % e)
    finally:
        db_op.DB.session.remove()
        Redis.lpush(redis_key, '_End_')
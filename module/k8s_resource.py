#-*- coding: utf-8 -*-
import conf
from module import loging,tools,db_op
from kubernetes import client
import os
import shutil
import tarfile
import docker
import oss2
import time
import redis
from sqlalchemy import and_,desc
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
app = Flask(__name__)
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/redis.conf')
app.config.from_pyfile('../conf/docker.conf')
app.config.from_pyfile('../conf/tokens.conf')
app.config.from_pyfile('../conf/oss.conf')
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
docker_user = app.config.get('USER')
docker_password = app.config.get('PASSWORD')
docker_base_url = app.config.get('BASE_URL')
dockerfile_path = app.config.get('DOCKERFILE_PATH')
ops_token = app.config.get('OPS_TOKEN')
oss_id = app.config.get('OSS_ID')
oss_key = app.config.get('OSS_KEY')
oss_url = app.config.get('OSS_URL')
Redis = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
logging = loging.Error()
config,contexts,config_file = tools.k8s_conf()
flow_number = time.strftime('%Y%m%d%H%M%S',time.localtime())
#流水日志记录
def _flow_log(Msg):
    try:
        logpath = "/opt/k8s/flow_logs"
        tm = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime())
        if not os.path.exists(logpath):
            os.system("/bin/mkdir -p %s" %logpath)
        flow_log_ptah = "%s/%s.log" %(logpath,flow_number)
        with open(flow_log_ptah,'a+') as f:
            f.write("%s  %s\n"%(tm,str(Msg)))
    except Exception as e:
        logging.error(e)

def download_war(object,version,run_args,redis_key):
    #下载对应项目的最新代码包
    try:
        #包名需要规范
        Files = tools.get_k8s_packages()
        project_file = object
        object = object.split('.')
        dm_name = object[0]
        if dm_name in Files:
            project_file = Files[dm_name]
        dm_type = project_file.split('.')[-1]
        if len(project_file.split('.')) >2:
            dm_type = '.'.join(project_file.split('.')[1:])
        package = '%s-%s.%s'% (dm_name, version, dm_type)
        project_path = '%s/%s/%s' % (dockerfile_path, dm_name, project_file)
        if not os.path.exists(project_path):
            try:
                Redis.lpush(redis_key, '%s package download from oss ......' %package)
                _flow_log('%s package download from oss ......' %package)
                auth = oss2.Auth(oss_id, oss_key)
                bucket = oss2.Bucket(auth, oss_url, 'mojiops')
                oss_project_path = None
                try:
                    if not os.path.exists('%s/%s' %(dockerfile_path,dm_name)):
                        os.mkdir('%s/%s' %(dockerfile_path,dm_name))
                    for obj in oss2.ObjectIterator(bucket):
                        if obj.key.endswith('.war') or obj.key.endswith('.tar.gz') or obj.key.endswith('.jar'):
                            if obj.key.split('/')[-1].startswith(dm_name) and version in obj.key.split('/')[-1]:
                                oss_project_path = obj.key
                                break
                except Exception as e:
                    logging.error(e)
                if oss_project_path:
                    #尝试3次下载
                    for i in range(3):
                        try:
                            oss2.resumable_download(bucket,oss_project_path, project_path)
                            break
                        except:
                            continue
                else:
                    Redis.lpush(redis_key, '%s package not fond!' %package)
                    _flow_log('%s package not fond!' %package)
                    return False
            except Exception as e:
                logging.error(e)
        if os.path.exists(project_path):
            try:
                if project_file.endswith('.tar.gz'):
                    project_file = project_file.split('.')[0]
                    os.chdir('%s/%s/' % (dockerfile_path,dm_name))
                    tar = tarfile.open(project_path.split('/')[-1], 'r')
                    tar.extractall()
                    tar.close()
                    for file in os.listdir('./'):
                        if dm_name in file and not file.endswith('.tar.gz'):
                            shutil.move(file,project_file)
                    if os.path.exists(dm_name):
                        os.remove(project_path.split('/')[-1])
                #生成dockerfile文件
                dockerfile = '%s/%s/Dockerfile' %(dockerfile_path,dm_name)
                if os.path.exists(dockerfile):
                    os.remove(dockerfile)
                with open(dockerfile, 'a+') as f:
                    with open('%s/../conf/dockerfile_%s.template'%(app.root_path,dm_type)) as F:
                        for line in F:
                            if '<PROJECT>' in line:
                                line = line.replace('<PROJECT>',project_file)
                            f.write('%s\n'%line)
                #生成docker_run启动脚本文件
                if run_args:
                    runfile = '%s/%s/run.sh' % (dockerfile_path, dm_name)
                    if os.path.exists(runfile):
                        os.remove(runfile)
                    with open(runfile, 'a+') as f:
                        with open('%s/../conf/docker_run.template' %app.root_path) as F:
                            for line in F:
                                f.write('%s\n' % line)
                        for line in run_args:
                            f.write('%s\n' % line)
                Redis.lpush(redis_key, '%s package download success!' %package)
                _flow_log('%s package download success!' %package)
                return package
            except Exception as e:
                logging.error(e)
        else:
            Redis.lpush(redis_key, '%s package download fail!' %package)
            _flow_log('%s package download fail!' %package)
            return False
    except Exception as e:
        logging.error(e)

def make_image(image,redis_key):
    try:
        Redis.lpush(redis_key, 'start build image %s......' % image)
        _flow_log('start build image %s......' % image)
        project = image.split('/')[-1].split(':')[0]
        dockerfile = "%s/%s" %(dockerfile_path,project)
        if os.path.exists(dockerfile):
            try:
                client = docker.APIClient(base_url=docker_base_url)
                response = [line for line in client.build(path=dockerfile, rm=True, tag=image)]
                result = eval(response[-1])
                if 'Successfully' in str(result):
                    Redis.lpush(redis_key,"docker build %s success!" %image)
                    _flow_log("docker build %s success!" %image)
                else:
                    Redis.lpush(redis_key,'fail:%s'%result)
                    _flow_log('fail:%s'%result)
                    return False
            except Exception as e:
                logging.error(e)
                if 'BaseException' not in str(e):
                    Redis.lpush(redis_key, 'fail:%s' % e)
                    _flow_log('fail:%s' % e)
            else:
                try:
                    Files = tools.get_k8s_packages()
                    response = [line for line in client.push(image, stream=True,auth_config={'username':docker_user,'password':docker_password})]
                    result = eval(response[-1])['aux']['Tag']
                    version = image.split(':')[-1]
                    if version == result:
                        #删除代码包
                        for file in os.listdir(dockerfile):
                            if Files[project].split('.')[0] in file:
                                try:
                                    os.remove('%s/%s' % (dockerfile,file))
                                except:
                                    shutil.rmtree('%s/%s' % (dockerfile,file))
                        Redis.lpush(redis_key,"docker push %s success!" % image)
                        _flow_log("docker push %s success!" % image)
                        return True
                    else:
                        Redis.lpush(redis_key, 'fail:%s' %result)
                        _flow_log('fail:%s' %result)
                        return False
                except Exception as e:
                    logging.error(e)
                    Redis.lpush(redis_key, 'fail:%s' %e)
                    _flow_log('fail:%s' %e)
                    return False
        else:
            Redis.lpush(redis_key,'dockerfile %s path not exists!' %dockerfile, 'fail')
            _flow_log('dockerfile %s path not exists!' %dockerfile, 'fail')
            return False
    except Exception as e:
        logging.error(e)
        if 'BaseException' not in str(e):
            Redis.lpush(redis_key, 'fail:%s' % e)
            _flow_log('fail:%s' % e)
        return False

class k8s_object(object):
    def __init__(self,dm_name,image,container_port,replicas,mounts,healthcheck,sidecar,re_requests={},re_limits={}):
        config.load_kube_config(config_file, context=contexts[0])
        self.namespace = "default"
        self.config_file = config_file
        self.dm_name = dm_name
        self.image = image
        self.container_port = container_port
        self.replicas = replicas
        self.mounts = mounts
        self.healthcheck = healthcheck
        self.sidecar = sidecar
        self.re_requests = {'cpu':1,'memory': '2G'}
        self.re_limits = {'cpu':2,'memory': '4G'}
        if re_requests and re_limits:
            self.re_requests = re_requests
            self.re_limits = re_limits
    def export_deployment(self):
        # Configureate Pod template container
        volume_mounts = []
        containers = []
        volumes = []
        volume_mounts.append(client.V1VolumeMount(mount_path='/docker/logs', name='logs'))
        volumes.append(client.V1Volume(name='logs',
                                       host_path=client.V1HostPathVolumeSource(path='/opt/logs',
                                                                               type='DirectoryOrCreate')))
        if self.mounts:
            for path in self.mounts:
                volume_mounts.append(client.V1VolumeMount(mount_path=path, name=self.mounts[path]))
                volumes.append(client.V1Volume(name=self.mounts[path],
                                               host_path=client.V1HostPathVolumeSource(path=path,
                                                                                       type='DirectoryOrCreate')))
        liveness_probe = client.V1Probe(initial_delay_seconds=15,
                                        tcp_socket=client.V1TCPSocketAction(port=int(self.container_port[0])))
        readiness_probe = client.V1Probe(initial_delay_seconds=15,
                                         tcp_socket=client.V1TCPSocketAction(port=int(self.container_port[0])))
        if self.healthcheck:
            liveness_probe = client.V1Probe(initial_delay_seconds=15,
                                            http_get=client.V1HTTPGetAction(path=self.healthcheck,
                                                                            port=int(self.container_port[0])))
            readiness_probe = client.V1Probe(initial_delay_seconds=15,
                                             http_get=client.V1HTTPGetAction(path=self.healthcheck,
                                                                             port=int(self.container_port[0])))
        Env = [client.V1EnvVar(name='LANG', value='en_US.UTF-8'),
                 client.V1EnvVar(name='LC_ALL', value='en_US.UTF-8'),
                 client.V1EnvVar(name='POD_NAME',value_from=client.V1EnvVarSource(
                     field_ref=client.V1ObjectFieldSelector(field_path='metadata.name'))),
                 client.V1EnvVar(name='POD_IP', value_from=client.V1EnvVarSource(
                     field_ref=client.V1ObjectFieldSelector(field_path='status.podIP'))),
                 ]
        container = client.V1Container(
            name=self.dm_name,
            image=self.image,
            ports=[client.V1ContainerPort(container_port=int(port)) for port in self.container_port],
            image_pull_policy='Always',
            env=Env,
            resources=client.V1ResourceRequirements(limits=self.re_limits,
                                                    requests=self.re_requests),
            volume_mounts=volume_mounts,
            liveness_probe=liveness_probe,
            readiness_probe=readiness_probe
        )
        containers.append(container)
        if self.sidecar:
            sidecar_container = client.V1Container(
                name= 'sidecar-%s' %self.dm_name,
                image = self.sidecar,
                image_pull_policy='Always',
                env=Env,
                resources=client.V1ResourceRequirements(limits=self.re_limits,
                                                        requests=self.re_requests),
                volume_mounts=volume_mounts)
            containers.append(sidecar_container)
        # Create and configurate a spec section
        secrets = client.V1LocalObjectReference('registrysecret')
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"project": self.dm_name}),
            spec=client.V1PodSpec(containers=containers,
              image_pull_secrets=[secrets],
              volumes=volumes,
              affinity=client.V1Affinity(
                  node_affinity=client.V1NodeAffinity(
                      preferred_during_scheduling_ignored_during_execution = [
                          client.V1PreferredSchedulingTerm(
                              preference=client.V1NodeSelectorTerm(
                                  match_expressions=[client.V1NodeSelectorRequirement(
                                      key='project',
                          operator='In',values=['moji'])
                      ]),weight=30),
                          client.V1PreferredSchedulingTerm(
                              preference=client.V1NodeSelectorTerm(
                                  match_expressions=[client.V1NodeSelectorRequirement(
                                      key='deploy',
                          operator='In',values=[self.dm_name])
                      ]),weight=70)]
              )))
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

    def export_service(self,node_port):
        ports = [client.V1ServicePort(port=int(port), target_port=int(port)) for port in self.container_port]
        spec = client.V1ServiceSpec(ports=ports, selector={'project': self.dm_name},type='ClusterIP')
        if node_port:
            ports = [client.V1ServicePort(port=int(self.container_port[0]), target_port=int(self.container_port[0]),node_port=int(node_port))]
            spec = client.V1ServiceSpec(ports=ports,selector={'project':self.dm_name},type='NodePort')
        service = client.V1Service(
            api_version = 'v1',
            kind = 'Service',
            metadata=client.V1ObjectMeta(name=self.dm_name),
            spec=spec)
        return service

    def export_ingress(self,domains,ingress_port):
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
            for ingress_domain in domains:
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
                                             namespace=self.namespace,
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
            api_instance.delete_namespaced_deployment(name=self.dm_name, namespace=self.namespace, body=body)
            return True
        except Exception as e:
            logging.error(e)
            return False

    def delete_service(self):
        try:
            api_instance = client.CoreV1Api()
            body = client.V1DeleteOptions(propagation_policy='Foreground', grace_period_seconds=5)
            api_instance.delete_namespaced_service(name=self.dm_name, namespace=self.namespace, body=body)
            return True
        except Exception as e:
            logging.error(e)
            return False

    def delete_ingress(self):
        try:
            db_ingress = db_op.k8s_ingress
            v = db_ingress.query.filter(db_ingress.serviceName==self.dm_name).all()
            if v:
                for c in v:
                    db_op.DB.session.delete(c)
            return True
        except Exception as e:
            logging.error(e)
            return False
        finally:
            db_op.DB.session.remove()

    def delete_hpa(self):
        try:
            api_instance = client.AutoscalingV2beta2Api()
            body = client.V1DeleteOptions(propagation_policy='Foreground', grace_period_seconds=5)
            api_instance.delete_namespaced_horizontal_pod_autoscaler(name=self.dm_name, namespace=self.namespace, body=body)
            return True
        except Exception as e:
            logging.error(e)
            return False

def check_pod(dm_name,replicas,old_pods,redis_key):
    namespace = "default"
    api_instance = client.CoreV1Api()
    # 判断pod是否部署成功
    try:
        Redis.lpush(redis_key, '进行POD运行状态检查，大约用时1分钟......')
        _flow_log('进行POD运行状态检查，大约用时1分钟......')
        for t in range(4):
            phases = []
            ret = api_instance.list_namespaced_pod(namespace=namespace)
            if ret:
                for i in ret.items:
                    if i.metadata.name.startswith(dm_name) and i.metadata.name not in old_pods:
                        phase = 'unknown'
                        if i.status.container_statuses:
                            if i.status.container_statuses[-1].state.running:
                                phase = 'Running'
                                phases.append(phase)
                            else:
                                if i.status.container_statuses[-1].state.waiting:
                                    phase = i.status.container_statuses[-1].state.waiting.reason
                            Redis.lpush(redis_key, 'POD:%s ---->当前状态:%s' %(i.metadata.name,phase))
                            _flow_log('POD:%s ---->当前状态:%s' %(i.metadata.name,phase))
            if len(phases) >= int(replicas):
                Redis.lpush(redis_key, 'POD运行状态检测正常!')
                _flow_log('POD运行状态检测正常!')
                return True
            time.sleep(15)
        if len(phases) < int(replicas):
            Redis.lpush(redis_key, 'POD运行状态存在异常!')
            _flow_log('POD运行状态存在异常!')
    except Exception as e:
        logging.error(e)
        _flow_log(e)
    return False

def delete_pod(dm_name):
    try:
        namespace = "default"
        api_instance = client.CoreV1Api()
        ret = api_instance.list_namespaced_pod(namespace=namespace)
        for i in ret.items:
            if i.metadata.name.startswith(dm_name):
                api_instance.delete_namespaced_pod(name=i.metadata.name,
                                                   namespace=namespace,
                                                   body=client.V1DeleteOptions())
        return True
    except Exception as e:
        logging.error(e)
        return False

def object_deploy(args):
    try:
        namespace = "default"
        (project, object, version, image,run_args, container_port, ingress_port, replicas,
         domain,re_requests,mounts,healthcheck,sidecar,re_limits,redis_key) = args
        dm_name = object.split('.')[0]
        db_k8s = db_op.k8s_deploy
        values = db_k8s.query.filter(db_k8s.image == image).all()
        if values:
            _flow_log('%s image already exists!' %image)
            raise Redis.lpush(redis_key, '%s image already exists!' %image)
        war = download_war(object,version,run_args,redis_key)
        if war:
            # 制作docker镜像并上传至仓库
            if make_image(image,redis_key):
                db_k8s = db_op.k8s_deploy
                db_docker_run = db_op.docker_run
                #部署deployment
                Redis.lpush(redis_key,'start deploy deployment %s......' %dm_name)
                _flow_log('start deploy deployment %s......' %dm_name)
                k8s = k8s_object(dm_name, image, container_port, replicas,mounts,healthcheck,sidecar,re_requests,re_limits)
                api_instance = client.ExtensionsV1beta1Api()
                try:
                    deployment = k8s.export_deployment()
                    api_instance.create_namespaced_deployment(body=deployment, namespace=namespace)
                except Exception as e:
                    logging.error(e)
                    Redis.lpush(redis_key, 'fail:%s' % e)
                    _flow_log('fail:%s' % e)
                else:
                    try:
                        Redis.lpush(redis_key, '......deploy deployment success!')
                        _flow_log('......deploy deployment success!')
                        old_pods = []
                        if check_pod(dm_name, replicas,old_pods,redis_key):
                            #部署service
                            try:
                                Redis.lpush(redis_key, 'start deploy service %s......' % dm_name)
                                _flow_log('start deploy service %s......' % dm_name)
                                node_port = None
                                if ingress_port and not domain and len(container_port) == 1:
                                    node_port = ingress_port
                                service = k8s.export_service(node_port)
                                api_instance = client.CoreV1Api()
                                api_instance.create_namespaced_service(body=service,namespace=namespace)
                            except Exception as e:
                                logging.error(e)
                                # 自动删除service
                                k8s.delete_service()
                                if 'BaseException' not in str(e):
                                    Redis.lpush(redis_key, 'fail:%s' % e)
                                    _flow_log('fail:%s' % e)
                            else:
                                #部署ingress
                                Redis.lpush(redis_key, '......deploy service success!')
                                _flow_log('......deploy service success!')
                                if ingress_port and domain:
                                    api_instance = client.ExtensionsV1beta1Api()
                                    Domains = [domain.strip() for domain in domain.split(',') if domain]
                                    Redis.lpush(redis_key,'start deploy ingress %s......' % domain)
                                    _flow_log('start deploy ingress %s......' % domain)
                                    try:
                                        ingress = k8s.export_ingress(domains=Domains,ingress_port=int(ingress_port))
                                        if ingress:
                                            api_instance.patch_namespaced_ingress(body=ingress,namespace=namespace,
                                                                                name='nginx-ingress')
                                        else:
                                            raise Redis.lpush(redis_key, 'deploy ingress fail')
                                    except Exception as e:
                                        logging.error(e)
                                        Redis.lpush(redis_key, 'fail:%s'%e)
                                    else:
                                        Redis.lpush(redis_key, '......deploy ingress success!')
                                        _flow_log('......deploy ingress success!')
                                        #ingress信息写入数据库
                                        db_ingress = db_op.k8s_ingress
                                        for domain in Domains:
                                            v = db_ingress(name='nginx-ingress',namespace=namespace,domain=domain,
                                                           serviceName=dm_name,servicePort=int(ingress_port))
                                            db_op.DB.session.add(v)
                                            db_op.DB.session.commit()
                                try:
                                    # 部署日志记录
                                    v = db_k8s(project=project, deployment=dm_name, image=image,war = war,
                                               container_port=','.join([str(port) for port in container_port]),
                                               replicas=replicas,
                                               re_requests=str(re_requests).replace("'",'"'),
                                               re_limits=str(re_limits).replace("'",'"'), action='create',
                                               update_date=time.strftime('%Y-%m-%d', time.localtime()),
                                               update_time=time.strftime('%H:%M:%S', time.localtime()))
                                    db_op.DB.session.add(v)
                                    db_op.DB.session.commit()
                                    #记录docker启动参数
                                    v = db_docker_run(deployment=dm_name,run_args=str(run_args),side_car=sidecar)
                                    db_op.DB.session.add(v)
                                    db_op.DB.session.commit()
                                except Exception as e:
                                    logging.error(e)
                                    if 'BaseException' not in str(e):
                                        Redis.lpush(redis_key, 'fail:%s' % e)
                                        _flow_log('fail:%s' % e)
                        else:
                            #自动删除deployment
                            k8s.delete_deployment()
                            Redis.lpush(redis_key,"......create deployment %s fail!" %dm_name)
                            _flow_log("......create deployment %s fail!" %dm_name)
                    except Exception as e:
                        logging.error(e)
                        if 'BaseException' not in str(e):
                            Redis.lpush(redis_key, 'fail:%s' % e)
                            _flow_log('fail:%s' % e)
    except Exception as e:
        logging.error(e)
        if 'BaseException' not in str(e):
            Redis.lpush(redis_key, 'fail:%s' % e)
            _flow_log('fail:%s' % e)
    finally:
        db_op.DB.session.remove()
        Redis.lpush(redis_key,'_End_')
        _flow_log('_End_')

def object_update(args):
    try:
        namespace = "default"
        mounts = None
        healthcheck= None
        sidecar = None
        run_args = None
        new_image, new_replicas,version,redis_key,channel = args
        if new_image and redis_key:
            db_k8s = db_op.k8s_deploy
            db_docker_run = db_op.docker_run
            dm_name = new_image.split('/')[-1].split(':')[0]
            #生成新镜像
            values = db_k8s.query.with_entities(db_k8s.project, db_k8s.container_port, db_k8s.image,db_k8s.war,
                                                db_k8s.replicas,db_k8s.re_requests, db_k8s.re_limits).filter(and_(
                db_k8s.deployment == dm_name, db_k8s.action != 'delete')).order_by(desc(db_k8s.id)).limit(1).all()
            project, container_port,image,war,replicas, re_requests, re_limits = values[0]
            vals = db_docker_run.query.with_entities(db_docker_run.run_args,db_docker_run.side_car).filter(db_docker_run.deployment==dm_name).all()
            if vals:
                run_args = eval(run_args[0][0])
                sidecar = eval(run_args[0][1])
            war = download_war(dm_name,version,run_args,redis_key)
            if not war:
                _flow_log("params error,update fail!")
                raise Redis.lpush(redis_key, "params error,update fail!")
            if not make_image(new_image,redis_key):
                _flow_log("image record not exists,update fail!")
                raise Redis.lpush(redis_key, "image record not exists,update fail!")
            try:
                _flow_log('start deploy image %s   ......' % new_image)
                Redis.lpush(redis_key, 'start deploy image %s   ......' % new_image)
                re_requests = eval(re_requests)
                re_limits = eval(re_limits)
                container_port = container_port.split(',')
                k8s = k8s_object(dm_name, image, container_port, replicas,mounts,healthcheck,sidecar,re_requests,re_limits)
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
                    old_pos = [i.metadata.name for i in ret.items if i.metadata.name.startswith(dm_name)]
                    api_instance = client.ExtensionsV1beta1Api()
                    api_instance.patch_namespaced_deployment(name=dm_name, namespace=namespace,
                                                         body=deployment)
                except Exception as e:
                    logging.error(e)
                    _flow_log('deployment parameter fail!')
                    Redis.lpush(redis_key,'deployment parameter fail!')
                else:
                    _flow_log('开始进行更新后的结果验证......')
                    Redis.lpush(redis_key, '开始进行更新后的结果验证......')
                    if check_pod(dm_name, replicas,old_pos,redis_key):
                        v = db_k8s(project=project, deployment=dm_name, image=new_image,war=war,
                                   container_port=container_port,
                                   replicas=replicas, re_requests=str(re_requests).replace("'", '"'),
                                   re_limits=str(re_limits).replace("'", '"'), action='update',
                                   update_date=time.strftime('%Y-%m-%d', time.localtime()),
                                   update_time=time.strftime('%H:%M:%S', time.localtime()))
                        db_op.DB.session.add(v)
                        db_op.DB.session.commit()
                        _flow_log('%s 镜像更新成功!' % new_image)
                        Redis.lpush(redis_key, '%s 镜像更新成功!' % new_image)
                        if channel == 'api':
                            text = ['**容器平台自动上线:**',"项目:%s" %project,"版本:%s" %version,"操作:更新成功", '**请关注业务健康状况!**']
                    else:
                        deployment.spec.template.spec.containers[0].image = image
                        if image == new_image:
                            delete_pod(dm_name)
                        api_instance = client.ExtensionsV1beta1Api()
                        api_instance.patch_namespaced_deployment(name=dm_name, namespace=namespace,
                                                                 body=deployment)
                        _flow_log('%s 镜像更新失败并自动回滚!' % new_image)
                        Redis.lpush(redis_key,'%s 镜像更新失败并自动回滚!' % new_image)
                        if channel == 'api':
                            text = ['**容器平台自动上线:**',"项目:%s" %project,"版本:%s" %version,"操作:失败并回滚", '**需要手动处理!**']
            except Exception as e:
                logging.error(e)
                _flow_log( 'fail:%s' % e)
                Redis.lpush(redis_key, 'fail:%s' % e)
                if channel == 'api':
                    text = ['**容器平台自动上线:**', "项目:%s" % project, "版本:%s" % version, "操作:更新未完成", '**需要手动处理!**']
    except Exception as e:
        logging.error(e)
        if 'BaseException' not in str(e):
            _flow_log('fail:%s' % e)
            Redis.lpush(redis_key, 'fail:%s' % e)
        if channel == 'api':
            text = ['**容器平台自动上线:**', "项目:%s" % project, "版本:%s" % version, "操作:更新未完成", '**需要手动处理!**']
    finally:
        db_op.DB.session.remove()
        Redis.lpush(redis_key, '_End_')
        if channel == 'api':
            tools.dingding_msg(text,ops_token)
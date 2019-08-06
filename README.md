该平台整合业界开源自动化运维工具结合自主研发，致力于打造CI/CD全链路平台和一站式综合管理平台。由于使用sso方式登录验证、平台配置文件及依赖底层数据源众多建议只做代码交流学习.因项目开发进度问题代码注释比较少,只注释重要逻辑部分,见谅！别忘了给个star^_^
# 开发语言与环境依赖 #
编程语言：Python3.6 + HTML + JQuery
前端Web框架：Bootstrap4
前端图表框架：Pycharts + Datatables
后端Web框架：Flask1.0+
后端Task框架：Pyscheduler + Redis
后端数据库：mysql、influxdb
后端日志源：ElasticSearch
监控数据源：zabbix
后端代码库：gitlab
容器化平台：Kubernetes + Docker + Harbor
后端编译：jenkins
登录鉴权：cas
操作系统：CentOS 7+
Ansible版本：2.6+
web运行：Nginx + Gunicron

# 主要功能： #
    - 全新架构优化调整
    - 由sso单点登录系统进行统一鉴权
    - 标准CMDB资产管理
    - 代码上线，包含上线、灰度、回滚等功能并实时显示执行过程 
    - 生产环境基于git、jenkins、harbor、k8s容器化实现的CI\CD流水作业 
    - 自主开发k8s容器UI管理及一键式容器环境部署、代码更新
    - 自动进行服务器资产、应用服务的信息及关联关系抓取及资产、资源的生命周期管理
    - 生产服务资源例如mysql、redis、kafka等信息汇总查询
    - WEBSSH登录
    - 实时大数据分析包含线上业务的并发量、流量、响应时间、业务访问占比、用户地区分布等
    - 安全审查包括登录鉴权记录、用户操作记录、访问记录
    - 业务运行关键指标报警、监控报警故障自动处理
    - 访问限速、访问黑名单、用户单点登录限制等安全措施
    - 页面级别用户权限控制
    - 通过分布式全局锁,进程锁,实现多机多进程部署后台单任务运行
    — 新增工单系统、工单统计报表功能
    - 本平台适合具有python二次开发能力者或运维开发学习者。    
# 界面展示
![show](https://github.com/wylok/opsweb/blob/master/static/images/01.jpg)
# 资产管理
![show](https://github.com/wylok/opsweb/blob/master/static/images/02.jpg)
# 工单系统
![show](https://github.com/wylok/opsweb/blob/master/static/images/04.jpg)
# K8s平台管理
![show](https://github.com/wylok/opsweb/blob/master/static/images/03.jpg)
author:wylok@126.com

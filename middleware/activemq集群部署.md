# zookeeper&activemq集群标准部署手册

## 一、概述

ZooKeeper是一个分布式应用下的分布式、开源的协调服务。分布式应用依赖ZooKeeper提供的基础稳固的服务，可以很容易地实现更高层的服务，实现同步、配置信息维护、分组和命名。它的设计目标就是可以易于编程并使用一种类似树形结构的文件系统设计数据模型。运行在Java虚拟机上，同时支持Java语言和C语言。协调服务特别的难于实现正确，特别容易出现竞争条件和死锁，所以ZooKeeper的动机就是减少分布式系统实现协调服务的开发困难，防止从新开发。

ActiveMQ 是Apache出品，最流行的，能力强劲的开源消息总线。ActiveMQ 是一个完全支持JMS1.1和J2EE 1.4规范的 JMS Provider实现，尽管JMS规范出台已经是很久的事情了，但是JMS在当今的J2EE应用中间仍然扮演着特殊的地位。

### 1、目的

为了加快和提高服务器资源交付应用和投入生产的效率，服务器的部署工作要做到规
范化，标准化；在规范化，标准化的前提下，进一步实现自动化/半自动化；从而最终提高
工作效率，降低遗漏等错误发生率。
鉴于以上缘由，催化了此文档的产生，一方面也是为了方便部署时的参考，防止在部
署过程中细节的忽视和遗漏，另一方面也为了以后的自动化批量部署做准备。
本文亦可作为对新员工的培训资料。

### 2、适合的读者对象

本手册适合以下读者对象：
基础架构团队的服务器部署人员；主机系统以及中间件管理人员；网络管理人员；数
据库管理员，新入职员工等。

### 3、操作系统和jdk&zookeeper&activemq版本

操作系统版本：Ubuntu-16.04/CentOS 7
JDK 版本：1.7.0_80-b15
zookeeper 版本：3.4.10
activemq 版本：5.13.4



#二、部署zookeeper集群

搭建zookeeper集群一般建议为奇数台，这里选择三台。

**1、为三台机器配置jdk环境，线上系统统一使用jdk-7u80-linux-x64版本，统一安装目录为/usr/local/**

```
tar zxvf jdk-7u80-linux-x64.tar.gz -C /usr/local/
```

在/etc/profile末尾添加以下配置：

```
export JAVA_HOME=/usr/local/jdk1.7.0_80
export JRE_HOME=/usr/local/jdk1.7.0_80/jre
export CLASSPATH=.:${JAVA_HOME}/lib:${JRE_HOME}/lib:${CLASSPATH}
export PATH=${JAVA_HOME}/bin:${JAVA_HOME}/jre/bin:${PATH}
```

执行source /etc/profile使配置生效。

**2、为三台机器安装zookeeper，统一使用zookeeper-3.4.10版本，统一安装目录为/data/apps/zookeeper**

```
tar zxvf zookeeper-3.4.10.tar.gz -C /data/apps
mv zookeeper-3.4.10 zookeeper
```

**3、配置zookeeper配置文件**

```
cp -Rp /data/apps/zookeeper/conf/zoo_sample.cfg /data/apps/zookeeper/conf/zoo.cfg
```

vim zoo.cfg
```
tickTime=2000
initLimit=10
syncLimit=5
dataDir=/data/apps/zookeeper/data
dataLogDir=/data/apps/zookeeper/logs
clientPort=2181
server.0=192.168.56.101:2888:3888
server.1=192.168.56.102:2888:3888
server.2=192.168.56.103:2888:3888
```
注：dataDir： 快照日志的存储路径

​        dataLogDir：事物日志的存储路径，如果不配置这个那么事物日志会默认存储到dataDir制定的目录，这样会严重影响zk的性能，当zk吞吐量较大的时候，产生的事物日志、快照日志太多。

分别在node1、node2、node3上创建myid文件

```
echo 0 > /data/apps/zookeeper/data/myid
echo 1 > /data/apps/zookeeper/data/myid
echo 2 > /data/apps/zookeeper/data/myid
```

启动服务

```
/data/apps/zookeeper/bin/zkServer.sh start
/data/apps/zookeeper/bin/zkServer.sh status
/data/apps/zookeeper/bin/zkServer.sh start-foreground 可以查看启动过程
```

此时查看可能会报错：Error contacting service. It is probably not running。这是防火墙的原因，关闭防火墙或者允许2888/3888端口

```
firewall-cmd --zone=public --add-port=2888/tcp --permanent
firewall-cmd --zone=public --add-port=3888/tcp --permanent
```

重新启动zookeeper。



#三、部署activemq集群

**1、jdk环境前面已经配置过了，这里不再进行配置说明**

**2、为三台机器安装activemq，统一使用apache-activemq-5.13.4版本，统一安装目录为/data/apps/activemq**

```
tar zxvf apache-activemq-5.13.4-bin.tar.gz -C /data/apps/
mv apache-activemq-5.13.4 activemq
```

**3、修改配置文件**

3.1、配置环境变量,否则可能会出现路径有多个/

vim /etc/profile

```
export ACTIVEMQ_HOME=/data/apps/activemq
```

3.2、修改activemq配置文件

vim activemq.xml

```
brokerName=ActivemqCluster   #找到brokerName配置项，指定节点名称，三个节点名称需要一致
```

```
找到persistenceAdapter配置段，注释kahaDB配置行。
        <persistenceAdapter>
        <!--
            <kahaDB directory="${activemq.data}/kahadb"/>
        -->
        <replicatedLevelDB
        directory="${activemq.data}/kahadb"
        replicas="3"
        bind="tcp://0.0.0.0:62621"
        zkAddress="192.168.56.101:2181,192.168.56.102:2182,192.168.56.103:2181"
        hostname="192.168.56.101"
        zkPath="/activemq/leveldb-stores"
        />
        </persistenceAdapter>
```

以上配置分别在三台机器上配置，hostname配置项请按照不同机器，配置不同IP。

3.3、端口说明

```
Zookeeper
2181 – the port that clients will use to connect to the ZK ensemble
2888 – port used by ZK for quorum election
3888 – port used by ZK for leader election

ActiveMQ
61616 – 消息端口（服务端口）　　# 默认的
8161  – 控制台端口　　　　　　　# 默认的
62621 – 集群通信端口
```

```
centos7:
firewall-cmd --zone=public --add-port=62621/tcp --permanent
firewall-cmd --zone=public --add-port=61616/tcp --permanent
firewall-cmd --zone=public --add-port=8161/tcp --permanent
firewall-cmd --zone=public --add-port=2888/tcp --permanent
firewall-cmd --zone=public --add-port=3888/tcp --permanent
firewall-cmd --zone=public --add-port=2181/tcp --permanent
systemctl restart firewalld
firewall-cmd --zone=public --list-ports 61616/tcp 3888/tcp 2181/tcp 2888/tcp 8161/tcp 62621/tcp
```

**4、启动zookeeper、activemq**

```
/data/apps/activemq/bin/activemq start   #最好先启动leader状态的机器上的activemq
```

**5、验证**

```
/data/apps/zookeeper/bin/zkCli.sh
ls /activemq/leveldb-stores
```

在三台机器都可以看到数据，说明已经成功

分别登陆：

```
http://192.168.56.101:8161/admin/
http://192.168.56.102:8161/admin/
http://192.168.56.103:8161/admin/
```































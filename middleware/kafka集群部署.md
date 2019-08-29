# zookeeper&kafka集群标准部署手册

## 一、概述

​	**ZooKeeper**是一个分布式应用下的分布式、开源的协调服务。分布式应用依赖ZooKeeper提供的基础稳固的服务，可以很容易地实现更高层的服务，实现同步、配置信息维护、分组和命名。它的设计目标就是可以易于编程并使用一种类似树形结构的文件系统设计数据模型。运行在Java虚拟机上，同时支持Java语言和C语言。协调服务特别的难于实现正确，特别容易出现竞争条件和死锁，所以ZooKeeper的动机就是减少分布式系统实现协调服务的开发困难，防止从新开发。

​	**Kafka**是由Apache软件基金会开发的一个开源流处理平台，由Scala和Java编写。Kafka是一种高吞吐量的分布式发布订阅消息系统，它可以处理消费者规模的网站中的所有动作流数据。 这种动作（网页浏览，搜索和其他用户的行动）是在现代网络上的许多社会功能的一个关键因素。 这些数据通常是由于吞吐量的要求而通过处理日志和日志聚合来解决。 对于像Hadoop的一样的日志数据和离线分析系统，但又要求实时处理的限制，这是一个可行的解决方案。Kafka的目的是通过Hadoop的并行加载机制来统一线上和离线的消息处理，也是为了通过集群来提供实时的消费。

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

### 3、操作系统和jdk&zookeeper&kafka版本

操作系统版本：Ubuntu-16.04/CentOS 7
JDK 版本：1.8.0_151-b12
zookeeper 版本：3.4.11
kafka 版本：1.0.0



#二、部署zookeeper集群

搭建zookeeper集群一般建议为奇数台，这里选择三台。

**1、为三台机器配置jdk环境，线上系统统一使用jdk-8u151-linux-x64版本，统一安装目录为/usr/local/**

```
tar zxvf jdk-8u151-linux-x64.tar.gz -C /usr/local/
```

在/etc/profile末尾添加以下配置：

```
export JAVA_HOME=/usr/local/jdk1.8.0_151
export JRE_HOME=/usr/local/jdk1.8.0_151/jre
export CLASSPATH=.:${JAVA_HOME}/lib:${JRE_HOME}/lib:${CLASSPATH}
export PATH=${JAVA_HOME}/bin:${JAVA_HOME}/jre/bin:${PATH}
```

执行source /etc/profile使配置生效。

**2、为三台机器安装zookeeper，统一使用zookeeper-3.4.11版本，统一安装目录为/opt/apps/zookeeper**

```
tar zxvf zookeeper-3.4.11.tar.gz -C /opt/apps
mv /opt/apps/zookeeper-3.4.11 /opt/apps/zookeeper
```

**3、配置zookeeper配置文件**

```
cp -Rp /opt/apps/zookeeper/conf/zoo_sample.cfg /opt/apps/zookeeper/conf/zoo.cfg
```

vim zoo.cfg
```
tickTime=2000
initLimit=10
syncLimit=5
dataDir=/data/data/zookeeper
dataLogDir=/data/logs/zookeeper
clientPort=2181
server.0=172.16.70.42:2888:3888
server.1=172.16.70.43:2888:3888
server.2=172.16.70.44:2888:3888
```
注：dataDir： 快照日志的存储路径

​        dataLogDir：事物日志的存储路径，如果不配置这个，那么事物日志会默认存储到dataDir制定的目录，这样会严重影响zk的性能，当zk吞吐量较大的时候，产生的事物日志、快照日志太多。

分别在node1、node2、node3上的ataDir目录下创建myid文件

```
echo 0 > /data/data/zookeeper/myid
echo 1 > /data/data/zookeeper/myid
echo 2 > /data/data/zookeeper/myid
```

vim /opt/apps/zookeeper/bin/zkEnv.sh

```
ZOO_LOG_DIR="/data/logs/zookeeper"
```

启动服务

```
/opt/apps/zookeeper/bin/zkServer.sh start
/opt/apps/zookeeper/bin/zkServer.sh status
/opt/apps/zookeeper/bin/zkServer.sh start-foreground 可以查看启动过程
```

此时查看可能会报错：Error contacting service. It is probably not running。这是防火墙的原因，关闭防火墙或者允许2888/3888端口

```
firewall-cmd --zone=public --add-port=2888/tcp --permanent
firewall-cmd --zone=public --add-port=3888/tcp --permanent
```

重新启动zookeeper。

![1](images\1.png)

![2](images\2.png)

![3](images\3.png)

至此，zookeeper集群已经部署完毕。



#三、部署kafka集群

**1、jdk环境前面已经配置过了，这里不再进行配置说明**

**2、为三台机器安装kafka，统一使用kafka_2.11-1.0.0版本，统一安装目录为/ope/apps/kafka**

```
tar zxvf kafka_2.11-1.0.0.tgz -C /opt/apps/
mv /opt/apps/kafka_2.11-1.0.0 /opt/apps/kafka
```

**3、修改配置文件**

vim /opt/apps/kafka/config/server.properties

```
broker.id=1
listeners = PLAINTEXT://172.16.70.42:9092
zookeeper.connect=172.16.70.42:2181,172.16.70.43:2181,172.16.70.44:2181
```

```
broker.id=2
listeners = PLAINTEXT://172.16.70.43:9092
zookeeper.connect=172.16.70.42:2181,172.16.70.43:2181,172.16.70.44:2181
```

```
broker.id=3
listeners = PLAINTEXT://172.16.70.44:9092
zookeeper.connect=172.16.70.42:2181,172.16.70.43:2181,172.16.70.44:2181
```

```
broker.id=0
listeners=PLAINTEXT://:9092
num.network.threads=3
num.io.threads=8
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600
log.dirs=/tmp/kafka-logs
num.partitions=1
num.recovery.threads.per.data.dir=1
log.retention.hours=168
log.segment.bytes=1073741824
log.retention.check.interval.ms=300000
zookeeper.connect=master.storm.com:2181
zookeeper.connection.timeout.ms=6000
```



说明：如果是单机版的话，默认即可。配置集群，所以需要配置一些参数:

1)、broker.id：每台机器不能一样

2)、zookeeper.connect：因为我有3台zookeeper服务器，所以在这里zookeeper.connect设置为3台，必须全部加进去

3)、listeners：在配置集群的时候，必须设置，不然以后的操作会报找不到leader的错误

**4、启动kafka**

```
/opt/apps/kafka/bin/kafka-server-start.sh -daemon /opt/apps/kafka/config/server.properties

/opt/apps/kafka/bin/kafka-server-stop.sh
```

**5、验证**

```
# jps
21968 QuorumPeerMain
23572 Jps
1223 Application
23502 Kafka
```

在三台机器都可以看到数据，说明已经启动成功

创建topic：

```
/opt/apps/kafka/bin/kafka-topics.sh --create --zookeeper 172.16.70.42:2181 --replication-factor 1 --partitions 1 --topic test
显示Created topic "test"表示创建成功。

/opt/apps/kafka/bin/kafka-topics.sh --list --zookeeper 172.16.70.43:2181
/opt/apps/kafka/bin/kafka-topics.sh --list --zookeeper 172.16.70.44:2181
在另外两台机器上也可以看到创建的topic
```



创建发布：

```
/opt/apps/kafka/bin/kafka-console-producer.sh --broker-list 172.16.70.42:9092 --topic test
```

创建消费：

```
/opt/apps/kafka/bin/kafka-console-consumer.sh --bootstrap-server 172.16.70.42:9092 --topic test --from-beginning
```

至此zookeeper+kafka集群已经部署完毕。

```
kafka-topics.sh --create --zookeeper emr-header-1:2181,emr-header-2:2181,emr-header-3:2181/kafka-1.0.0 --replication-factor 1 --partitions 10 --topic test

kafka-topics.sh --list --zookeeper emr-header-1:2181,emr-header-2:2181,emr-header-3:2181/kafka-1.0.0

kafka-console-consumer.sh --bootstrap-server 172.31.59.246:9092,172.31.59.247:9092,172.31.59.248:9092,172.31.59.249:9092,172.31.59.250:9092,172.31.59.251:9092 --topic test --from-beginning

kafka-topics.sh --delete --zookeeper emr-header-1:2181,emr-header-2:2181,emr-header-3:2181/kafka-1.0.0 --topic nginx
```







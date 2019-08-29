# Ceph存储集群

> 不管你是想为云平台提供[*Ceph 对象存储*](http://docs.ceph.org.cn/glossary/#term-30)和/或 [*Ceph 块设备*](http://docs.ceph.org.cn/glossary/#term-38)，还是想部署一个 [*Ceph 文件系统*](http://docs.ceph.org.cn/glossary/#term-45)或者把 Ceph 作为他用，所有 [*Ceph 存储集群*](http://docs.ceph.org.cn/glossary/#term-21)的部署都始于部署一个个 Ceph 节点、网络和 Ceph 存储集群。 Ceph 存储集群至少需要一个 Ceph Monitor 和两个 OSD 守护进程。而运行 Ceph 文件系统客户端时，则必须要有元数据服务器（ Metadata Server ）。
>
> Ceph OSDs：Ceph OSD 守护进程（ Ceph OSD ）的功能是存储数据，处理数据的复制、恢复、回填、再均衡，并通过检查其他OSD 守护进程的心跳来向 Ceph Monitors 提供一些监控信息。当 Ceph 存储集群设定为有2个副本时，至少需要2个 OSD 守护进程，集群才能达到 `active+clean` 状态（ Ceph 默认有3个副本，但你可以调整副本数）。
>
> Monitors：Ceph Monitor维护着展示集群状态的各种图表，包括监视器图、 OSD 图、归置组（ PG ）图、和 CRUSH 图。 Ceph 保存着发生在Monitors 、 OSD 和 PG上的每一次状态变更的历史信息（称为 epoch ）。
>
> MDSs：Ceph 元数据服务器（ MDS ）为 Ceph 文件系统存储元数据（也就是说，Ceph 块设备和 Ceph 对象存储不使用MDS ）。元数据服务器使得 POSIX 文件系统的用户们，可以在不对 Ceph 存储集群造成负担的前提下，执行诸如 `ls`、`find` 等基本命令。
>
> 
>
> Ceph 把客户端数据保存为存储池内的对象。通过使用 CRUSH 算法， Ceph 可以计算出哪个归置组（PG）应该持有指定的对象(Object)，然后进一步计算出哪个 OSD 守护进程持有该归置组。 CRUSH 算法使得 Ceph 存储集群能够动态地伸缩、再均衡和修复。



## 节点构造如下 :

| 节点ip                         | hostname | 说明                       |
| ------------------------------ | -------- | -------------------------- |
| 172.16.20.8<br/>192.168.10.8   | ceph-01  | 管理节点，监视器，存储节点 |
| 172.16.20.9<br/>192.168.10.9   | ceph-02  | 管理节点，监视器，存储节点 |
| 172.16.20.10<br/>192.168.10.10 | ceph-03  | 管理节点，监视器，存储节点 |

生产环境：

| 节点ip | hostname    | 说明                         |
| ------ | ----------- | ---------------------------- |
|        | ceph-mon-01 | 管理节点，监视器 monitor,mds |
|        | ceph-mon-02 | 监视器 monitor,mds,client    |
|        | ceph-mon-03 | 监视器 monitor,mds           |
|        | ceph-osd-01 | 存储节点 osd                 |
|        | ceph-osd-02 | 存储节点 osd                 |
|        | ceph-osd-03 | 存储节点 osd                 |



## 集群网络结构：

| 网络名称                                 | 网络范围        |
| ---------------------------------------- | --------------- |
| 公共网络(供客户端连接使用)               | 172.16.20.0/24  |
| 集群网络(供集群内部使用，与其它网络隔离) | 192.168.10.0/24 |

### 

## 一、安装前准备

###1、系统设置

####1.2、绑定主机名

```
echo -e "\n# Ceph Cluster\n192.168.10.8\tceph-01\n192.168.10.9\tceph-02\n192.168.10.10\tceph-03" >> /etc/hosts
```

#### 1.3、配置ssh互通

```
test -d .ssh || mkdir -m 700 .ssh
ssh-keygen -t rsa -b 4096
for i in ceph-01 ceph-02 ceph-03; do ssh-copy-id $i; done
```

#### 1.4、防火墙

打开TCP6789、6800-7100端口

```
firewall-cmd --zone=public --add-port=6789/tcp --permanent
firewall-cmd --zone=public --add-port=6800-7100/tcp --permanent
firewall-cmd --reload
```

####1.5、时间同步

配置/etc/chrony.conf

```
server ntp.aliyun.com iburst
stratumweight 0
driftfile /var/lib/chrony/drift
rtcsync
makestep 10 3
bindcmdaddress 127.0.0.1
bindcmdaddress ::1
keyfile /etc/chrony.keys
commandkey 1
generatecommandkey
logchange 0.5
logdir /var/log/chrony
```

####1.6、配置软件源并安装ceph-deploy

```
[Ceph]
name = Ceph packages for $basearch
baseurl = http://mirrors.cloud.aliyuncs.com/ceph/rpm-luminous/el7/$basearch
	      https://mirrors.aliyun.com/ceph/rpm-luminous/el7/$basearch
enabled = 1
gpgcheck = 1
gpgkey = http://mirrors.cloud.aliyuncs.com/ceph/keys/release.asc

[Ceph-noarch]
name = Ceph noarch packages
baseurl = http://mirrors.cloud.aliyuncs.com/ceph/rpm-luminous/el7/noarch
	      https://mirrors.aliyun.com/ceph/rpm-luminous/el7/noarch
enabled = 1
gpgcheck = 1
gpgkey = http://mirrors.cloud.aliyuncs.com/ceph/keys/release.asc

[ceph-source]
name = Ceph source packages
baseurl = http://mirrors.cloud.aliyuncs.com/ceph/rpm-luminous/el7/SRPMS
	      https://mirrors.aliyun.com/ceph/rpm-luminous/el7/SRPMS
enabled = 1
gpgcheck = 1
gpgkey = http://mirrors.cloud.aliyuncs.com/ceph/keys/release.asc
```

安装ceph-deploy

```
yum -y install ceph-deploy
```

执行 ceph-deploy --version确认版本

创建ceph-cluster目录，将文件输出到该文件夹

```
mkdir ceph-cluster
cd ceph-cluster
```



##二、准备磁盘

###2.1、journal磁盘

在每个节点为journal磁盘分区，vdb1,vdb2分别对应本机两个osd

```
parted /dev/vdd mklabel gpt
parted /dev/vdd mkpart primary xfs  0% 50%
parted /dev/vdd mkpart primary xfs 50% 100%
```

### 2.2、OSD磁盘

OSD磁盘不需要做处理，交由ceph-deploy操作。如果OSD磁盘存在分区，可通过以下方式删除

```
parted /dev/vdb rm 1
```



##三、安装Ceph

### 3.1、使用ceph-deploy安装ceph

####3.1.1、创建新集群

```
ceph-deploy new ceph-01 ceph-02 ceph-03
```

- 如您有多个网络接口，请在ceph配置文件添加以下配置

  ```
  public network = {ip-address}/{bits}
  ```

- 如要在ipv6环境中部署，请`ceph.conf`在本地目录中添加以下内容：

  ```
  echo ms bind ipv6 = true >> ceph.conf
  ```

####3.1.2、在所有节点安装ceph

```
ceph-deploy install ceph-01 ceph-02 ceph-03
```

- 也可在每个节点执行`yum -y install ceph ceph-radosgw`来安装

####3.1.3、创建和初始化监控节点

```
ceph-deploy --overwrite-conf mon create-initial
```

- 请确保ceph.conf中为监控节点列出的IP是公共IP，而不是私有IP 。

####3.1.4、清空OSD磁盘

```
ceph-deploy disk zap ceph-01 /dev/sdd /dev/sde 
ceph-deploy disk zap ceph-02 /dev/sdd /dev/sde 
ceph-deploy disk zap ceph-03 /dev/sdd /dev/sde
```

#### 3.1.5、创建OSD存储节点

```
ceph-deploy osd create --data /dev/vdd ceph-01
ceph-deploy osd create --data /dev/vdd ceph-02
ceph-deploy osd create --data /dev/vdd ceph-03

ceph-deploy osd create --data /dev/vde ceph-01
ceph-deploy osd create --data /dev/vde ceph-02
ceph-deploy osd create --data /dev/vde ceph-03
```

- 如果要在LVM卷上创建OSD，则参数 `--data` *必须*是`volume_group/lv_name`，而不是卷的块设备的路径。

#### 3.1.6、将配置文件同步到其他节点

```
ceph-deploy --overwrite-conf admin ceph-01 ceph-02 ceph-03
```

#### 3.1.7、检查集群状态

```
ceph -s
```

- 您的群集应该报告`HEALTH_OK`

- 如OSD未启动，使用以下命令启动相应节点，@后面为OSD ID

  ```
  systemctl start ceph-osd@0
  ```

#### 3.1.8、部署MDS元数据服务

要使用CephFS，您至少需要一个元数据服务器。

```
ceph-deploy mds create ceph-01 ceph-02 ceph-03
```

#### 3.1.9、添加监视器

​	Ceph存储集群需要至少运行一个Ceph Monitor和Ceph Manager。为了实现高可用性，Ceph存储集群通常运行多个Ceph监视器，因此单个Ceph监视器的故障不会导致Ceph存储集群崩溃。Ceph使用Paxos算法，该算法需要大多数监视器（即大于*N / 2*，其中*N*是监视器的数量）才能形成法定数量。虽然这不是必需的，但监视器的数量往往更好。

将两个Ceph监视器添加到您的群集：

```
ceph-deploy mon add ceph-01 ceph-02
```

一旦你添加了新的Ceph监视器，Ceph将开始同步监视器并形成一个法定人数。您可以通过执行以下操作来检查仲裁状态：

```
ceph quorum_status --format json-pretty
```

#### 3.1.10、添加管理员

​	Ceph Manager守护进程以活动/备用模式运行。部署其他管理器守护程序可确保在一个守护程序或主机发生故障时，另一个守护程序或主机可以在不中断服务的情况下接管。

```
ceph-deploy mgr create ceph-02 ceph-03
```

- 使用ceph -s，您应该可以看到备用管理器

#### 3.1.11、添加RGW实例

要使用[Ceph的Ceph对象网关](http://docs.ceph.com/docs/master/glossary/#term-ceph-object-gateway)组件，必须部署[RGW](http://docs.ceph.com/docs/master/glossary/#term-rgw)实例。执行以下命令以创建RGW的新实例：

```
ceph-deploy rgw create ceph-01
```

默认情况下，[RGW](http://docs.ceph.com/docs/master/glossary/#term-rgw)实例将侦听端口7480.可以通过在运行[RGW](http://docs.ceph.com/docs/master/glossary/#term-rgw)的节点上编辑ceph.conf来更改此设置，如下所示：

```
[client]
rgw frontends = civetweb port=80
```

要使用IPv6地址，请使用：

```
[client]
rgw frontends = civetweb port=[::]:80
```

#### 3.1.12、创建存储对象

要将对象数据存储在Ceph存储集群中，Ceph客户端必须：

1. 设置对象名称
2. 指定一个pool

Ceph客户端检索最新的集群映射，CRUSH算法计算如何将对象映射到[放置组](http://docs.ceph.com/docs/master/rados/operations/placement-groups)，然后计算如何动态地将放置组分配给Ceph OSD守护进程。要查找对象位置，您只需要对象名称和池名称。例如：

```
ceph osd map {poolname} {object-name}
```

查看pool

```
ceph osd pool ls
```

创建pool

```
ceph osd pool create {poolname} 64
```

- 创建一个名为{poolname}的存储池，pg = 64

删除pool

```
ceph osd pool rm {poolname}
```

####3.1.13、创建文件系统

查看文件系统

```
ceph fs ls
```

创建文件系统

```
ceph osd pool create <data_name> <pg_num>
ceph osd pool create <metadata_namw> <pg_num>
ceph fs new <fs_name> <metadata_namw> <data_name>
```

```
ceph osd pool create es_data 128
ceph osd pool create es_metadata 128
ceph fs new es es_metadata es_data
ceph fs ls
ceph mds stat
```



使用文件系统

```
yum -y install ceph-fuse
```

复制ceph.conf 与 ceph.client.admin.keyring 文件到主机

查看文件系统编号

```
ceph fs dump
```

创建挂载目录，并进行挂载

```
ceph-authtool -l /etc/ceph/ceph.client.admin.keyring
[client.admin]
        key = AQAEKJFa54MlFRAAg76JDhpwlHD1F8J2G76baQ==
```

```
mount -t ceph 172.24.10.21:6789:/ /data/ceph-storage/ -o name=admin,secret=AQAEKJFa54MlFRAAg76JDhpwlHD1F8J2G76baQ==
```



```
test -d /data || mkdir /data
ceph-fuse -m ceph-01,ceph-02,ceph-03:6789 /data/files
```

####3.1.14、清除操作

安装中出错，可以通过以下步骤清除操作：

```
ceph-deploy purge {ceph-node} [{ceph-node}]
ceph-deploy purgedata {ceph-node} [{ceph-node}]
ceph-deploy forgetkeys
rm -rf ceph.*
```



## 四、注意事项

### 4.1、为何网络分离

- 性能

  OSD 为客户端处理数据复制，复制多份时 OSD 间的网络负载势必会影响到客户端和 ceph 集群 的通讯，包括延时增加、产生性能问题;恢复和重均衡也会显著增加公共网延时。

- 安全

  很少的一撮人喜欢折腾拒绝服务攻击(DoS)。当 OSD 间的流量瓦解时， 归置组再也不能达到 active+clean 状态，这样用户就不能读写数据了。挫败此类攻击的一种好方法是 维护一个完全独立的集群网，使之不能直连互联网;另外，请考虑用签名防止欺骗攻击。

### 4.2、分离公共网络和集群网络(推荐、可选)

修改ceph.conf

```
[global]

# 注意替换 fsid
fsid = dca70270-3292-4078-91c3-1fbefcd3bd62

mon_initial_members = ceph-0,ceph-1,ceph-2
mon_host = 192.168.50.20,192.168.50.21,192.168.50.22
auth_cluster_required = cephx
auth_service_required = cephx
auth_client_required = cephx

public network  = 192.168.50.0/24
cluster network = 172.20.0.0/24

[mon.a]
host = ceph-0
mon addr = 192.168.50.20:6789

[mon.b]
host = ceph-1
mon addr = 192.168.50.21:6789

[mon.c]
host = ceph-2
mon addr = 192.168.50.22:6789

[osd]
osd data = /var/lib/ceph/osd/ceph-$id
osd journal size = 20000
osd mkfs type = xfs
osd mkfs options xfs = -f

filestore xattr use omap = true
filestore min sync interval = 10
filestore max sync interval = 15
filestore queue max ops = 25000
filestore queue max bytes = 10485760
filestore queue committing max ops = 5000
filestore queue committing max bytes = 10485760000

journal max write bytes = 1073714824
journal max write entries = 10000
journal queue max ops = 50000
journal queue max bytes = 10485760000

osd max write size = 512
osd client message size cap = 2147483648
osd deep scrub stride = 131072
osd op threads = 8
osd disk threads = 4
osd map cache size = 1024
osd map cache bl size = 128
osd mount options xfs = "rw,noexec,nodev,noatime,nodiratime,nobarrier"
osd recovery op priority = 4
osd recovery max active = 10
osd max backfills = 4

[client]
rbd cache = true
rbd cache size = 268435456
rbd cache max dirty = 134217728
rbd cache max dirty age = 5
```

### 4.3、重启各个节点

```
systemctl restart ceph\*.service ceph\*.target
```

### 4.4、RBD

- 关于 rbd 的更多信息，请参阅文档 [RBD – MANAGE RADOS BLOCK DEVICE (RBD) IMAGES]](<http://docs.ceph.com/docs/master/man/8/rbd/>)

- 若要在其它主机上使用 rbd, 需安装 ceph-common (提供 rbd 命令), 否则将无法创建文件系统（对于 k8s, kube-controller-manager 所在系统也需要安装 ceph-common）



## 五、测试

### 5.1、使用 rados bench 测试 rbd

使用 `rados -p rbd bench 60 write` 进行 顺序写入

```
rados -p rbd bench 60 write
```

使用 `rados -p rbd -b 4096 bench 60 write -t 256 --run-name test1` 进行 4k 写入

```
rados -p rbd -b 4096 bench 60 write -t 128 --run-name test1
```

rados bench 更多信息请参阅 官方文档(http://docs.ceph.com/docs/master/)

### 5.2、使用 fio 测试 ceph-fs

安装fio

```
yum install -y fio
```

进入ceph-fs挂载目录内，执行测试

```
fio -direct=1 -iodepth=128 -rw=randwrite -ioengine=libaio -bs=4k -size=1G -numjobs=1 -runtime=1000 -group_reporting -filename=iotest -name=Rand_Write_Testing
```


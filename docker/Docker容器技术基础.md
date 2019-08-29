[TOC]

## 一、Docker简介

### 1.1、什么是Docker

​	Docker是在2013年由dotCloud发起的一个开源项目，使用Go语言进行开发，基于LInux内核的cgroup、namespace等技术，对进程进行封装隔离，属于操作系统层面的虚拟化技术。

​	Docker基于LXC的基础上进一步封装，从文件系统、网络互联到进程隔离等等，极大简化了容器的创建和维护，使Docker技术比虚拟机技术更为轻便、快捷。

![docker1](../images/docker1.png)



### 1.2、为什么使用Docker

- 更高效的系统资源利用率

  ​	由于容器不需要进行硬件虚拟化以及运行完整操作系统等额外开销，Docker对系统资源利用率更高。无论是应用执行速度、内存损耗或者文件存储速度，都要比传统虚拟机技术更高效。因此，相比虚拟机技术，一个相同配置的主机，往往可以运行更多数量的应用。

- 更快速的启动时间

  传统虚拟机技术启动应用服务因需要启动完整的操作系统，往往需要数分钟，而Docker容器应用运行于宿主机内核，无需启动完整的操作系统，因此可以做到秒级、甚至毫秒级启动。大大节约了开发、测试、部署的时间。

- 环境一致性

  开发过程中一个常见的问题是环境一致性问题。由于开发、测试、预发布、生产环境不一致，导致有些问题未及时发现。而Docker的镜像提供了除内和外完整的运行时环境，确保了应用运行环境一致性。

- 更高效的持续交付和部署

  通过Docker可以定制应用镜像实现持续集成、持续交付、持续部署，可以很容器的部署或迁移到另一个平台，而不用担心运行环境的变化导致应用无法正常运行。

- 更轻松的维护和扩展

  Docker使用分层存储以及镜像的技术，可以更容易的复用应用重复部分，应用的部署、运维也更加简单。

对比传统虚拟机总结：

| 特性       | 容器               | 虚拟机       |
| ---------- | ------------------ | ------------ |
| 启动       | 秒级               | 分钟级       |
| 硬盘使用   | 一般为MB           | 一般为GB     |
| 性能       | 接近原生           | 弱于原生     |
| 系统支持量 | 单机支持上千个容器 | 一般为几十个 |



## 二、基本概念

Docker包含了三大基本概念：

- 镜像(Image)

  Docker镜像是一个特殊的文件系统，除了提供容器运行时所需的程序、库、资源、配置等文件外，还包含了一些为运行时准备的一些配置参数（如环境变量、用户等）。镜像不包含任何动态数据，其内容在构建之后也不会被改变，这个和容器的根本区别。

- 容器(Container)

  镜像和容器的关系，就像是面向对象程序设计中的**类**和**实例**一样，镜像是静态的定义，容器是镜像运行时的实体。容器可以被创建、启动、停止、删除、暂停等。容器运行时，以镜像为基础层（镜像本身时只读的），在其上创建一个可写层，镜像本身时保持不变的。

- 仓库(Repository)

  Docker仓库类似于代码仓库，是Docker集中存放镜像文件的地方。很多时候有人会将Docker仓库和注册服务器（registry）混为一谈。实际上，注册服务器是存放仓库的地方，可以包含多个仓库；每个仓库可以包含多个标签（tag）；每个标签对应一个镜像。



## 三、Docker安装

### 3.1、Ubuntu

安装必要的一些系统工具

```
apt-get -y install apt-transport-https ca-certificates curl software-properties-common
```

安装GPG证书

```
curl -fsSL http://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg | sudo apt-key add -
```

添加软件源

```
add-apt-repository "deb [arch=amd64] http://mirrors.aliyun.com/docker-ce/linux/ubuntu $(lsb_release -cs) stable"
```

安装Docker

```
apt-get -y update
apt-get -y install docker-ce
```

安装指定版本：

查询docker版本

```
apt-cache madison docker-ce
```

安装指定版本(VERSION 例如18.06.1~ce-0~ubuntu-xenial)

```
apt-get -y install docker-ce-[VERSION]
```

### 3.2、CentOS7

安装必要的一些系统工具

```
yum -y install yum-utils device-mapper-persistent-data lvm2
```

添加软件源

```
yum-config-manager --add-repo http://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
```

安装Docker

```
yum makecache fast
yum -y install docker-ce
```

安装指定版本：

查询docker版本

```
yum list docker-ce --showduplicates | sort -r
```

安装指定版本(VERSION 例如18.09.0.ce.1-1.el7.centos)

```
yum -y install docker-ce-[VERSION]
```



### 3.3、Docker配置文件

```
cat > /etc/docker/daemon.json <<EOF
{
 "registry-mirrors": ["https://registry.docker-cn.com"],
 "exec-opts": ["native.cgroupdriver=systemd"],
 "storage-driver": "overlay2",
 "storage-opts":["overlay2.override_kernel_check=true"],
 "graph": "/data/data/docker",
 "log-driver": "json-file",
 "log-opts": {
     "max-size": "500m",
     "max-file": "10"
 },
 "oom-score-adjust": -1000,
 "bip": "192.168.100.1/24"
}
EOF
```

注意：

- registry-mirrors指定镜像加速地址，这里指定官方在国内的地址
- insecure-registries指定私有docker仓库地址
- docker默认存放路径在/var/lib/docker下，graph可以自定义存放路径。
- bip可以指定docker运行的网段



## 四、Docker常用操作

### 4.1、操作容器

从镜像创建并启动容器(需要注意的是，容器运行在后台模式下，是不能使用`--rm`选项的。)

```
docker run -itd -p 8080:8080 -v /data:/data --name k8s registry.k8sre.com/library/alpine:3.9
docker container run -it --rm registry.k8sre.com/library/alpine:3.9
```

说明：

1、-t 选项让Docker分配一个伪终端并绑定到容器的标准输入上

2、-i 选项让容器的标准输入保持打开

3、-d选项让容器可以后台运行

4、当操作者执行`docker run --privileged --privileged=true` 时，Docker将拥有访问主机所有设备的权限，同时Docker也会在apparmor或者selinux做一些设置，使容器可以容易的访问那些运行在容器外部的设备。

查看容器

```
docker ps 			#列出当前正在运行的容器
docker ps -a		#列出所有的容器，包括正在运行的和其他未运行的
docker ps -l		#列出最近一次启动的容器
docker ps -a -q		#列出所有容器的CONTAINER_ID
docker container ls -a #列出所有容器
```



启动/停止/重启/删除容器(新版本逐步使用docker container来管理容器)

```
docker start xxxx
docker stop xxxx
docker restart xxxx
docker rm -f xxxx
docker container prune -f #清理停止状态的容器
docker container prune --filter "until=24h" #删除 24 小时之前创建的停止状态的容器
```

进入容器

```
docker attach xxxx
docker exec -it xxxx
```

注意：使用docker attach从这个sedin中exit，会导致容器的停止，而docker exec并不会。所以推荐大家使用docker exec。

导出和导入容器

```
docker save alpine:3.9 -o xxx.tar 
docker load -i xxx.tar
```

```
docker export alpine:3.9 > alpine.tar
cat alpine.tar | docker import - registry.k8sre.com/library/alpine:3.9
```

注意：既可以使用docker load来导入镜像文件到本地镜像库，也可以使用docker import来导入一个容器快照到本地镜像库。这两者的区别在于docker import导入容器快照文件将丢弃所有的历史记录和元数据信息（即仅保存容器当时的快照状态），而docker load导入镜像存储文件将保存完整记录，体积也要大。此外容器快照文件导入时可以重新制定标签等元数据信息。

宿主机与容器间传文件

```
docker cp -r /root/tomcat.tar.gz CONTAINER_ID:/root	#从宿主机复制到容器
docker cp -r CONTAINER_ID:/root/tomcat.tar.gz /root/	#从容器复制到宿主机
```

创建并使用存储卷

```
docker run -v /data/downloads:/usr/downloads  --name dataVol ubuntu64 /bin/bash
docker run -it --volumes-from dataVol ubuntu64 /bin/bash
```



### 4.2、操作镜像

docker1.13+推荐使用docker image管理镜像

从Dockerfile构建镜像

```
docker build -t registry.k8sre.com/libary/alpine:3.9 .
```

将运行的容器保存为镜像

```
docker commit -a "作者名字" -m "说明文字" 容器ID 镜像名:tag
```

搜索/获取镜像

```
docker search ubuntu
docker pull [选项] [Docker Registry地址]<仓库名>:<标签>
docker image pull ubunut:18.04		
```

查看镜像

```
docker images -q
docker history IMAGE_ID		#查看镜像内的历史记录
docker image ls	
docker images --format "table {{.ID}}\t{{.Repository}}\t{{.Tag}}" #自定义结构查看镜像
```

**删除镜像**

清理 dangling 镜像。dangling 镜像是没被标记且没被其它任何镜像引用的镜像

```
docker image prune -f
```

通过 `-a` 标志可以删除没有被已有容器使用的所有镜像

```
docker image prune -a -f
```

可以使用 `--filter` 标志使用过滤表达式来限制清理哪些镜像，例如，只考虑 24 小时前创建的镜像

```
docker image prune -a --filter "until=24h"
```

**推送镜像到仓库**

```
docker login -u k8sre registry.k8sre.com
docker tag IMAGE_ID registry.k8sre.com/libary/xxx:xxx
docker push registry.k8sre.com/libary/xxx:xxx
```

### 4.3、其他常用命令

```
docker system df            //显示Docker磁盘使用状态
docker system events        //显示Docker服务实时事件信息
docker system info          //显示系统信息
docker system prune         //删除未使用的数据
```

```
docker trust inspect        //返回Key和签名的低级别信息
docker trust key            //管理用于镜像签名的Key
docker trust revoke         //撤销对镜像的签名
docker trust sign           //对镜像进行签名
docker trust signer         //管理可以对镜像签名的用户
```

```
docker volume create       //创建一个卷
docker volume insoect      //显示一或多个卷的详细信息
docker volume ls           //列出卷
docker volume prune        //删除所有未使用的卷
docker volume rm           //删除一或多个卷
```

```
docker pause xxxx          //暂停一或多个容器内所有进程
docker unpause xxxx        //取消暂停一或多个容器内所有进程
docker port xxxx           //列出容器与主机的端口映射
docker rename xxx          //重命名容器名称
docker diff                //查看容器文件系统内有差异的文件
docker stats xxx           //实时输出指定容器的资源使用状态
docker top xxxx            //显示指定容器运行中的进程信息
docker update              //更新一或多个容器配置,如资源配额、重启策略等等
docker wait xxx            //捕捉一或多个容器的退出状态
```





## 五、Docker网络实现和文件系统

### 5.1、Docker的网络模式

​	Docker的网络实现利用了Linux上网络命名空间和虚拟网络设备（特别是veth pair）。熟悉这两部分的基本概念，可以有助于理解Docker网络的实现过程。

#### 5.1.1、基本原理

​	要实现网络通信，主机需要至少一个网络接口（物理接口或虚拟接口）与外界相通，并可以收发数据包；此外，如果不同子网之间要进行通信，需要额外的路由机制。

​	Docker中的网络接口默认都是虚拟的接口。虚拟接口的最大优势就是转发效率极高。这是因为Linxu通过在内核中进行数据复制来实现虚拟接口之间的数据转发，即发送接口的发送缓存中的数据包将被直接复制到接收接口的接收缓存中，而无需通过外部物理网络设备进行交换。对于本地系统和容器内系统来看，虚拟接口跟一个正常的以太网卡相比并无区别，只是它速度要快得多。

​	Docker容器网络就很好的利用了Linux虚拟网络技术。它在本地主机和容器内分别建立一个虚拟接口，并让它们彼此连通（这样的一对接口叫做veth pair）。

![docker2](../images\docker2.png)

#### 5.1.2、网络创建过程

Docker创建一个容器的时候，会执行以下操作：

​	1、创建一对虚拟接口，分别放到本地主机和新容器的命名空间中。

​	2、本地主机一端的虚拟接口连接到默认的docker0网桥，并具有一个veth开头的唯一名字。

​	3、容器一端的虚拟接口将放到新创建容器中，并修改名字作为eth0。这个接口只在容器的命名空间中可见。

​	4、从网桥可用的地址段中获取一个空闲地址分配给容器的eth0，并配置默认路由网关为docker0网卡的内部接口docker0的IP地址。

​	5、此时，容器就可以使用它所能看到的eth0虚拟网卡来连接其他容器和访问外部网络了。

#### 5.1.3、常见Docker网络模型

- bridge

  通过veth接口来连接容器，*默认配置*。

- host

  不将容器网络放到隔离的命名空间中，即不要容器化容器内的网络。可以使用本地主机的网络，它拥有完全的本地主机接口访问权限。容器进程可以跟主机其他root进程一样打开低范围端口，可以访问本地网络服务（比如D-bus），还可以让容器做一些影响主机系统的事情，比如重启主机等。因此使用这个选项的时候要谨慎，如果进一步的使用--privileged=true参数，容器甚至会被允许直接配置主机的网络堆栈。

- container

  将新建的容器的进程放到一个已存在容器的网络栈中，新容器进程有自己的文件系统、进程列表、资源限制，但会和已存在的容器共享IP地址和端口等网络资源，两者进程可以直接通过lo环回接口通信。

- none

  将新建容器放到隔离的网络栈中，但是不进行网络配置。之后，用户可以自己进行配置。

#### 5.1.4、网络配置

​	用户使用--net=none后，Docker将不对容器网络进行配置，可以使用以下方式进行配置：

启用一个网络为none的容器

```
docker run -it --net=none alpine /bin/bash
```

查找容器进程id

```
docker inspect -f '{{.State.Pid}}' container_id
```

查看docker0网络信息

```
ip addr show docker0
```

创建一对”veth pair“接口A和B，绑定其中一个到docker0

```
ip link add A type veth peer name B
brctl addif docker0 A
ip link set A up
```

将B接口放到容器的网络命名空间，命名为eth0

```
ip link set B netns $PID
ip netns exec $PID ip link set dev B name eth0
ip netns exec $PID ip link set eth0 up
```

配置容器网络和网关

```
ip netns exec $PID ip addr add 172.17.1.2/24 dev eth0
ip netns exec $PID ip route add default via 172.17.1.1
```

以上就是Docker网络的配置过程。

当容器终止后，Docker会清空容器，容器内的网络接口会随网络命名空间一起被清除，A接口也被自动从docker0卸载并清除。

此外，在删除/var/run/netns/下的内容之前，用户可以使用ip netns exec 命令指定网络命名中进行配置，从而影响容器内的网络。

### 5.2、Docker联合文件系统

#### 5.2.1、基本原理

​	联合文件系统（UnionFS）是一种轻量级的高性能分层文件系统，它支持将文件系统中的修改信息作为一次提交，并层层叠加，同时可以将不同目录挂载到同一个虚拟文件系统下。

联合文件系统是实现Docker镜像的技术基础。镜像可以通过分层来继承。例如，用户基于基础镜像（没有父镜像的镜像成为基础镜像）来制作各种不同的应用镜像。这些镜像共享同一个基础镜像曾，提高了存储效率。此外，当用户改变一个Docker镜像，则一个新的层（layer）会被创建。因此，用户不用替换整个原镜像或者重新建立，只要添加新层即可用户分发镜像的时候，也只需要分发被改动的新层内容（增量部分）。这让Docker的镜像管理变得十分轻量级和快速。

![docker3](../images\docker3.jpg)

#### 5.2.2、Docker常见联合文件系统

- devicemapper

  1、建议不要在生产环境使用此存储方案

  2、本地文件容易丢失，且不容易扩展空间

  3、从性能上而言，本地文件挂接方式让存储结构跟复杂且性能更低

  4、本地文件在集群和分布式存储方式中让系统架构更加复杂

  5、不能很好的体现data数据和meta数据分离的优越性

- overlay

  1、RHEL/CentOS 必须是 7.2 或以上版本

  2、Docker必须是最新版本，并且支持Overlay

  3、底层文件系统必须是XFS

  4、SELinux在宿主机上必须打开设为enforcing模式，但docker服务启动时不能打开支持selinux选项，不能设置"--selinux-enabled"。目前RHEL 7.2系统还不支持overlay下的selinux

  5、为了支持yum和rpm工具在以overlay为基础的容器中正常运行，需要安装yum-plugin-ovl软件包。

- overlay2

  1、overlay2 是 overlay 的升级，与overlay的结构基本相同

  2、使用了从写的函数，在存储上是不兼容的，因此从overlay升级的话需要删除所有的镜像和容器

  3、Overlay2解决了overlay inode损耗和提交（commit）性能问题，但是只在Docker 1.11之后的版本才能实现

  4、overlay2在docker 18之前的版本需要升级内核版本才可以使用，目前最新版已经不需要升级内核即可使用





## 六、Dockerfile详解

​	镜像的定制实际上就是定制每一层所添加的配置文件。如果我们可以把每一层修改、安装、构建、操作的命令都写入一个脚本，用这个脚本来定制、构建镜像，那么无法重复、镜像构建透明性、镜像体积的问题都会解决。这个脚本就是Dockerfile。

​	Dockerfile是一个文本文件，其内包含了一条条的指令，所有指令都是在开头，并且必须为大写字母，每一条指令构建一层，因此每一条指令的内容，就是描述该层当如何构建。Dockerfile的指令会按从上到下的顺序执行。

- FROM：指定基础镜像

  所谓定制镜像，那一定是以一个镜像为基础的，在其上进行定制，而FROM就是指定基础镜像，因此Dockerfile中FROM是必备的指令，并且必须是第一条指令。

- RUN：执行命令

  RUN指令是用来执行命令行命令的，由于命令行的强大能力，RUN指令是在定制镜像时最常用的指令之一。其格式有两种：

  - shell格式：RUN <命令>，就像直接在命令行种输入的命令一样。
  - exec格式：RUN [“可执行文件”,“参数1”,"参数2"]，这更像是函数调用种的格式。

  ​      因每一条指定构建一层，当有多个shell格式的RUN指令时，尽量使用&&将各个命令串联起来，简化镜像层。Dockerfile支持shell类的行尾添加\的命令换行方式，以及行首#进行注释的格式。良好的格式，比如换行、缩进、注释等，会让维护、排障更为容易，这是一个比较好的习惯。

  ​       此外，在指令结束时务必进行缓存清理，之前说过，镜像时多层的，每一层的东西并不会在下一层被删除，会一直跟随着镜像。因此镜像构建时，一定确保每一层只添加真正需要的东西，任何无关的东西都应该清理掉。很多初学者制作令很臃肿的镜像的原因之一，就是忘记了每一层构建的最后一定要清理掉无关文件。

- COPY：复制文件

  格式：

  - COPY <源路径> …<目标路径> 
  - COPY ["<源路径1>",..."<目标路径>"]

  ​       和RUN指令一样，也有两种格式，一种类似命令行，一种类似于函数调用。COPY指令将从构建上下文目录<源路径>的文件/目录复制到新的一层镜像内的<目标路径>指定位置。

  ​       <源路径>可以是多个，甚至可以是通配符，其通配符规则要满足GO的规则。

  ​      <目标路径>可以是容器内的绝对路径，也可以是相对于工作目录的相对路径（工作目录可以用WORKDIR指令来指定）。目标路径不需要事先创建，如果目录不存在会在复制文件前先行创建缺失目录。

  ​      此外，还需要注意一点，使用COPY指令，源文件的各种元数据都会保留。比如读、写、执行权限、文件变更时间等。这个特性对于镜像定制很有用。

- ADD：更高级的复制文件

  ​	ADD指令和COPY的格式和性质基本一致。但是在COPY基础上增加了一些功能。比如<源路径>可以是一个URL，这种情况下，Docker引擎会试图去下载这个链接的文件放到<目标路径>去。下载后的文件权限自动设置为600，如果这并不是想要的权限，那么还需要增加额外的一层RUN进行权限调整，另外，下载的是个压缩包，需要使用额外一层RUN进行解压缩。所以不如直接使用RUN指令，然后wget、curl下载，处理权限、解压缩、然后清理无用文件更合理。因此，这个功能其实并不实用，而且不推荐。

  ​	如果<源路径>为一个tar压缩文件的话，压缩格式为gzip、bzip2、xz的情况下，ADD指令将会自动解压缩。

  ​	在Docker官方文档中，ADD指令会令镜像构建缓存失效，从而可能会令镜像变得比较缓慢。因此，尽可能的使用COPY，因为COPY语义很明确，就是复制文件而已，而ADD则包含了更复杂的功能，其行为也不一定很清晰。最适合使用ADD的场合，就是自动解压缩的场合。

  

- CMD：容器启动命令

  CMD指令的格式和RUN相似，也是两种格式：

  - shell格式：CMD <命令>
  - exec格式：CMD [“可执行文件”,"参数1","参数2"...]
  - 参数列表格式：CMD ["参数1","参数2"…]。在指定了CNTRYPOINT指令后，用CMD指定具体参数。

  ​        Docker不是虚拟机，容器就是进城。既然是进程，那么在启动容器的时候，需要指定所运行的程序及参数。CMD指令就是用于指定默认的容器主进程的启动命令。在运行时可以指定新的命令来替代镜像设置中的这个默认命令。

  ​	在指令格式上，一般推荐使用exec格式，这类格式在解析时会被解析喂JSON数组，因此一定要使用双引号，而不是单引号。如果使用shell格式的话，实际的命令会被包装为`sh -c`的参数的形式进行执行。

  ​	Docker不是虚拟机，容器中的应用都应该在前台执行，而不是像虚拟机、物理机里面那样，用upstart/systemd去启动后台服务，容器内没有后台服务的概念。

  ```
  CMD ["nginx","-g","daemon off"]
  ```

  

- ENTRYPOINT：接入点

  ​	ENTRYPOINT的格式和RUN指令的格式一样，分为exec格式和shell格式。ENTRYPOINT的目的和CMD一样，都是在指定容器启动程序及参数。ENTRYPOINT在运行时也可以替代，需要通过--entrypoint来指定。

  ​	当指定来ENTRYPOINT后，CMD的含义就发生了改变，不再是直接运行其命令，而是将CMD的内容作为参数传给ENTRYPOINT指令。

- ENV：设置环境变量

  格式有两种：

  - ENV <key> <value>
  - ENV <key1>=<value1> <key2>=<value2>

  ​        这个指令很简单，就是设置环境变量而已，无论是后面的其它指令，如RUN，还是运行时的应用，都可以直接使用这里定义的环境变量。

- ARG：构建参数

  格式：ARG <参数名> [=<默认值]

  ​	构建参数和ENV的效果一样，都是设置环境变量。不同的是，ARG所设置的构建环境的环境变量，在将来容器运行时是不会存在这些环境变量的。但是不要因此就使用ARG保存密码之类的信息，因为`docker history`还是可以看到所有值的。

  ​	Dockerfile中的ARG指令时定义参数名称，以及定义其默认值。该默认值可以在构建命令`docker build `中用`--build-arg <参数名>=<值>`来覆盖。

  ​	在1.13之前的版本，要求`--build-arg`中的参数名，必须在Dockerfile中用ARG定义过了，换句话说，就是`--build-arg`指定的参数，必须在Dockerfile中使用了。如果对应参数没有被使用，则会报错退出构建。从1.13开始，这种严格的限制被放开，不再报错退出，而是现实警告信息，并继续构建。这对于使用CI系统，用同样的构建流程构建不同的Dockerfile的时候比较有帮助，避免构建命令必须根据每个Dockerfile的内容修改。

- VOLUME：定义存储卷

  格式：

  - VOLUME ["<路径1>","<路径2>"...]
  - VOLUME <路径>

  ​        之前我们说过，容器运行时应该尽量避免容器存储层不发生写操作，对于数据库类需要保存动态数据的应用，其数据库文件应该保存于卷（volume）中，在Dockerfile中，我们可以事先指定某些目录挂载为匿名卷，这样在运行时如果忘记指定挂载，其应用也可以这个正常运行，不会向容器存储层写入大量数据。

- EXPOSE：声明端口

  格式： EXPOSE <端口1> [<端口2>…]。

  ​	EXPOSE指令时声明运行时容器提供服务端口，这只是一个声明，在运行时并不会因为这个声明应用就会开启这个端口的服务。

- WORKDIR：指定工作目录

  格式： WORKDIR <工作目录路径>。

  ​	使用WORKDIR指令可以来指定工作目录（或者称为当前目录），以后各层的当前目录就被改为指定的目录，如该目录不存在，WORKDIR会帮你创建目录。

- USER：指定当前用户

  格式：USER <用户名>

  ​	USER指定和WORKDIR相似，都是改变环境状态并影响以后层。WORKDIR是改变工作目录，USER则是改变之后层的执行RUN、CMD以及ENTRYPOINT这类命令的身份。

  ​	USER只是帮助你切换到指定用户而已，这个用户必须是事先创建好的，否则无法切换。

- HEALTHCHECK：健康检查

  格式：

  - HEALTHCHECK [选项] CMD <命令> ：设置检查容器健康状况的命令
  - HEALTHCHECK NONE ：如果基础镜像有健康检查指令，使用这行可以屏蔽掉其健康检查指令

  ​        HEALTHCHECK指令是Docker应该如何进行判断容器的状态是否正常，这是Docker1.12引入的新指令。通过该指令指定一行命令，用这行命令来判断容器主进程的服务状态是否正常，从而比较真实的反应容器实际状态。

  ​	当一个镜像指定了HEALTHCHECK指令后，用其启动容器，初始状态会为starting，在HEALTHCHECK指令检查成功后变为healthy，如果连续一定次数失败，则会变为unhealthy。

  HEALTHCHECK支持下列选项：

  - --interval=<间隔> ：两次健康检查的间隔，默认为30秒。
  - --timeout=<时长> ：健康检查命令运行超时时间，如果超过这个时间，本次健康检查就被视为失败，默认30秒。
  - --retries=<次数> ：当连续失败指定次数后，则将容器状态视为unhealth，默认3次。

  ​       和CMD、ENTRYPOINT一样，HEALTHCHECK只可以出现一次，如果写了多个，只有最后一个生效。在`HEALTHCHECK [选项] CMD` 后面的命令，格式和ENTRYPOINT一样，分为shell格式和exec格式。命令的返回值决定了该次健康检查的成功与否：0:成功；1:失败；2:保留。不要使用这个值。

  

- ONBUILD：为他人做嫁衣

  格式：ONBUILD <其他指令>。

  ​	ONBUILD是一个特殊的指令，它后面跟的是其它指令，比如RUN、COPY等，而这些指令，在当前镜像构建时并不会被执行。只有当以当前镜像为基础镜像，去构建下一级镜像的时候才会被执行。Dockerfile中的其它指令都是为了定制当前镜像而准备的，唯有ONBUILD是为了帮助别人定制自己而准备的。



## 七、Docker核心技术

​	Docker采用了标准的C/S架构，包括客户端和服务端两大部分。

​	客户端可以和服务端机可以运行在一个机器，也可以通过socket或者RESTful API来进行通信。

### 7.1、服务端

​	Docker daemon一般在宿主机后台运行，作为服务端接受来自客户的请求，并处理这些请求（创建、运行、分发容器）。在设计上，Docker daemon是一个非常松耦合的架构，通过专门的ENgine模块来分发管理各个来自客户端的任务。

​	Docker服务端默认监听本地的unux:///var/run/docker.sock套接字，只允许本地的root用户访问。可以通过-H选项修改监听方式。

```
docker -H 0.0.0.0:666 -d &
```

此外，Docker还支持通过HTPPS认证方式来验证访问。

### 7.2、客户端

​	Docker客户端为用户提供了一系列可执行命令，用户通过这些命令实现与Docker daemon的交互。

​	用户使用的Docker可执行命令即为客户端程序。与Docker daemon不同的是，客户端发送命令后，等待服务端返回，一旦收到返回后，客户端立刻执行结束并退出。用户执行新的命令，需要再次调用客户端命令。

​	同样，客户端默认通过本地的unux:///var/run/docker.sock套接字向服务端发送命令。如果服务端没有监听到默认套接字，则需要客户端在执行命令的时候显式指定。

```
docker -H tcp://127.0.0.1:666 version
```

### 7.3、命令空间

​	命令空间（Namespace）是Linux内核针对实现容器虚拟化而引入的一个强大特性。

​	每个容器都可以拥有自己单独的命名空间，运行在其中的应用都像是在独立的操作系统中运行一样。命名空间保证了容器之间互不影响。

​	众所周知，在操作系统中，包括内核、文件系统、网络、PID、UID、IPC、内存、硬盘、CPU等资源，所有的资源都是应用进程直接共享的。要想实现虚拟化，除了要实现对内存、CPU、网络IO、硬盘IO、存储空间等的限制外，还要实现文件系统、网络、PID、UID、IPC等等的相互隔离。前者相对实现容易实现一些，后者则需要宿主机系统的深入支持。

​	随着Linux系统的逐步完善，已经实现让某些进程在彼此隔离的命名空间中运行，这些进程都共用一个内核和某些运行时环境（runtime），但是彼此是不可见的-它们各自认为是自己独占系统的。

#### 7.3.1、进程命名空间

​	Linux通过命名空间管理进程号，对于同一个进程（同一个task_struct），在不同的命名空间中，看到的进程号不相同，每个进程命名空间有一套自己的进程号股那里方法。进程命名空间是一个父子关系的结构，子空间中的进程对于父空间是可见的。新fork出的进程在父命名空间个子命名空间将分别由一个进程号来对应。

#### 7.3.2、网络命名空间

​	如果有了PID命名空间，那么每个名字空间中的进程就可以相互隔离，但是网络端口还是共享本地系统的端口，

​	通过网络命名空间，可以实现网络隔离。一个网络命名空间为进程提供了一个完全独立的网络协议栈的视图。包括网络设备接口、IPv4和IPv6协议栈、IP路由表】防火墙规则，Sockets等等。这样每个容器的网络就能隔离。Docker采用虚拟网络设备（Virtual Network Device）的方式，将不同命名空间的网络设备连接到一起。默认情况下，容器中的虚拟网卡将同本地主机上的docker0网桥连接在一起。

查看桥街道宿主机docker0网桥的虚拟网口：

```
brctl show
```

#### 7.3.3、IPC命名空间

​	容器中进程交互还是采用了LInux常见的进程间交互方法（Interprocess Communication IPC），包括信号量、消息队列和共享内存等。PID命名空间和IPC命名空间可以组合起来一起使用，同一个IPC名字空间内的进程可以彼此可见，允许进行交互；不同名字空间的进程则无法交互。

#### 7.3.4、挂载命名空间

​	类似chroot，将一个进程放到一个特定的目录执行。挂载命名空间运行不同命名空间的进程看到的文件结构不同，这样每个命名空间中的进程所看到的文件目录彼此隔离。

#### 7.3.5、UTS命名空间

​	UTS（UNIX Time-sharing System）命名空间允许每个容器拥有独立的主机名和域名，从而可以虚拟出一个独立主机名和网络空间的环境，就跟网络上一台独立的主机一样。

#### 7.3.6、用户命名空间

​	每个容器可以有不同的用户和组ID，也就是说可以在容器内使用特定的内部用户执行程序，而非本地系统上存在的用户。

​	每个容器内部都可以由root用户，跟宿主机不在同一个命名空间。



### 7.4、控制组

​	控制组（CGroups）是Linux内核的一个特性，主要用来对共享资源进行隔离、限制、审计等。只有能控制分配到容器的资源，Docker才能避免多个容器同时运行时的系统资源竞争。

​	控制组可以提供对容器的内存、CPU、磁盘IO等资源进行限制和计费管理。控制组的设计目标是为不同的应用情况提供统一的接口，从控制单一进程（比如nice工具）到系统级虚拟化（包括OpenVZ、Linux-VServer、LXC等）。

控制组提供以下功能：

- **资源限制（Resource Limiting）**：可以设置为不超过设定的内存限制。比如内存子系统可以为进程组设定一个内存使用上限，一旦进程组使用的内存达到限额再申请内存，就会触发Out of Memory。
- **优先级（Prioritization）**：通过优先级让一些组优先得到更多的CPU、MEM等资源
- **资源审计（Accounting）**：用来统计系统实际上把多少资源用到适合的目的上，可以使用cpuacct子系统记录某个进程组使用的CPU时间
- **隔离（Isolation）**：为组隔离名字空间，这样一个组不会看到另一个组的进程、网络连接、文件系统
- **控制（Control）**：挂起、恢复和重启动等操作
















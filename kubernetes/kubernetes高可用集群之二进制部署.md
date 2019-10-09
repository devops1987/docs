[TOC]

## 一、概述

​	本文档使用二进制手动部署kubernetes集群的所有步骤，不使用kubeadm、ansible等自动化工具来部署，旨在深入理解各个组件工作原理，进而能快速解决生产中问题。 由于使用了 `x509` 证书双向认证、`RBAC` 授权等安全机制，建议从头详细按照文档操作。

若是想自动化部署，参见ansible playbook一键部署：https://github.com/k8sre/k8s_init.git



## 二、架构

![kubernetes](../images/kubernetes.png)



## 三、环境信息

完全按照生产环境架构部署，若仅是测试最小3台机器即可部署。

### 3.1.基础环境

| 名称           | 版本       |
| -------------- | ---------- |
| OS             | CentOS 7.6 |
| Kernel         | 3.10       |
| kubernetes     | v1.14.5    |
| etcd           | v3.3.11    |
| docker-ce      | 18.09      |
| calico         | v3.6.2     |
| coredns        | 1.5.0      |
| dashboard      | 10.0.1     |
| metrics-server | v0.3.3     |
| harbro         | 1.8.1      |



### 3.2.集群网络

| 名称             | 地址段        |
| ---------------- | ------------- |
| Physical Network | 10.15.1.0/24  |
| Service Network  | 172.32.0.0/16 |
| Pod Network      | 172.48.0.0/12 |



### 3.3.集群节点

<table>
   <tr>
      <td>Role</td>
      <td>HostName</td>
      <td>IP</td>
      <td>CPU</td>
      <td>MEM</td>
      <td>Disk(数据盘)</td>
      <td>Common</td>
   </tr>
   <tr>
      <td rowspan="3">master</td>
      <td>master-01</td>
      <td>10.15.1.201</td>
      <td>4</td>
      <td>8</td>
      <td>200G SSD</td>
      <td rowspan="3">apiserver域名:apiserver.k8sre.com</td>
   </tr>
   <tr>
      <td>master-02</td>
      <td>10.15.1.202</td>
      <td>4</td>
      <td>8</td>
      <td>200G SSD</td>
   </tr>
   <tr>
      <td>master-03</td>
      <td>10.15.1.203</td>
      <td>4</td>
      <td>8</td>
      <td>200G SSD</td>
   </tr>
   <tr>
      <td rowspan="2">node</td>
      <td>node-01</td>
      <td>10.15.1.204</td>
      <td>16</td>
      <td>32</td>
      <td>500G SSD</td>
      <td>app=addons</td>
   </tr>
   <tr>
      <td>node-02</td>
      <td>10.15.1.205</td>
      <td>16</td>
      <td>32</td>
      <td>500G SSD</td>
      <td>app=addons</td>
   </tr>
   <tr>
      <td rowspan="2">haproxy</td>
      <td>haproxy-01</td>
      <td>10.15.1.198</td>
      <td>8</td>
      <td>16</td>
      <td>100G</td>
      <td>VIP：10.15.1.200</td>
   </tr>
   <tr>
      <td>haproxy-02</td>
      <td>10.15.1.199</td>
      <td>8</td>
      <td>16</td>
      <td>100G</td>
      <td>VIP：10.15.1.200</td>
   </tr>
</table>

⚠️：

- 所有数据保存在etcd中，master节点尽量使用ssd磁盘作为etcd数据目录
- haproxy作为apiserver 4层代理，可根据需要更改为其他方式



## 四、系统初始化

### 4.1.前提条件

- 所有机器可以访问互联网，并且内网互通
- 使用root用户进行操作

### 4.2.配置密钥登录

在master-01上生成密钥，并拷贝到其他节点

```
ssh-keygen -t rsa -b 4096 -C kubernetes
ssh-copy-id root@master-01
```

- 将etcd-01换成对应主机名

### 4.3.修改主机名

```
hostnamectl set-hostname master-01
```

- 将etcd-01换成对应主机名

### 4.4.修改软件源

```
curl -o /etc/yum.repos.d/CentOS-Base.repo https://mirrors.aliyun.com/repo/Centos-7.repo
curl -o /etc/yum.repos.d/epel.repo https://mirrors.aliyun.com/repo/epel-7.repo
yum clean all && yum makecache fast
```

### 4.5.关闭swap

删除/etc/fstab中swap配置，并执行一下命令：

```
swapoff -a
sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab
sed -i 's/.*swap.*/#&' /etc/fstab
```

### 4.6.关闭防火墙

```
systemctl stop iptables.service
systemctl stop firewalld.service
systemctl disable iptables.service
systemctl disable firewalld.service
```

### 4.7.关闭selinux

```
setenforce 0
sed -i 's@SELINUX=enforcing@SELINUX=disabled@' /etc/selinux/config
```

### 4.8.配置chrony时间服务

```
yum -y install chrony
```

```
cat > /etc/chrony.conf << EOF
server ntp.cloud.aliyuncs.com iburst
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
EOF
```

```
systemctl enable chronyd
systemctl restart chronyd
```

虚拟机可以再同步下系统及硬件时钟

```
clock --hctosys
```



### 4.9.安装依赖

```
yum -y install vim wget lrzsz telnet nmap-ncat make net-tools gcc gcc-c++ cmake bash-completion mtr python-devel sshpass conntrack ipvsadm ipset jq libnetfilter_conntrack-devel libnetfilter_conntrack conntrack-tools
```

### 4.10.加载内核模块

```
modprobe ip_vs
modprobe ip_vs_rr
modprobe ip_vs_wrr
modprobe ip_vs_sh
modprobe br_netfilter
modprobe nf_conntrack_ipv4
```

### 4.11.内核优化

```
cat > /etc/sysctl.conf << EOF
net.bridge.bridge-nf-call-iptables=1
net.bridge.bridge-nf-call-ip6tables=1
net.ipv4.ip_forward=1
fs.file-max=655360
net.ipv4.tcp_tw_recycle=0
vm.swappiness=0 # 禁止使用 swap 空间，只有当系统 OOM 时才允许使用它
vm.overcommit_memory=1 # 不检查物理内存是否够用
vm.panic_on_oom=0 # 开启 OOM
fs.inotify.max_user_instances=8192
fs.inotify.max_user_watches=1048576
fs.file-max=52706963
fs.nr_open=52706963
net.ipv6.conf.all.disable_ipv6=1
net.netfilter.nf_conntrack_max=2310720
net.ipv4.ip_local_port_range=20000 60999
EOF
```

### 4.12.配置journald

```
mkdir /var/log/journal # 持久化保存日志的目录
mkdir /etc/systemd/journald.conf.d
cat > /etc/systemd/journald.conf.d/99-prophet.conf <<EOF
[Journal]
# 持久化保存到磁盘
Storage=persistent
# 压缩历史日志
Compress=yes
SyncIntervalSec=5m
RateLimitInterval=30s
RateLimitBurst=1000
# 最大占用空间 10G
SystemMaxUse=10G
# 单日志文件最大 200M
SystemMaxFileSize=200M
# 日志保存时间 2 周
MaxRetentionSec=2week
# 不将日志转发到 syslog
ForwardToSyslog=no
EOF
systemctl restart systemd-journald
```

### 4.13.挂载数据盘

```
parted /dev/sdb mklabel gpt
parted /dev/sdb "mkpart primary xfs 0 -0"
mkfs.xfs  /dev/sdb1
mount /dev/sdb1 /data
echo "/dev/sdb1 /data    xfs     defaults        0 0" >> /etc/fstab 
```

### 4.14.创建证书目录

在k8s所有节点创建

```
mkdir -p /etc/kubernetes/ssl/
```

### 4.15.分发kubernetes二进制文件

```
wget https://dl.k8s.io/v1.14.5/kubernetes-server-linux-amd64.tar.gz
tar zxvf kubernetes-server-linux-amd64.tar.gz
cd kubernetes/server/bin
scp {kube-apiserver,kube-controller-manager,kube-scheduler,kubectl} ${MASTER}:/usr/bin/
scp {kubelet,kube-proxy} ${NODE}:/usr/bin/
ssh ${IP_ADDR} "chmod +x /usr/bin/kube*"
```

### 4.16.添加kubernetes运行用户

在master节点上执行

```
useradd -u 200 -d /var/kube -s /sbin/nologin kube
```



## 五、签发证书

### 5.1.签发证书
#### 5.1.1.签发ca证书

准备ca.cnf

```
cat > ca.cnf << EOF
[ req ]
req_extensions = v3_req
distinguished_name = req_distinguished_name
[req_distinguished_name]

[ v3_req ]
keyUsage = critical, cRLSign, keyCertSign, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer
basicConstraints = critical, CA:true, pathlen:2
EOF
```

生成ca.key

```
openssl genrsa -out ca.key 4096
```

签发ca

```
openssl req -x509 -new -nodes -key ca.key -days 1825 -out ca.pem -subj \
        "/CN=kubernetes/OU=System/C=CN/ST=Shanghai/L=Shanghai/O=k8s" \
        -config ca.cnf -extensions v3_req
```

- CN：Common Name，kube-apiserver从证书中提取该字段作为请求的用户名（User Name），浏览器使用该字段验证网站是否合法。
- O：Organization，kube-apiserver从证书中提取该字段作为请求用户所属的组（Group）。
- kube-apiserver将提取的User、Group作为RBAC授权的用户标识。

校验证书

```
openssl x509  -noout -text -in ca.pem
```

#### 5.1.2.签发etcd证书

准备etcd.cnf

```
cat > etcd.cnf << EOF
[ req ]
req_extensions = v3_req
distinguished_name = req_distinguished_name
[req_distinguished_name]
[ v3_req ]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names
[alt_names]
IP.1 = 127.0.0.1
IP.2 = 10.15.1.201
IP.3 = 10.15.1.202
IP.4 = 10.15.1.203
EOF
```

- IP对应etcd节点IP

生成key

```
openssl genrsa -out etcd.key 4096
```

生成证书请求

```
openssl req -new -key etcd.key -out etcd.csr \
        -subj "/CN=etcd/OU=System/C=CN/ST=Shanghai/L=Shanghai/O=k8s" \
        -config etcd.cnf
```

签发证书

```
openssl x509 -req -in etcd.csr \
        -CA ca.pem -CAkey ca.key -CAcreateserial \
        -out etcd.pem -days 1825 \
        -extfile etcd.cnf -extensions v3_req
```

校验证书

```
openssl x509  -noout -text -in etcd.pem
```



#### 5.1.3.签发kubectl证书

准备admin.cnf

```
cat > admin.cnf << EOF
[ req ]
req_extensions = v3_req
distinguished_name = req_distinguished_name
[req_distinguished_name]
[ v3_req ]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
EOF
```

- 该证书只会被 kubectl 当做 client 证书使用，所以alt_names字段为空

生成key

```
openssl genrsa -out admin.key 4096
```

生成证书请求

```
openssl req -new -key admin.key -out admin.csr \
        -subj "/CN=admin/OU=System/C=CN/ST=Shanghai/L=Shanghai/O=system:masters" \
        -config admin.cnf
```

- O 为 `system:masters` ，kube-apiserver 收到该证书后将请求的 Group 设置为
  system:masters`。
- 预定义的 ClusterRoleBinding cluster-admin 将 Group system:masters 与Role cluster-admin 绑定，该 Role 授予所有 API的权限

签发admin证书

```
openssl x509 -req -in admin.csr \
        -CA ca.pem -CAkey ca.key -CAcreateserial \
        -out admin.pem -days 1825 \
        -extfile admin.cnf -extensions v3_req
```

校验证书

```
openssl x509  -noout -text -in admin.pem
```



#### 5.1.4.签发apiserver证书

准备apiserver.cnf

```
cat > apiserver.cnf << EOF
[ req ]
req_extensions = v3_req
distinguished_name = req_distinguished_name
[req_distinguished_name]
[ v3_req ]
basicConstraints = critical, CA:FALSE
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
#subjectKeyIdentifier = hash
#authorityKeyIdentifier = keyid:always,issuer
subjectAltName = @alt_names
[alt_names]
DNS.1 = kubernetes
DNS.2 = kubernetes.default
DNS.3 = kubernetes.default.svc
DNS.4 = kubernetes.default.svc.cluster
DNS.5 = kubernetes.default.svc.cluster.local
DNS.6 = apiserver.k8sre.com
IP.1 = 127.0.0.1
IP.2 = 10.15.1.201
IP.3 = 10.15.1.202
IP.4 = 10.15.1.203
IP.5 = 172.32.0.1
IP.6 = 10.15.1.200
EOF
```

- alt_name下指定授权使用该证书的IP和域名列表，这里列出了master节点IP、HA VIP、apiserver域名、kubernetes服务IP和域名
- kubernetes服务IP是apiserver自动创建的，一般为`--service-cluster-ip-range`参数指定的网段的第一个IP
- IP.5：kubernetes服务IP
- IP.6：HA VIP，如是使用公有云负载均衡，应为负载均衡IP
- DNS.6：apiserver访问域名

生成key

```
openssl genrsa -out apiserver.key 4096
```

生成证书请求

```
openssl req -new -key apiserver.key -out apiserver.csr -subj \
        "/CN=kubernetes/OU=System/C=CN/ST=Shanghai/L=Shanghai/O=k8s" \
        -config apiserver.cnf
```

签发证书

```
openssl x509 -req -in apiserver.csr \
        -CA ca.pem -CAkey ca.key -CAcreateserial \
        -out apiserver.pem -days 1825 \
        -extfile apiserver.cnf -extensions v3_req
```

校验证书

```
openssl x509  -noout -text -in apiserver.pem
```

#### 5.1.5.签发metrics-server证书

准备proxy-client.cnf

```
cat > proxy-client.cnf << EOF
[ req ]
req_extensions = v3_req
distinguished_name = req_distinguished_name
[req_distinguished_name]
[ v3_req ]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
EOF
```

生成key

```
openssl genrsa -out proxy-client.key 4096
```

生成证书请求

```
openssl req -new -key proxy-client.key -out proxy-client.csr \
        -subj "/CN=aggregator/OU=System/C=CN/ST=Shanghai/L=Shanghai/O=k8s" \
        -config proxy-client.cnf
```

- CN名称需要配置在apiserver的`--requestheader-allowed-names`参数中，否则后续访问metrics时会提示权限不足

签发证书

```
openssl x509 -req -in proxy-client.csr \
        -CA ca.pem -CAkey ca.key -CAcreateserial \
        -out proxy-client.pem -days 1825 \
        -extfile proxy-client.cnf -extensions v3_req
```

校验证书

```
openssl x509  -noout -text -in proxy-client.pem
```

#### 5.1.6.签发kube-controller-manager证书

准备kube-controller-manager.cnf

```
cat > kube-controller-manager.cnf << EOF
[ req ]
req_extensions = v3_req
distinguished_name = req_distinguished_name
[req_distinguished_name]
[ v3_req ]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names
[alt_names]
IP.1 = 127.0.0.1
IP.2 = 10.15.1.201
IP.3 = 10.15.1.202
IP.4 = 10.15.1.203
EOF
```

- alt_name列表为kube-controller-manager节点IP

生成key

```
openssl genrsa -out kube-controller-manager.key 4096
```

生成证书请求

```
openssl req -new -key kube-controller-manager.key \
        -out kube-controller-manager.csr \
        -subj "/CN=system:kube-controller-manager/OU=System/C=CN/ST=Shanghai/L=Shanghai/O=system:kube-controller-manager" \
        -config kube-controller-manager.cnf
```

- CN和O均为`system:kube-controller-manager`，kubernetes 内置的
  ClusterRoleBindings `system:kube-controller-manager` 赋予 kube-controller-
  manager 工作所需的权限

签发证书

```
openssl x509 -req -in kube-controller-manager.csr \
        -CA ca.pem -CAkey ca.key -CAcreateserial \
        -out kube-controller-manager.pem -days 1825 \
        -extfile kube-controller-manager.cnf -extensions v3_req
```

校验证书

```
openssl x509  -noout -text -in kube-controller-manager.pem
```

#### 5.1.7.签发kube-scheduler证书

准备kube-scheduler.cnf

```
cat > kube-scheduler.cnf << EOF
[ req ]
req_extensions = v3_req
distinguished_name = req_distinguished_name
[req_distinguished_name]
[ v3_req ]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names
[alt_names]
IP.1 = 127.0.0.1
IP.2 = 10.15.1.201
IP.3 = 10.15.1.202
IP.4 = 10.15.1.203
EOF
```

- alt_name列表为kube-scheduler节点IP

生成key

```
openssl genrsa -out kube-scheduler.key 4096
```

生成证书请求

```
openssl req -new -key kube-scheduler.key \
        -out kube-scheduler.csr \
        -subj "/CN=system:kube-scheduler/OU=System/C=CN/ST=Shanghai/L=Shanghai/O=system:kube-scheduler" \
        -config kube-scheduler.cnf
```

- CN和O均为`system:kube-scheduler`，kubernetes 内置的
  ClusterRoleBindings `system:kube-scheduler` 赋予kube-scheduler工作所需的权限

签发证书

```
openssl x509 -req -in kube-scheduler.csr \
        -CA ca.pem -CAkey ca.key -CAcreateserial \
        -out kube-scheduler.pem -days 1825 \
        -extfile kube-scheduler.cnf -extensions v3_req
```

校验证书

```
openssl x509  -noout -text -in kube-scheduler.pem
```

#### 5.1.8.签发kube-proxy证书

准备kube-proxy.cnf

```
cat > kube-proxy.cnf << EOF
[ req ]
req_extensions = v3_req
distinguished_name = req_distinguished_name
[req_distinguished_name]
[ v3_req ]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
EOF
```

生成key

```
openssl genrsa -out kube-proxy.key 4096
```

生成证书请求

```
openssl req -new -key kube-proxy.key -out kube-proxy.csr \
        -subj "/CN=system:kube-proxy/OU=System/C=CN/ST=Shanghai/L=Shanghai/O=k8s" \
        -config kube-proxy.cnf
```

- CN：指定该证书的 User 为 system:kube-proxy 
- 预定义的 RoleBinding system:node-proxier 将User system:kube-proxy 与
  Role system:node-proxier 绑定，该 Role 授予了调用 kube-apiserver
  Proxy 相关 API 的权限
- 该证书只会被 kube-proxy 当做 client 证书使用，所以 alt_names字段为空

签发证书

```
openssl x509 -req -in kube-proxy.csr \
        -CA ca.pem -CAkey ca.key -CAcreateserial \
        -out kube-proxy.pem -days 1825 \
        -extfile kube-proxy.cnf -extensions v3_req
```

校验证书

```
openssl x509  -noout -text -in kube-proxy.pem
```



### 5.2.分发证书

分发master节点证书

```
scp {ca.pem,ca.key,etcd.pem,etcd.key,apiserver.pem,apiserver.key,proxy-client.pem,proxy-client.key} ${MASTER_IP}:/etc/kubernetes/ssl
```

分发node节点证书

```
scp {ca.pem,ca.key} ${NODE_IP}:/etc/kubernetes/ssl
```



## 六、部署etcd集群

​	etcd是CoreOS团队发起的开源项目，基于Go语言实现，作为一个分布式键值对（key-value）存储系统，通过分布式锁，leader选举和写屏障（write barriers）来实现可靠的分布式写作。主要用于服务发现、共享配置以及并发控制等。

特点：

- 简单：支持curl方式的用户API（HTTP+JSON）
- 安全：可选SSL客户端证书认证
- 快速：单实例可达每秒1000次写操作
- 可靠：使用Raft实现分布式

### 6.1.安装etcd

```
yum -y install etcd
```

### 6.2.修改主配置文件

/etc/etcd/etcd.conf

```
[member]
ETCD_NAME=etcd01
ETCD_DATA_DIR="/data/lib/etcd"
ETCD_LISTEN_PEER_URLS="https://10.15.1.201:2380"
ETCD_LISTEN_CLIENT_URLS="https://10.15.1.201:2379"
[cluster]
ETCD_INITIAL_ADVERTISE_PEER_URLS="https://10.15.1.201:2380"
ETCD_INITIAL_CLUSTER="etcd01=https://10.15.1.201:2380,etcd02=https://10.15.1.202:2380,etcd03=https://10.15.1.203:2380"
ETCD_INITIAL_CLUSTER_STATE="new"
ETCD_ADVERTISE_CLIENT_URLS="https://10.15.1.201:2379"
[security]
ETCD_CERT_FILE="/etc/kubernetes/ssl/etcd.pem"
ETCD_KEY_FILE="/etc/kubernetes/ssl/etcd.key"
ETCD_CLIENT_CERT_AUTH="true"
ETCD_TRUSTED_CA_FILE="/etc/kubernetes/ssl/ca.pem"
ETCD_AUTO_TLS="true"
ETCD_PEER_CERT_FILE="/etc/kubernetes/ssl/etcd.pem"
ETCD_PEER_KEY_FILE="/etc/kubernetes/ssl/etcd.key"
ETCD_PEER_CLIENT_CERT_AUTH="true"
ETCD_PEER_TRUSTED_CA_FILE="/etc/kubernetes/ssl/ca.pem"
ETCD_PEER_AUTO_TLS="true"
```

- 拷贝到对应机器时请将名称、IP修改为对应节点名称、IP

### 6.4.配置systemd unit

/usr/lib/systemd/system/etcd.service

```
[Unit]
Description=Etcd Server
After=network.target
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
WorkingDirectory=/var/lib/etcd/
EnvironmentFile=-/etc/etcd/etcd.conf
User=etcd

ExecStart=/bin/bash -c "GOMAXPROCS=$(nproc) /usr/bin/etcd \
    --name=\"${ETCD_NAME}\" \
    --cert-file=\"${ETCD_CERT_FILE}\" \
    --key-file=\"${ETCD_KEY_FILE}\" \
    --peer-cert-file=\"${ETCD_PEER_CERT_FILE}\" \
    --peer-key-file=\"${ETCD_PEER_KEY_FILE}\" \
    --trusted-ca-file=\"${ETCD_TRUSTED_CA_FILE}\" \
    --peer-trusted-ca-file=\"${ETCD_PEER_TRUSTED_CA_FILE}\" \
    --initial-advertise-peer-urls=\"${ETCD_INITIAL_ADVERTISE_PEER_URLS}\" \
    --listen-peer-urls=\"${ETCD_LISTEN_PEER_URLS}\" \
    --listen-client-urls=\"${ETCD_LISTEN_CLIENT_URLS}\" \
    --advertise-client-urls=\"${ETCD_ADVERTISE_CLIENT_URLS}\" \
    --initial-cluster-token=\"${ETCD_INITIAL_CLUSTER_TOKEN}\" \
    --initial-cluster=\"${ETCD_INITIAL_CLUSTER}\" \
    --initial-cluster-state=\"${ETCD_INITIAL_CLUSTER_STATE}\" \
    --data-dir=\"${ETCD_DATA_DIR}\""

Restart=on-failure
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

### 6.5.配置etcd数据目录

```
mkdir -p /data/lib/etcd
chown -R etcd. /data/lib/etcd
```

### 6.6.启动服务

```
systemctl daemon-reload 
systemctl restart etcd
systemctl enable etcd
```

### 6.7.集群验证

配置启用v3版本API

/etc/profile

```
export ETCDCTL_API=3
```

```
ETCDCTL_API=3 etcdctl \
  --endpoints=https://10.15.1.131:2379,https://10.15.1.132:2379,https://10.15.1.133:2379 \
  --cacert=/etc/kubernetes/ssl/ca.pem \
  --cert=/etc/kubernetes/ssl/etcd.pem \
  --key=/etc/kubernetes/ssl/etcd.key \
  endpoint health 
```

```
ETCDCTL_API=3 etcdctl --write-out=table \
  --endpoints=https://10.15.1.131:2379,https://10.15.1.132:2379,https://10.15.1.133:2379 \
  --cacert=/etc/kubernetes/ssl/ca.pem \
  --cert=/etc/kubernetes/ssl/etcd.pem \
  --key=/etc/kubernetes/ssl/etcd.key \
  endpoint status
```

```
ETCDCTL_API=3 etcdctl --write-out=table \
  --endpoints=https://10.15.1.131:2379,https://10.15.1.132:2379,https://10.15.1.133:2379 \
  --cacert=/etc/kubernetes/ssl/ca.pem \
  --cert=/etc/kubernetes/ssl/etcd.pem \
  --key=/etc/kubernetes/ssl/etcd.key \
  member list
```



### 6.8.集群扩容

修改主配置文件

```
ETCD_INITIAL_CLUSTER_STATE="existing"
```

将节点加入集群

```
ETCDCTL_API=3 etcdctl --write-out=table \
  --endpoints=https://10.15.1.131:2379,https://10.15.1.132:2379,https://10.15.1.133:2379 \
  --cacert=/etc/kubernetes/ssl/ca.pem \
  --cert=/etc/kubernetes/ssl/etcd.pem \
  --key=/etc/kubernetes/ssl/etcd.key \
  member add etcd04 https://10.15.1.220:2380
```



## 七、apiserver高可用配置

### 7.1.安装haproxy

```
yum -y install haproxy
```

### 7.2.配置haproxy

/etc/haproxy/haproxy.cfg

```
global
   log /dev/log local0
   log /dev/log local1 notice
   chroot      /var/lib/haproxy
   pidfile     /var/run/haproxy.pid
   maxconn     4000
   stats timeout 30s
   user        haproxy
   group       haproxy
   daemon
   stats socket /var/lib/haproxy/stats

defaults
    mode                    tcp
    log                     global
    option                  httplog
    option                  dontlognull
    option                  http-server-close
    option                  redispatch
    retries                 3
    timeout connect         5s
    timeout client          30s
    timeout server          30s
    timeout check           2s
    maxconn                 50000

frontend http_stats
   bind *:58080
   mode http
   stats uri /haproxy?stats

frontend haproxy_kube
    bind *:6443
    mode tcp
    option tcplog
    default_backend masters

backend masters
    mode tcp
    option tcplog
    balance roundrobin
    server  master-01  10.15.1.201:6443 check port 6443  inter 1500 rise 1 fall 3
    server  master-02  10.15.1.202:6443 check port 6443  inter 1500 rise 1 fall 3
    server  master-03  10.15.1.203:6443 check port 6443  inter 1500 rise 1 fall 3
```

### 7.3.启动haproxy

```
systemctl restart haproxy
systemctl enable haproxy
```

### 7.4.安装keepalived

```
yum -y install keepalived
```

### 7.5.配置keepalived

/etc/keepalived/keepalived.conf

master:

```
global_defs {
   router_id k8s
}

vrrp_script Checkhaproxy {
    script "/etc/keepalived/check_haproxy.sh"
    interval 3
    timeout 9
    fall 2
    rise 2
}

vrrp_instance VI_1 {
    state MASTER
    interface ens192
    virtual_router_id  100
    priority 100
    advert_int 1
    nopreempt
    mcast_src_ip 10.15.1.198
    authentication {
        auth_type PASS
        auth_pass kuburnetes
    }
    unicast_peer {
      10.15.1.198
      10.15.1.199
    }
    virtual_ipaddress {
        10.15.1.200
    }
    track_script {
        Checkhaproxy
    }

}
```

backup

```
global_defs {
   router_id k8s
}

vrrp_script Checkhaproxy {
    script "/etc/keepalived/check_haproxy.sh"
    interval 3
    timeout 9
    fall 2
    rise 2
}

vrrp_instance VI_1 {
    state BACKUP
    interface ens192
    virtual_router_id  100
    priority 90
    advert_int 1
    nopreempt
    mcast_src_ip 10.15.1.199
    authentication {
        auth_type PASS
        auth_pass kuburnetes
    }
    unicast_peer {
      10.15.1.198
      10.15.1.199
    }
    virtual_ipaddress {
        10.15.1.200
    }
    track_script {
        Checkhaproxy
    }

}
```
/etc/keepalived/check_haproxy.sh
```
#!/bin/bash
if [ `ps -C haproxy --no-header |wc -l` -eq 0 ] ; then
    systemctl restart haproxy
    sleep 3
    if [ `ps -C haproxy --no-header |wc -l` -eq 0 ] ; then
        systemctl stop keepalived
    fi
fi
```

```
chmod +x /etc/keepalived/check_haproxy.sh
```

### 7.6.启动服务

```
systemctl restart keepalived
systemctl enable keepalived
```



## 八、部署Master节点

master节点运行以下组件：

- kube-apiserver
- kube-controller-manager
- kube-scheduler

1、这三个组件均为无状态，数据存储在etcd中。kube-controller-manager和kube-scheduler会自动选举出一个leader实例，其他实例处于阻塞模式，当leader挂了之后，重新选举出一个新的leader，从而保证服务的可用性。

2、kube-apiserver需要进行代理访问。

### 8.1.配置kubectl

#### 8.1.1.生成kubectl kubeconfig

```
export KUBE_APISERVER="https://apiserver.k8sre.com:6443"
# 设置集群参数
kubectl config set-cluster kubernetes \
  --certificate-authority=ca.pem \
  --embed-certs=true \
  --server=${KUBE_APISERVER}
# 设置客户端认证参数
kubectl config set-credentials admin \
  --client-certificate=admin.pem \
  --embed-certs=true \
  --client-key=admin.key
# 设置上下文参数
kubectl config set-context kubernetes \
  --cluster=kubernetes \
  --user=admin
# 设置默认上下文
kubectl config use-context kubernetes
```

- admin.pem`证书O字段值为`system:masters`，`kube-apiserver` 预定义的 RoleBinding `cluster-admin` 将 Group `system:masters` 与 Role `cluster-admin` 绑定，该 Role 授予了调用`kube-apiserver` 相关 API 的权限。
- --certificate-authority ：验证 kube-apiserver 证书的根证书
- --client-certificate 、 --client-key ：刚生成的 admin 证书和私钥，连
  接 kube-apiserver 时使用
- --embed-certs=true ：将 ca.pem 和 admin.pem 证书内容嵌入到生成的
  kubectl.kubeconfig 文件中(不加时，写入的是证书文件路径，后续拷贝 kubeconfig
  到其它机器时，还需要单独拷贝证书文件，不方便。)
- 生成的 kubeconfig 被保存到 `~/.kube/config` 文件

#### 8.1.2.配置kubectl命令自动补全

/etc/profile

```
source <(kubectl completion bash)
```



### 8.2.安装apiserver

#### 8.2.1.配置apiserver

/etc/kubernetes/apiserver

```
KUBE_API_ARGS="\
    --allow-privileged=true \
    --bind-address=10.15.1.201 \
    --etcd-servers=https://10.15.1.201:2379,https://10.15.1.202:2379,https://10.15.1.203:2379 \
    --secure-port=6443 \
    --insecure-port=0 \
    --service-account-key-file=/etc/kubernetes/ssl/ca.key \
    --tls-cert-file=/etc/kubernetes/ssl/apiserver.pem \
    --tls-private-key-file=/etc/kubernetes/ssl/apiserver.key \
    --client-ca-file=/etc/kubernetes/ssl/ca.pem \
    --etcd-cafile=/etc/kubernetes/ssl/ca.pem \
    --etcd-certfile=/etc/kubernetes/ssl/etcd.pem \
    --etcd-keyfile=/etc/kubernetes/ssl/etcd.key \
    --kubelet-certificate-authority=/etc/kubernetes/ssl/ca.pem \
    --kubelet-client-certificate=/etc/kubernetes/ssl/apiserver.pem \
    --kubelet-client-key=/etc/kubernetes/ssl/apiserver.key \
    --enable-admission-plugins=NamespaceLifecycle,LimitRanger,ServiceAccount,DefaultStorageClass,ResourceQuota,NodeRestriction \
    --authorization-mode=RBAC,Node \
    --kubelet-https=true \
    --anonymous-auth=false \
    --apiserver-count=3 \
    --default-not-ready-toleration-seconds=10 \
    --default-unreachable-toleration-seconds=10 \
    --delete-collection-workers=3 \
    --audit-log-maxage=7 \
    --audit-log-maxbackup=10 \
    --audit-log-maxsize=100 \
    --event-ttl=1h \
    --service-cluster-ip-range=172.32.0.0/16 \
    --service-node-port-range=30000-50000 \
    --requestheader-client-ca-file=/etc/kubernetes/ssl/ca.pem \
    --proxy-client-cert-file=/etc/kubernetes/ssl/proxy-client.pem \
    --proxy-client-key-file=/etc/kubernetes/ssl/proxy-client.key \
    --requestheader-allowed-names=aggregator \
    --requestheader-extra-headers-prefix=X-Remote-Extra- \
    --requestheader-group-headers=X-Remote-Group \
    --requestheader-username-headers=X-Remote-User \
    --enable-aggregator-routing=true \
    --max-requests-inflight=3000 \
    --enable-bootstrap-token-auth \
    --logtostderr=true \
    --allow-privileged=true \
    --v=4"
```

- `--advertise-address`：apiserver 对外通告的 IP（kubernetes 服务后端节点 IP）；
- `--default-*-toleration-seconds`：设置节点异常相关的阈值；
- `--max-*-requests-inflight`：请求相关的最大阈值；
- `--etcd-*`：访问 etcd 的证书和 etcd 服务器地址；
- `--experimental-encryption-provider-config`：指定用于加密 etcd 中 secret 的配置；
- `--bind-address`： https 监听的 IP，不能为 `127.0.0.1`，否则外界不能访问它的安全端口 6443；
- `--secret-port`：https 监听端口；
- `--insecure-port=0`：关闭监听 http 非安全端口(8080)；
- `--tls-*-file`：指定 apiserver 使用的证书、私钥和 CA 文件；
- `--audit-*`：配置审计策略和审计日志文件相关的参数；
- `--client-ca-file`：验证 client (kue-controller-manager、kube-scheduler、kubelet、kube-proxy 等)请求所带的证书；
- `--enable-bootstrap-token-auth`：启用 kubelet bootstrap 的 token 认证；
- `--requestheader-*`：kube-apiserver 的 aggregator layer 相关的配置参数，proxy-client & HPA 需要使用；
- `--requestheader-client-ca-file`：用于签名 `--proxy-client-cert-file` 和 `--proxy-client-key-file` 指定的证书；在启用了 metric aggregator 时使用；
- `--requestheader-allowed-names`：不能为空，值为逗号分割的 `--proxy-client-cert-file` 证书的 CN 名称，这里设置为 "aggregator"；
- `--service-account-key-file`：签名 ServiceAccount Token 的公钥文件，kube-controller-manager 的 `--service-account-private-key-file` 指定私钥文件，两者配对使用；
- `--runtime-config=api/all=true`： 启用所有版本的 APIs，如 autoscaling/v2alpha1；
- `--authorization-mode=Node,RBAC`、`--anonymous-auth=false`： 开启 Node 和 RBAC 授权模式，拒绝未授权的请求；
- `--enable-admission-plugins`：启用一些默认关闭的 plugins；
- `--allow-privileged`：运行执行 privileged 权限的容器；
- `--apiserver-count=3`：指定 apiserver 实例的数量；
- `--event-ttl`：指定 events 的保存时间；
- `--kubelet-*`：如果指定，则使用 https 访问 kubelet APIs；需要为证书对应的用户(上面 kubernetes*.pem 证书的用户为 kubernetes) 用户定义 RBAC 规则，否则访问 kubelet API 时提示未授权；
- `--proxy-client-*`：apiserver 访问 metrics-server 使用的证书；
- `--service-cluster-ip-range`： 指定 Service Cluster IP 地址段；
- `--service-node-port-range`： 指定 NodePort 的端口范围；

如果 kube-apiserver 机器**没有**运行 kube-proxy，则还需要添加 `--enable-aggregator-routing=true` 参数；

关于 `--requestheader-XXX` 相关参数，参考：

- https://github.com/kubernetes-incubator/apiserver-builder/blob/master/docs/concepts/auth.md
- https://docs.bitnami.com/kubernetes/how-to/configure-autoscaling-custom-metrics/

注意：

1. requestheader-client-ca-file 指定的 CA 证书，必须具有 client auth and server auth；

2. 如果 `--requestheader-allowed-names` 为空，或者 `--proxy-client-cert-file` 证书的 CN 名称不在 allowed-names 中，则后续查看 node 或 pods 的 metrics 失败，提示：

   ```
   kubectl top nodes
   Error from server (Forbidden): nodes.metrics.k8s.io is forbidden: User "aggregator" cannot list resource "nodes" in API group "metrics.k8s.io" at the cluster scope
   ```

#### 8.2.2.配置systemd unit

/usr/lib/systemd/system/kube-apiserver.service

```
[Unit]
Description=Kubernetes API Server
Documentation=https://github.com/kubernetes/kubernetes
After=network.target
After=etcd.service

[Service]
EnvironmentFile=-/etc/kubernetes/apiserver
User=kube
ExecStart=/usr/bin/kube-apiserver $KUBE_API_ARGS
Restart=on-failure
Type=notify
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

#### 8.2.3.启动kube-apiserver

```
systemctl daemon-reload
systemctl enable kube-apiserver
systemctl restart kube-apiserver
```

#### 8.2.4.查看端口

```
netstat -lntp| grep kube-apiserver
```

- 6443：apiserver端口，接收 https 请求的安全端口，对所有请求做认证和授权；由于关闭了非安全端口，故没有监听 8080。
- 以上端口都提供/metrics和/healthz接口。

#### 8.2.5.授予kube-apiserver访问kubelet API权限

在执行 kubectl exec、run、logs 等命令时，apiserver 会将请求转发到 kubelet 的 https 端口。这里定义 RBAC 规则，授权 apiserver 使用的证书（apiserver.pem）用户名（CN：kuberntes）访问 kubelet API 的权限

```
kubectl create clusterrolebinding kube-apiserver:kubelet-apis --clusterrole=system:kubelet-api-admin --user kubernetes
```

- --user指定的为apiserver.pem证书中CN指定的值

### 8.3.安装kube-controller-

#### 8.3.1.生成kube-controller-manager kubeconfig

使用以下命令生成kubeconfig文件并拷贝至其他master节点

```
export KUBE_APISERVER="https://apiserver.k8sre.com:6443"

# 设置集群参数
kubectl config set-cluster kubernetes \
  --certificate-authority=ca.pem \
  --embed-certs=true \
  --server=${KUBE_APISERVER} \
  --kubeconfig=kube-controller-manager.kubeconfig

# 设置客户端认证参数
kubectl config set-credentials system:kube-controller-manager \
  --client-certificate=kube-controller-manager.pem \
  --client-key=kube-controller-manager.key \
  --embed-certs=true \
  --kubeconfig=kube-controller-manager.kubeconfig

# 设置上下文参数
kubectl config set-context system:kube-controller-manager \
  --cluster=kubernetes \
  --user=system:kube-controller-manager \
  --kubeconfig=kube-controller-manager.kubeconfig

# 设置默认上下文
kubectl config use-context system:kube-controller-manager --kubeconfig=kube-controller-manager.kubeconfig
```

#### 8.3.2.配置kube-controller-manager

/etc/kubernetes/controller-manager

```
KUBE_CONTROLLER_MANAGER_ARGS="\
    --service-account-private-key-file=/etc/kubernetes/ssl/ca.key \
    --root-ca-file=/etc/kubernetes/ssl/ca.pem \
    --requestheader-client-ca-file=/etc/kubernetes/ssl/ca.pem \
    --allocate-node-cidrs=true \
    --cluster-name=kubernetes \
    --cluster-signing-cert-file=/etc/kubernetes/ssl/ca.pem \
    --cluster-signing-key-file=/etc/kubernetes/ssl/ca.key \
    --leader-elect=true \
    --cluster-cidr=172.48.0.0/12 \
    --service-cluster-ip-range=172.32.0.0/16 \
    --secure-port=10257 \
    --node-monitor-period=2s \
    --node-monitor-grace-period=16s \
    --pod-eviction-timeout=30s \
    --use-service-account-credentials=true \
    --controllers=*,bootstrapsigner,tokencleaner \
    --horizontal-pod-autoscaler-sync-period=10s \
    --kubeconfig=/etc/kubernetes/kube-controller-manager.kubeconfig \
    --authentication-kubeconfig=/etc/kubernetes/kube-controller-manager.kubeconfig \
    --authorization-kubeconfig=/etc/kubernetes/kube-controller-manager.kubeconfig \
    --feature-gates=RotateKubeletServerCertificate=true \
    --logtostderr=true \
    --v=4"
```

- `--secure-port=10257`、`--bind-address=0.0.0.0`: 在所有网络接口监听 10257端口的 https /metrics 请求；
- `--kubeconfig`：指定 kubeconfig 文件路径，kube-controller-manager 使用它连接和验证 kube-apiserver；
- `--authentication-kubeconfig` 和 `--authorization-kubeconfig`：kube-controller-manager 使用它连接 apiserver，对 client 的请求进行认证和授权。`kube-controller-manager` 不再使用 `--tls-ca-file` 对请求 https metrics 的 Client 证书进行校验。如果没有配置这两个 kubeconfig 参数，则 client 连接 kube-controller-manager https 端口的请求会被拒绝(提示权限不足)。
- `--cluster-signing-*-file`：签名 TLS Bootstrap 创建的证书；
- `--experimental-cluster-signing-duration`：指定 TLS Bootstrap 证书的有效期；
- `--root-ca-file`：放置到容器 ServiceAccount 中的 CA 证书，用来对 kube-apiserver 的证书进行校验；
- `--service-account-private-key-file`：签名 ServiceAccount 中 Token 的私钥文件，必须和 kube-apiserver 的 `--service-account-key-file` 指定的公钥文件配对使用；
- `--service-cluster-ip-range` ：指定 Service Cluster IP 网段，必须和 kube-apiserver 中的同名参数一致；
- `--leader-elect=true`：集群运行模式，启用选举功能；被选为 leader 的节点负责处理工作，其它节点为阻塞状态；
- `--controllers=*,bootstrapsigner,tokencleaner`：启用的控制器列表，tokencleaner 用于自动清理过期的 Bootstrap token；
- `--horizontal-pod-autoscaler-*`：custom metrics 相关参数，支持 autoscaling/v2alpha1；
- `--tls-cert-file`、`--tls-private-key-file`：使用 https 输出 metrics 时使用的 Server 证书和秘钥；
- `--use-service-account-credentials=true`: kube-controller-manager 中各 controller 使用 serviceaccount 访问 kube-apiserver；

#### 8.3.3.配置systemd unit

/usr/lib/systemd/system/kube-controller-manager.service

```
[Unit]
Description=Kubernetes Controller Manager
Documentation=https://github.com/kubernetes/kubernetes
After=kube-apiserver.service
Requires=kube-apiserver.service

[Service]
EnvironmentFile=-/etc/kubernetes/controller-manager
User=kube
ExecStart=/usr/bin/kube-controller-manager $KUBE_CONTROLLER_MANAGER_ARGS
Restart=on-failure
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

#### 8.3.4.配置ACL

```
setfacl -m u:kube:r /etc/kubernetes/*.kubeconfig
```

#### 8.3.5.启动kube-controller-manager

```
systemctl daemon-reload
systemctl enable kube-controller-manager
systemctl restart kube-controller-manager
```

#### 8.3.6.查看端口

```
netstat -lntp| grep kube-controller-manager
```

- 10252：controller-manager端口，接受http请求，非安全端口，不需要认证。
- 10257：controller-manager端口，接受https请求，安全端口，需要认证。
- 以上端口都提供/metrics和/healthz接口。



### 8.4.安装kube-scheduler

#### 8.4.1.生成kube-scheduler kubeconfig

使用以下命令生成kubeconfig文件并拷贝至其他master节点

```
export KUBE_APISERVER="https://apiserver.k8sre.com:6443"

# 设置集群参数
kubectl config set-cluster kubernetes \
  --certificate-authority=ca.pem \
  --embed-certs=true \
  --server=${KUBE_APISERVER} \
  --kubeconfig=kube-scheduler.kubeconfig

# 设置客户端认证参数
kubectl config set-credentials system:kube-scheduler \
  --client-certificate=kube-scheduler.pem \
  --client-key=kube-scheduler.key \
  --embed-certs=true \
  --kubeconfig=kube-scheduler.kubeconfig

# 设置上下文参数
kubectl config set-context system:kube-scheduler \
  --cluster=kubernetes \
  --user=system:kube-scheduler \
  --kubeconfig=kube-scheduler.kubeconfig

# 设置默认上下文
kubectl config use-context system:kube-scheduler --kubeconfig=kube-scheduler.kubeconfig
```

#### 8.4.2.配置kube-scheduler

/etc/kubernetes/scheduler

```
KUBE_SCHEDULER_ARGS="\
    --kubeconfig=/etc/kubernetes/kube-scheduler.kubeconfig \
    --authorization-kubeconfig=/etc/kubernetes/kube-scheduler.kubeconfig \
    --authentication-kubeconfig=/etc/kubernetes/kube-scheduler.kubeconfig \
    --leader-elect=true \
    --logtostderr=true \
    --v=4"
```

- --kubeconfig ：指定 kubeconfig 文件路径，kube-scheduler 使用它连接和验证
  kube-apiserver。
- --leader-elect=true ：集群运行模式，启用选举功能；被选为 leader 的节点负
  责处理工作，其它节点为阻塞状态

#### 8.4.3.配置systemd unit

/usr/lib/systemd/system/kube-scheduler.service

```
[Unit]
Description=Kubernetes Scheduler Plugin
Documentation=https://github.com/kubernetes/kubernetes
After=kube-apiserver.service
Requires=kube-apiserver.service

[Service]
EnvironmentFile=-/etc/kubernetes/scheduler
User=kube
ExecStart=/usr/bin/kube-scheduler $KUBE_SCHEDULER_ARGS
Restart=on-failure
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

#### 8.4.4.配置ACL权限

```
setfacl -m u:kube:r /etc/kubernetes/*.kubeconfig
```

#### 8.4.5.启动kube-scheduler

```
systemctl daemon-reload
systemctl enable kube-scheduler
systemctl restart kube-scheduler
```

#### 8.4.6.查看端口

```
netstat -lntp| grep kube-scheduler
```

- 10251：scheduler端口，接受http请求，非安全端口，不需要认证。
- 10259：scheduler端口，接受https请求，安全端口，需要认证。
- 以上端口都提供/metrics和/healthz接口。

### 8.5.检查集群

```
kubectl get componentstatuses
```

查看当前leader

```
kubectl get endpoints kube-controller-manager -n kube-system -o yaml 
kubectl get endpoints kube-scheduler -n kube-system -o yaml
```



## 九、部署Node节点

### 9.1.安装docker

#### 9.1.1.添加docker软件源

/etc/yum.repos.d/docker-ce.repo

```
[docker-ce-stable]
baseurl = http://mirrors.cloud.aliyuncs.com/docker-ce/linux/centos/7/$basearch/stable
	https://mirrors.aliyun.com/docker-ce/linux/centos/7/$basearch/stable
enabled = 1
gpgcheck = 1
gpgkey = https://mirrors.aliyun.com/docker-ce/linux/centos/gpg
name = Docker CE Stable - $basearch

[docker-ce-stable-debuginfo]
baseurl = http://mirrors.cloud.aliyuncs.com/docker-ce/linux/centos/7/debug-$basearch/stable
	https://mirrors.aliyun.com/docker-ce/linux/centos/7/debug-$basearch/stable
enabled = 1
gpgcheck = 1
gpgkey = https://mirrors.aliyun.com/docker-ce/linux/centos/gpg
name = Docker CE Stable - Debuginfo $basearch

[docker-ce-stable-source]
baseurl = http://mirrors.cloud.aliyuncs.com/docker-ce/linux/centos/7/source/stable 
	 https://mirrors.aliyun.com/docker-ce/linux/centos/7/source/stable
enabled = 1
gpgcheck = 1
gpgkey = https://mirrors.aliyun.com/docker-ce/linux/centos/gpg
name = Docker CE Stable - Sources
```

#### 9.1.2.安装docker

```
yum -y install docker-ce-18.09.8
systemctl start docker
```

#### 9.1.3.修改docker配置文件

```
cat > /etc/docker/daemon.json << EOF
{
 "registry-mirrors": ["https://registry.docker-cn.com"],
 "exec-opts": ["native.cgroupdriver=systemd"],
 "storage-driver": "overlay2",
 "storage-opts":["overlay2.override_kernel_check=true"],
 "log-driver": "json-file",
 "log-opts": {
     "max-size": "500m",
     "max-file": "3"
 },
 "oom-score-adjust": -1000,
 "data-root": "/data/lib/docker"
}
EOF
```

#### 9.1.4.启动docker服务

```
systemctl enable docker
systemctl restart docker
docker info
```



### 9.2. 安装kubelet

#### 9.2.1.生成kubelet bootstrap kubeconfig

使用 Token 时整个启动引导过程:

- 在集群内创建特定的  `Bootstrap Token Secret` ，该 Secret 将替代以前的  `token.csv` 内置用户声明文件 
- 在集群内创建首次 TLS Bootstrap 申请证书的 ClusterRole、后续 renew Kubelet client/server 的 ClusterRole，以及其相关对应的 ClusterRoleBinding；并绑定到对应的组或用户
- 调整 Controller Manager 配置，以使其能自动签署相关证书和自动清理过期的 TLS Bootstrapping Token
- 生成特定的包含 TLS Bootstrapping Token 的  `bootstrap.kubeconfig` 以供 kubelet 启动时使用 
- 调整 Kubelet 配置，使其首次启动加载  `bootstrap.kubeconfig` 并使用其中的 TLS Bootstrapping Token 完成首次证书申请 
- 证书被 Controller Manager 签署，成功下发，Kubelet 自动重载完成引导流程
- 后续 Kubelet 自动 renew 相关证书
- 可选的: 集群搭建成功后立即清除  `Bootstrap Token Secret` ，或等待 Controller Manager 待其过期后删除，以防止被恶意利用

首先建立一个随机产生`BOOTSTRAP_TOKEN`，并建立`bootstrap`的kubeconfig文件

```
TOKEN_PUB=$(openssl rand -hex 3)
TOKEN_SECRET=$(openssl rand -hex 8)
BOOTSTRAP_TOKEN="${TOKEN_PUB}.${TOKEN_SECRET}"

kubectl -n kube-system create secret generic bootstrap-token-${TOKEN_PUB} \
        --type 'bootstrap.kubernetes.io/token' \
        --from-literal description="cluster bootstrap token" \
        --from-literal token-id=${TOKEN_PUB} \
        --from-literal token-secret=${TOKEN_SECRET} \
        --from-literal usage-bootstrap-authentication=true \
        --from-literal usage-bootstrap-signing=true
```

- Token 必须满足  `[a-z0-9]{6}\.[a-z0-9]{16}` 格式；以  `.` 分割，前面的部分被称作  `Token ID` ，  `Token ID` 并不是 “机密信息”，它可以暴露出去；相对的后面的部分称为  `Token Secret` ，它应该是保密的。

使用以下命令生成bootstrap kubeconfig文件并拷贝至其他node节点

```
export KUBE_APISERVER="https://apiserver.k8sre.com:6443"

# 设置集群参数
kubectl config set-cluster kubernetes \
  --certificate-authority=ca.pem \
  --embed-certs=true \
  --server=${KUBE_APISERVER} \
  --kubeconfig=bootstrap.kubeconfig

# 设置客户端认证参数(${BOOTSTRAP_TOKEN}的值为前面token.csv的值)
kubectl config set-credentials kubelet-bootstrap \
  --token=${BOOTSTRAP_TOKEN} \
  --kubeconfig=bootstrap.kubeconfig

# 设置上下文参数
kubectl config set-context default \
  --cluster=kubernetes \
  --user=kubelet-bootstrap \
  --kubeconfig=bootstrap.kubeconfig

# 设置默认上下文
kubectl config use-context default --kubeconfig=bootstrap.kubeconfig
```

- 向 kubeconfig 写入的是 token，bootstrap 结束后 kube-controller-manager 为 kubelet 创建 client 和 server 证书。

#### 9.2.2.配置kubelet

从v1.10版本开始，部分kubelet参数需要在配置文件中配置，建议尽快替换

```
cat > /etc/kubernetes/kubelet.yaml << EOF
kind: KubeletConfiguration
apiVersion: kubelet.config.k8s.io/v1beta1
cgroupDriver: systemd
authentication:
  anonymous:
    enabled: false
  webhook:
    enabled: true
  x509:
    clientCAFile: "/etc/kubernetes/ssl/ca.pem"
authorization:
  mode: Webhook
readOnlyPort: 0
serverTLSBootstrap: true
rotateCertificates: true
enableDebuggingHandlers: true
enableContentionProfiling: true
clusterDomain: "cluster.local"
clusterDNS:
  - "172.32.0.2"
cgroupsPerQOS: true
hairpinMode: promiscuous-bridge
serializeImagePulls: false
enableControllerAttachDetach: true
EOF
```

/etc/kubernetes/kubelet

```
KUBELET_ARGS="\
    --hostname-override=10.15.1.204 \
    --config=/etc/kubernetes/kubelet.yaml \
    --cgroup-driver=systemd \
    --authentication-token-webhook=true \
    --authorization-mode=Webhook \
    --anonymous-auth=false \
    --pod-infra-container-image=k8sre/pause-amd64:3.1 \
    --cluster-dns=172.32.0.2 \
    --bootstrap-kubeconfig=/etc/kubernetes/bootstrap.kubeconfig \
    --kubeconfig=/etc/kubernetes/kubelet.kubeconfig  \
    --feature-gates=RotateKubeletClientCertificate=true,RotateKubeletServerCertificate=true \
    --client-ca-file=/etc/kubernetes/ssl/ca.pem \
    --cert-dir=/etc/kubernetes/ssl \
    --cluster-domain=cluster.local \
    --hairpin-mode promiscuous-bridge \
    --root-dir=/data/lib/kubelet \
    --network-plugin=cni \
    --serialize-image-pulls=false \
    --rotate-certificates \
    --logtostderr=true \
    --v=4"
```

- kubelet 启动后使用 --bootstrap-kubeconfig 向 kube-apiserver 发送 CSR 请求，当这个CSR 被 approve 后，kube-controller-manager 为 kubelet 创建 TLS 客户端证书、私钥和 --kubeletconfig 文件。

⚠️：kube-controller-manager 需要配置 --cluster-signing-cert-file 和 --cluster-signing-key-file 参数，才会为 TLS Bootstrap 创建证书和私钥。

#### 9.2.3.配置systemd unit

/usr/lib/systemd/system/kubelet.service

```
[Unit]
Description=Kubernetes Kubelet Server
Documentation=https://github.com/kubernetes/kubernetes
After=docker.service
Requires=docker.service

[Service]
WorkingDirectory=/data/lib/kubelet
EnvironmentFile=-/etc/kubernetes/kubelet
ExecStart=/usr/bin/kubelet $KUBELET_ARGS
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

#### 9.2.4.配置kubelet数据目录

```
mkdir -p /data/lib/kubelet
```

#### 9.2.5.Bootstrap Token Auth 和授予权限

​	kubelet 启动时查找 --kubeletconfig 参数对应的文件是否存在，如果不存在则使用
--bootstrap-kubeconfig 指定的 kubeconfig 文件向 kube-apiserver 发送证书签名
请求 (CSR)。

​	kube-apiserver 收到 CSR 请求后，对其中的 Token 进行认证，认证通过后将请求的 user 设置为 `system:bootstrap:<Token ID>`，group 设置为 `system:bootstrappers`，这一过程称为 Bootstrap Token Auth。

​	默认情况下，这个 user 和 group 没有创建 CSR 的权限，kubelet 启动失败。

​	解决办法是：创建一个 clusterrolebinding，将 group system:bootstrappers 和 clusterrole system:node-bootstrapper 绑定。

```
kubectl create clusterrolebinding kubelet-bootstrap \
        --clusterrole=system:node-bootstrapper \
        --group=system:bootstrappers
```

- kubelet 启动后使用 --bootstrap-kubeconfig 向 kube-apiserver 发送 CSR 请求，当这个 CSR 被 approve 后，kube-controller-manager 为 kubelet 创建 TLS 客户端证书、私钥和 --kubeletconfig 文件。

- 注意：kube-controller-manager 需要配置 `--cluster-signing-cert-file` 和 `--cluster-signing-key-file` 参数，才会为 TLS Bootstrap 创建证书和私钥。

#### 9.2.6.启动kubelet

```
systemctl daemon-reload
systemctl enable kubelet
systemctl restart kubelet
systemctl status kubelet
```

#### 9.2.7.批准kubelet的TLS请求

##### 9.2.7.1.查看未授权的CSR请求

```
# kubectl get csr
NAME        AGE     REQUESTOR                 CONDITION
csr-fhrnd   5m11s   system:bootstrap:998dda   Pending
csr-rq28z   7m33s   system:bootstrap:998dda   Pending
```

- 当前均处于Pending状态

##### 9.2.7.2.自动approve CSR请求

创建三个 ClusterRoleBinding，分别用于自动 approve client、renew client、renew server 证书

自动批准 system:bootstrappers 组用户 TLS bootstrapping 首次申请证书的 CSR 请求

```
kubectl create clusterrolebinding auto-approve-csrs-for-group --clusterrole=system:certificates.k8s.io:certificatesigningrequests:nodeclient --group=system:bootstrappers 
```

自动批准 system:nodes 组用户更新 kubelet 自身与 apiserver 通讯证书的 CSR 请求

```
kubectl create clusterrolebinding node-client-cert-renewal --clusterrole=system:certificates.k8s.io:certificatesigningrequests:selfnodeclient --group=system:nodes
```

创建自动批准相关 CSR 请求的 ClusterRole

```
kubectl create clusterrole approve-node-server-renewal-csr --verb=create --resource=certificatesigningrequests/selfnodeserver --resource-name=certificates.k8s.io
```

自动批准 system:nodes 组用户更新 kubelet 10250 api 端口证书的 CSR 请求

```
kubectl create clusterrolebinding node-server-cert-renewal --clusterrole=system:certificates.k8s.io:certificatesigningrequests:selfnodeserver --group=system:nodes
```

查看已有绑定

```
kubectl get clusterrolebindings
```

- auto-approve-csrs-for-group：自动 approve  nodeclient 的第一次 CSR； 注意第一次 CSR 时，请求的 Group 为 system:bootstrappers。
- node-client-cert-renewal：自动 approve selfnodeclient  后续过期的证书，自动生成的证书 Group 为 system:nodes。
- node-server-cert-renewal：自动 approve selfnodeserver 后续过期的证书，自动生成的证书 Group 为 system:nodes。

##### 9.2.7.3.查看kubelet情况

```
# kubectl get csr
NAME        AGE     REQUESTOR                 CONDITION
csr-92pjz   57s     system:node:10.15.1.205   Pending
csr-9l8nq   6m9s    system:node:10.15.1.204   Pending
csr-fhrnd   5m11s   system:bootstrap:998dda   Approved,Issued
csr-rq28z   7m33s   system:bootstrap:998dda   Approved,Issued
```

- Pending 的 CSR 用于创建 kubelet server 证书，需要手动 approve

基于安全性考虑，CSR approving controllers 不会自动 approve kubelet server 证书签名请求，需要手动 approve

```
kubectl certificate approve csr-92pjz csr-9l8nq
```

```
# kubectl get csr
NAME        AGE     REQUESTOR                 CONDITION
csr-92pjz   4m41s   system:node:10.15.1.205   Approved,Issued
csr-9l8nq   9m53s   system:node:10.15.1.204   Approved,Issued
csr-fhrnd   8m55s   system:bootstrap:998dda   Approved,Issued
csr-rq28z   11m     system:bootstrap:998dda   Approved,Issued
```

kube-controller-manager 已经为各个节点生成了kubelet公私钥和kubeconfig

```
ls -la /etc/kubernetes/kubelet.kubeconfig
ls -l /etc/kubernetes/ssl/kubelet*
```

#### 9.2.8.查看端口

```
netstat -lntp| grep kubelet
```

- 10248：healthz http 服务。
- 10250：https 服务，访问该端口时需要认证和授权（即使访问 /healthz 也需要），未开启只读端口 10255。
- 以上端口都提供/metrics和/healthz接口。



### 9.3.安装kube-proxy

#### 9.3.1.生成kube-proxy kubeconfig

使用以下命令生成kubeconfig文件并拷贝至其他node节点

```
export KUBE_APISERVER="https://apiserver.k8sre.com:6443"

# 设置集群参数
kubectl config set-cluster kubernetes \
  --certificate-authority=ca.pem \
  --embed-certs=true \
  --server=${KUBE_APISERVER} \
  --kubeconfig=kube-proxy.kubeconfig

# 设置客户端认证参数
kubectl config set-credentials kube-proxy \
  --client-certificate=kube-proxy.pem \
  --client-key=kube-proxy.key \
  --embed-certs=true \
  --kubeconfig=kube-proxy.kubeconfig

# 设置上下文参数
kubectl config set-context default \
  --cluster=kubernetes \
  --user=kube-proxy \
  --kubeconfig=kube-proxy.kubeconfig

# 设置默认上下文
kubectl config use-context default --kubeconfig=kube-proxy.kubeconfig
```

- `--embed-certs=true` ：将 ca.pem 和 admin.pem 证书内容嵌入到生成的
  kubectl-proxy.kubeconfig 文件中(不加时，写入的是证书文件路径)

#### 9.3.2.配置kube-proxy

/etc/kubernetes/proxy

```
KUBE_PROXY_ARGS="--bind-address=10.15.1.204 \
                 --hostname-override=10.15.1.204 \
                 --kubeconfig=/etc/kubernetes/kube-proxy.kubeconfig \
                 --cluster-cidr=172.32.0.0/16 \
                 --proxy-mode=ipvs \
                 --masquerade-all \
                 --ipvs-min-sync-period=2s \
                 --ipvs-sync-period=3s \
                 --ipvs-scheduler=wlc \
                 --logtostderr=true \
                 --v=4"
```

- `bindAddress`: 监听地址；
- `kubeconfig`: 连接 apiserver 的 kubeconfig 文件；
- `clusterCIDR`: kube-proxy 根据 `--cluster-cidr` 判断集群内部和外部流量，指定 `--cluster-cidr` 或 `--masquerade-all` 选项后 kube-proxy 才会对访问 Service IP 的请求做 SNAT；
- `hostnameOverride`: 参数值必须与 kubelet 的值一致，否则 kube-proxy 启动后会找不到该 Node，从而不会创建任何 ipvs 规则；
- `mode`: 使用 ipvs 模式

#### 9.3.3.配置systemd unit

/usr/lib/systemd/system/kube-proxy.service

```
[Unit]
Description=Kubernetes Kube-Proxy Server
Documentation=https://github.com/kubernetes/kubernetes
After=network.target
Requires=network.service

[Service]
EnvironmentFile=-/etc/kubernetes/proxy
ExecStart=/usr/bin/kube-proxy $KUBE_PROXY_ARGS
Restart=on-failure
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

#### 9.3.4.启动kube-proxy

```
systemctl daemon-reload
systemctl enable kube-proxy
systemctl restart kube-proxy
```

#### 9.3.4.查看端口

```
netstat -lntp| grep kube-proxy
```

- 10249：http prometheus metrics port。
- 10256：http healthz port。



### 9.4.部署网络插件

#### 9.4.1.部署calico(与flannel任选一种部署)

##### 9.4.1.1.calico简介

Calico组件：

- Felix：Calico agent，运行在每个node节点上，为容器设置网络信息、IP、路由规则、iptables规则等
- etcd：calico后端数据存储
- BIRD：BGP Client，负责把Felix在各个node节点上设置的路由信息广播到Calico网络（通过BGP协议）
- BGP Router Reflector：大规模集群的分级路由分发
- Calico：Calico命令行管理工具

##### 9.4.1.2.签发calico访问etcd证书

准备etcd-calico.cnf

```
cat > etcd-calico.cnf << EOF
[ req ]
req_extensions = v3_req
distinguished_name = req_distinguished_name
[req_distinguished_name]
[ v3_req ]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
EOF
```

生成key

```
openssl genrsa -out etcd-calico.key 4096
```

生成证书请求

```
openssl req -new -key etcd-calico.key -out etcd-calico.csr \
        -subj "/CN=etcd/OU=System/C=CN/ST=Shanghai/L=Shanghai/O=k8s" \
        -config etcd-calico.cnf
```

签发证书

```
openssl x509 -req -in etcd-calico.csr \
        -CA ca.pem -CAkey ca.key -CAcreateserial \
        -out etcd-calico.pem -days 1825 \
        -extfile etcd-calico.cnf -extensions v3_req
```

校验证书

```
openssl x509  -noout -text -in etcd-calico.pem
```



##### 9.4.1.3.配置calico

下载calico yaml

```
curl https://docs.projectcalico.org/v3.8/manifests/calico-etcd.yaml -O
```

修改yaml,以下配置项修改为对应pod地址段

```
typha_service_name: "calico-typha"
            - name: CALICO_IPV4POOL_CIDR
              value: "172.48.0.0/12"
            - name: IP_AUTODETECTION_METHOD
              value: "interface=ens192"
            - name: CALICO_IPV4POOL_IPIP
              value: "off"
```

将以下配置删除注释，并添加前面签发的证书（etcd如果配置了TLS安全认证，则还需要指定相应的ca、cert、key等文件）

```
apiVersion: v1
kind: Secret
type: Opaque
metadata:
  name: calico-etcd-secrets
  namespace: kube-system
data:
  etcd-key: (cat etcd-calico.key | base64 | tr -d '\n') #将输出结果填写在这里
  etcd-cert: (cat etcd-calico.pem | base64 | tr -d '\n') #将输出结果填写在这里
  etcd-ca: (cat ca.pem | base64 | tr -d '\n') #将输出结果填写在这里
```
修改configmap
```
kind: ConfigMap
apiVersion: v1
metadata:
  name: calico-config
  namespace: kube-system
data:
  etcd_endpoints: "https://10.15.1.201:2379,https://10.15.1.202:2379,https://10.15.1.203:2379"
  etcd_ca: /calico-secrets/etcd-ca"
  etcd_cert: /calico-secrets/etcd-cert"
  etcd_key: /calico-secrets/etcd-key"
```

ConfigMap部分主要参数：

- etcd_endpoints：Calico使用etcd来保存网络拓扑和状态，该参数指定etcd的地址，可以使用K8S Master所用的etcd，也可以另外搭建。
- calico_backend：Calico的后端，默认为bird。
- cni_network_config：符合CNI规范的网络配置，其中type=calico表示，Kubelet从 CNI_PATH(默认为/opt/cni/bin)找名为calico的可执行文件，用于容器IP地址的分配。

通过DaemonSet部署的calico-node服务Pod里包含两个容器：

- calico-node：calico服务程序，用于设置Pod的网络资源，保证pod的网络与各Node互联互通，它还需要以HostNetwork模式运行，直接使用宿主机网络。
- install-cni：在各Node上安装CNI二进制文件到/opt/cni/bin目录下，并安装相应的网络配置文件到/etc/cni/net.d目录下。

calico-node服务的主要参数：

- CALICO_IPV4POOL_CIDR： Calico IPAM的IP地址池，Pod的IP地址将从该池中进行分配。
- CALICO_IPV4POOL_IPIP：是否启用IPIP模式，启用IPIP模式时，Calico将在node上创建一个tunl0的虚拟隧道。
- FELIX_LOGSEVERITYSCREEN： 日志级别。
- FELIX_IPV6SUPPORT ： 是否启用IPV6。

​     IP Pool可以使用两种模式：BGP或IPIP。使用IPIP模式时，设置 CALICO_IPV4POOL_IPIP="always"，不使用IPIP模式时，设置为"off"，此时将使用BGP模式。

 	IPIP是一种将各Node的路由之间做一个tunnel，再把两个网络连接起来的模式，启用IPIP模式时，Calico将在各Node上创建一个名为"tunl0"的虚拟网络接口。

将以下镜像修改为自己的镜像仓库

```
image: calico/cni:v3.8.2
image: calico/pod2daemon-flexvol:v3.8.2
image: calico/node:v3.8.2
image: calico/kube-controllers:v3.8.2
```

```
kubectl apply -f calico-etcd.yaml
```

主机上会生成了一个tun10的接口

```
# ip route
172.54.2.192/26 via 10.15.1.205 dev tunl0 proto bird onlink
blackhole 172.63.185.0/26 proto bird
# ip route
blackhole 172.54.2.192/26 proto bird
172.63.185.0/26 via 10.15.1.204 dev tunl0 proto bird onlink
```

- 如果设置CALICO_IPV4POOL_IPIP="off" ，即不使用IPIP模式，则Calico将不会创建tunl0网络接口，路由规则直接使用物理机网卡作为路由器转发。

#### 9.4.2.部署Flannel(与calico任选一种部署)

```
wget https://raw.githubusercontent.com/coreos/flannel/master/Documentation/k8s-manifests/kube-flannel-rbac.yml
wget https://raw.githubusercontent.com/coreos/flannel/master/Documentation/k8s-manifests/kube-flannel-legacy.yml
```

修改kube-flannel-legacy，以下配置项修改为对应pod地址段

```
  net-conf.json: |
    {
      "Network": "172.48.0.0/12",
      "Backend": {
        "Type": "vxlan"
      }
    }
```

Flannel支持的后端：

- VXLAN：使用内核中的VXLAN封装数据包。
- host-gw：使用host-gw通过远程机器IP创建到子网的IP路由。
- UDP：如果网络和内核阻止使用VXLAN或host-gw，请仅使用UDP进行调试。
- ALIVPC：在阿里云VPC路由表中创建IP路由，这减轻了Flannel单独创建接口的需要。阿里云VPC将每个路由表的条目限制为50。
- AWS VPC：在AWS VPC路由表中创建IP路由。由于AWS了解IP，因此可以将ELB设置为直接路由到该容器。AWS将每个路由表的条目限制为50。
- GCE：GCE不使用封装，而是操纵IP路由以实现最高性能。因此，不会创建单独的Flannel 接口。GCE限制每个项目的路由为100。
- IPIP：使用内核IPIP封装数据包。IPIP类隧道是最简单的。它具有最低的开销，但只能封装IPv4单播流量，因此您将无法设置OSPF，RIP或任何其他基于组播的协议。

部署Flannel

```
kubectl apply -f kube-flannel-rbac.yml -f kube-flannel-legacy.yml
```



### 9.5.验证服务

#### 9.5.1.检查node是否注册

```
kubectl get nodes
ipvsadm -ln
```

- 此时能看到已注册node节点
- 在Node节点上执行`ipvsadm -ln`可以看到kubernetes的Service IP的规则

#### 9.5.2.kubelet提供API接口

如执行`kubectl exec -it nginx-ds-6ghhdf bash`,kube-apiserver会向kubelet发送如下请求：

```
POST /exec/default/nginx-ds-5rmws/my-nginx?command=sh&input=1&output=
1&tty=1
```

kubelet 接收 10250 端口的 https 请求，可以访问如下资源：

- /pods、/runningpods
- /metrics、/metrics/cadvisor、/metrics/probes
- /spec
- /stats、/stats/container
- /logs
- /run/、/exec/, /attach/, /portForward/, /containerLogs/



## 十、部署集群插件

### 10.1.部署coredns

#### 10.1.1.修改配置文件

在kubernets的二进制中已经有相应的yaml

```
tar zxvf kubernetes-src.tar.gz
cd kubernetes/cluster/addons/dns/coredns
CLUSTER_DNS_DOMAIN="cluster.local"
CLUSTER_DNS_SVC_IP="172.32.0.2"
sed -i -e "s@__PILLAR__DNS__DOMAIN__@${CLUSTER_DNS_DOMAIN}@" -e "s@__PILLAR__DNS__SERVER__@${CLUSTER_DNS_SVC_IP}@" coredns.yaml.base
//gcr.azk8s.cn是Azure中国镜像，建议使用私有镜像仓库
sed -i "s@k8s.gcr.io/coredns:1.3.1@gcr.azk8s.cn/google-containers/coredns:1.3.1@" coredns.yaml.base
```
#### 10.1.2.创建coredns
```
mv coredns.yaml.base coredns.yaml
kubectl apply -f coredns.yaml
```

#### 10.1.3.验证coredns

```
kubectl exec nginx-f9dbcb664-bh5td nslookup kube-dns.kube-system.svc.cluster.local.
```

#### 10.1.4.配置外部dns

```
  Corefile: |
    .:53 {
        errors
        health
        kubernetes cluster.local. in-addr.arpa ip6.arpa {
            pods insecure
            upstream
            fallthrough in-addr.arpa ip6.arpa
        }
        prometheus :9153
        proxy . /etc/resolv.conf
        cache 30
        reload
        loadbalance
    }
    .anymb.com {
    forward . 10.0.13.100 10.0.3.162 10.0.3.223
    }
```



### 10.2.部署metrics-server

#### 10.2.1.metrics server简介

​	metrics-server通过kube-apiserver发现所有节点，然后调用kubelet APIs（通过https接口）获得各节点和Pod的CPU、Memory等资源使用情况。

从kubernetes1.12开始，kubernets的安装脚本移除了Heapster，从1.13开始完全移除了对Heapster的支持，heapster不再维护。

替代方案：

- 用于支持自动扩缩容HPA：metrics-server
- 通用的监控方案：Prometheus
- 事件传输：使用第三方工具传输、归档kubernetes events

#### 10.2.2.配置metrics-server

```
git clone https://github.com/kubernetes-incubator/metrics-server.git
cd metrics-server/deploy/1.8+/
```

创建证书的secret

```
kubectl create secret generic metrics-server-certs --from-file=/etc/kubernetes/ssl/proxy-client.key --from-file=/etc/kubernetes/ssl/proxy-client.pem -n kube-system
```

修改`metrics-server-deployment.yaml` 文件，修改成以下内容

```
    spec:
      serviceAccountName: metrics-server
      hostNetwork: true
      dnsPolicy: ClusterFirstWithHostNet
      volumes:
      - name: tmp-dir
        emptyDir: {}
      - name: metrics-server-certs
        secret:
          secretName: metrics-server-certs
      containers:
      - name: metrics-server
        image: gcr.azk8s.cn/google-containers/metrics-server-amd64:v0.3.3
        imagePullPolicy: Always
        args:
        - --metric-resolution=30s
        - --tls-cert-file=/certs/proxy-client.pem
        - --tls-private-key-file=/certs/proxy-client.key
        - --kubelet-preferred-address-types=InternalIP,Hostname,InternalDNS,ExternalDNS,ExternalIP
        volumeMounts:
        - name: tmp-dir
          mountPath: /tmp
        - name: metrics-server-certs
          mountPath: /certs
```
- 因为我master节点没有运行网络插件，master节点无法访问pod，所以，这里我使用hostNetwork方式部署。

修改镜像地址（建议修改为私有镜像仓库地址）

```
sed -i "s@k8s.gcr.io/metrics-server-amd64:v0.3.3@gcr.azk8s.cn/google-containers/metrics-server-amd64:v0.3.3@" metrics-server-deployment.yaml
```

- --metric-resolution=30s：从 kubelet 采集数据的周期。
- --kubelet-preferred-address-types：优先使用 InternalIP 来访问 kubelet，这样可以避免节点名称**没有 DNS 解析**记录时，通过节点名称调用节点 kubelet API 失败的情况（未配置时默认的情况）。

#### 10.2.3.安装metrics-server

```
kubectl create -f .
```

#### 10.2.4.查看输出的metrics

```
kubectl get --raw "/apis/metrics.k8s.io/v1beta1" | jq .
kubectl get --raw "/apis/metrics.k8s.io/v1beta1/nodes" | jq .
kubectl get --raw "/apis/metrics.k8s.io/v1beta1/pods" | jq .
```

#### 10.2.5.查看集群资源

```
kubectl top node
```



### 10.3.部署helm

```
wget https://get.helm.sh/helm-v3.0.0-alpha.2-linux-amd64.tar.gz
tar zxvf helm-v3.0.0-alpha.2-linux-amd64.tar.gz
mv linux-amd64/helm /usr/bin/
```

初始化，并添加azure国内repo及阿里云repo

```
helm init --stable-repo-url http://mirror.azure.cn/kubernetes/charts
helm repo add apphub https://apphub.aliyuncs.com/
```



### 10.4.部署Ingress-controller

```
helm install --name nginx-ingress stable/nginx-ingress -n nginx-ingress \
     --set controller.image.repository="quay.azk8s.cn/kubernetes-ingress-controller/nginx-ingress-controller" \
     --set controller.hostNetwork=true \
     --set controller.daemonset.useHostPort=true
```



### 10.5.部署Dashboard

```
helm install kubernetes-dashboard stable/kubernetes-dashboard \
             --namespace kube-system \
             --set ingress.enabled=true,rbac.clusterAdminRole=true,ingress.hosts[0]=dashboard.k8sre.com,image.repository=gcr.azk8s.cn/google_containers/kubernetes-dashboard-amd64,image.tag=v1.10.1
```

配置登录token

```
apiVersion: v1
kind: ServiceAccount
metadata:
  name: admin-k8s
  namespace: kube-system

---
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: ClusterRoleBinding
metadata:
  name: admin-k8s
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: admin-k8s
  namespace: kube-system
```

```
echo <token> |base64 -d
```



### 10.6.部署harbor

#### 10.6.1.前提条件

- redis
- postgresql
- 存储

请自行保证以上资源的高可用性。

#### 10.6.2.部署harbor


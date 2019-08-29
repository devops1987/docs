# etcd高可用集群搭建

etcd是 CoreOS 团队发起的开源项目，基于 Go 语言实现，做为一个分布式键值对存储，通过分布式锁，leader选举和写屏障(write barriers)来实现可靠的分布式协作。主要用于分享配置和服务发现。 
● 简单：支持 curl 方式的用户 API (HTTP+JSON) 
● 安全：可选 SSL 客户端证书认证 
● 快速：单实例可达每秒1000次写操作 
● 可靠：使用 Raft 实现分布式

这里部署一个基于TLS（Self-signed certificates）的安全、快速灾难恢复（Disaster Recovery, SNAPSHOT）的高可用（High Availability）的etcd集群。使用TLS证书对证书通信进行加密，并开启基于CA根证书签名的双向数字证书认证。

搭建etcd集群有3种方式，分别为Static, etcd Discovery, DNS Discovery。本文仅以DNS Discovery方式展示一次集群搭建过程。



## 一、环境信息

CentOS 7.4

```
10.15.1.201 etcd01
10.15.1.202 etcd02
10.15.1.203 etcd03
hostnamectl set-hostname etcd01
```

CoreOS官方推荐集群规模5个为宜，为了简化本文仅以3个节点为例。

官方建议配置：

```
硬件            通常场景                    重负载
CPU           2-4 cores                 8-18 cores 
Memory        8GB                       16GB-64GB
Disk          50 sequential IOPS        500 sequential IOPS
Network       1GbE                      10GbE
```



## 二、TLS密钥和证书

etcd支持通过TLS加密通信，TLS channels可被用于集群peer间通信加密，以及client端traffic加密。Self-signed certificates与Automatic certificates两种安全认证形式，其中Self-signed certificates:自签名证书既可以加密traffic也可以授权其连接。本文以Self-signed certificates为例，使用Cloudflare的cfssl很容易生成集群所需证书。

下面介绍使用openssl生成所需要的私钥和证书.

### 2.1、签发CA证书

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

### 2.2、签发etcd证书

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

对生成的证书可以使用cfssl或openssl查看：

```
cfssl-certinfo -cert kubernetes.pem
openssl x509  -noout -text -in  kubernetes.pem
```



###  2.3、配置dns(可选)

dns 发现主要通过dns服务来记录集群中各节点的域名信息，各节点到dns服务中获取相互的地址信息，从而建立集群。etcd各节点通过--discovery-serv配置来获取域名信息,节点间将获取以下域名下的各节点域名，

- _etcd-server-ssl._tcp.example.com
- _etcd-server._tcp.example.com

如果_etcd-server-ssl._tcp.example.com下有值表示节点间将使用ssl协议，相反则使用非ssl。

- _etcd-client._tcp.example.com
- _etcd-client-ssl._tcp.example.com

按照以下方式添加dns解析

```
# dig @223.5.5.5 +noall +answer SRV _etcd-server._tcp.msfar.cn
_etcd-server._tcp.msfar.cn. 600	IN	SRV	0 100 2380 etcd02.msfar.cn.
_etcd-server._tcp.msfar.cn. 600	IN	SRV	0 100 2380 etcd01.msfar.cn.
_etcd-server._tcp.msfar.cn. 600	IN	SRV	0 100 2380 etcd03.msfar.cn.

# dig @223.5.5.5 +noall +answer etcd01.msfar.cn etcd02.msfar.cn etcd03.msfar.cn
etcd01.msfar.cn.	600	IN	A	172.31.150.86
etcd02.msfar.cn.	600	IN	A	172.31.150.87
etcd03.msfar.cn.	600	IN	A	172.31.150.88
```



## 3、安装

### 3.1.安装etcd

```
yum -y install etcd
```

### 3.2.修改主配置文件

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

### 3.4.配置systemd unit

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

### 3.5.配置etcd数据目录

```
mkdir -p /data/lib/etcd
chown -R etcd. /data/lib/etcd
```

### 3.6.启动服务

```
systemctl daemon-reload 
systemctl restart etcd
systemctl enable etcd
```

### 3.7.集群验证

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



### 3.8.集群扩容

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


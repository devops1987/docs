## 一、概述

1、目的

为了加快和提高服务器资源交付应用和投入生产的效率，服务器的部署工作要做到规
范化，标准化；在规范化，标准化的前提下，进一步实现自动化/半自动化；从而最终提高
工作效率，降低遗漏等错误发生率。
鉴于以上缘由，催化了此文档的产生，一方面也是为了方便部署时的参考，防止在部
署过程中细节的忽视和遗漏，另一方面也为了以后的自动化批量部署做准备。
本文亦可作为对新员工的培训资料。

2、适合阅读对象

基础架构团队的服务器部署人员；主机系统以及中间件管理人员；网络管理人员；数据库管理员，新入职员工等。



## 二、组件安装

###2.1、安装JDK

```
yum -y install java-1.8.0-openjdk
```

验证

```
java -version
```



### 2.2、安装maven

```
yum -y install maven
```

验证

```
mvn -version
```



###2.3、安装Jenkins

####2.3.1、配置jenkins

下载war包

```
curl -O https://mirrors.tuna.tsinghua.edu.cn/jenkins/war-stable/2.176.3/jenkins.war
```

创建jenkins用户

```
groupadd -g 600 jenkins
useradd -u 600 -g 600 jenkins
```

配置jenkins的systemd启动文件

```
cat > /usr/lib/systemd/system/jenkins.service <<EOF
[Unit]
Description=Jenkins

[Service]
User=jenkins
Environment=JENKINS_HOME=/data/jenkins/home
ExecStart=/usr/bin/java -Xmx8g -Xms8g -jar -Dfile.encoding=UTF-8 -Duser.timezone=GMT+08 /opt/jenkins.war --httpPort=8080
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
```

启动jenkins

```
systemctl daemon-reload
systemctl enable jenkins
systemctl start jenkins
```
另一种启动方式：
```
java -Xms256m -Xmx512m -DJENKINS_HOME=/data/jenkins/home -jar /opt/jenkins.war --httpPort=8080
```

maven打包

```
mvn clean install -DskipTests=true -Dfile.encoding=UTF-8
```

####2.3.2、配置ldap

```
Server:ldap://172.16.9.9
ROOT DN:ou=op,dc=anymb,dc=com
User search filter:sAMAccountName={0}
Group search filter:(&(objectclass=group)(cn={0}))
Group membership:Search for ldap group containing user:(member={0})
Manager DN:administrator@anymb.com
Display Name LDAP attribute:Name
Email Address LDAP attribute:mail
Environment Properties:
						com.sun.jndi.ldap.connect.timeout
						5000
						com.sun.jndi.ldap.read.timeout
						10000
```

- 完成ldap后，切记先添加一个管理员用户，ldap配置会覆盖admin权限，不能再使用admin登录

####2.3.3、添加jenkins agent

在控制台添加node节点，然后编辑脚本

```
#! /bin/bash

name="k8s"
secret="xxxxxxxxxxxxxx"
url="https://ci.anymb.com/computer/$name/slave-agent.jnlp"
args="-Xmx8g -Xms8g"
dir_jks="/data/web"
dir_lib="$dir_jks/lib"

if [ "`whoami`" = "root" ]
then
    su_cmd="su - jenkins -s /bin/sh -c"
fi

$su_cmd "java -jar $args $dir_lib/agent.jar -jnlpUrl $url -secret $secret -workDir $dir_jks/home"
```

启动容器

```
docker run -itd -e ENV_NAME="java" -e JKS_SECRET="dc238c69ca6102b79e039aaf07ec4acd58332122164e4f5c41e2bbadffebf03c" -e JKS_DOMAINNAME="https://ci.taojiji.work" -e JKS_ARGS="-Xmx4g -Xms4g" -e JKS_DIR="/data/jenkins" -v /data/jenkins:/data/jenkins --name java registry.taojiji.work/library/jenkins:java
```



构建过程中常见错误及解决方法

1、找不到pom.xml？

pom.xml文件是必须的，maven创建的项目都会有这个文件，其他项目支持maven且有这个文件才行。

2、maven创建项目时在generation project in interactive mode卡住了？

一直等待结束，大概一个小时左右，只是首次会出现这个情况。也可以在命令后加参数：-DarchetypeCatalog=internal

mvn archetype:generate  -DgroupId=helloworld -DartifactId=helloworld -DarchetypeCatalog=internal 

3、在执行创建工作空间的时候，创建不成功，出现错误：java.lang.NoSuchFieldError: DEFAULT_USER_SETTINGS_FILE？？

这是jar冲突，版本太高引起的，maven3.5.0版本有这个问题，推荐使用maven3.3.9版本就可以了。

必装插件

```
Pipeline Utility Steps
Modern Status
user build vars
```



```
        lifecycle:
          preStop:
            exec:
              command: ["/bin/bash", "-c", "sleep 30"]
```


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

### 3、操作系统和 GitLab 的版本

操作系统版本：Ubuntu-16.04/CentOS7
GitLab 版本：11.7.5
注意：因为 GitLab 自定义安装比较麻烦，安装组件较多，所以我们采用官方的一键安
装包
DEB、RPM包的下载地址：https://packages.gitlab.com/gitlab/gitlab-ce

### 4、Gitlab权限管理

Gitlab用户在组中有五种权限：Guest、Reporter、Developer、Master、Owner

Guest：可以创建issue、发表评论，不能读写版本库
Reporter：可以克隆代码，不能提交，QA、PM可以赋予这个权限
Developer：可以克隆代码、开发、提交、push，RD可以赋予这个权限
Master：可以创建项目、添加tag、保护分支、添加项目成员、编辑项目，核心RD负责人可以赋予这个权限
Owner：可以设置项目访问权限 - Visibility Level、删除项目、迁移项目、管理组成员，开发组leader可以赋予这个权限
Gitlab中的组和项目有三种访问权限：Private、Internal、Public

Private：只有组成员才能看到
Internal：只要登录的用户就能看到
Public：所有人都能看到
开源项目和组设置的是Internal

### 5、依赖工具的安装

安装需要的依赖工具：

Ubuntu16.04:

vim /etc/apt/sources.list.d/gitlab-ce.list

```
deb http://mirrors.tuna.tsinghua.edu.cn/gitlab-ce/debian stretch main
```

```
apt-get -y install curl openssh-server ca-certificates postfix
curl https://packages.gitlab.com/gpg.key 2> /dev/null | sudo apt-key add - &>/dev/null
apt-get update
apt-get -y install gitlab-ce
```

CentOS7:

```
yum install -y curl policycoreutils-python openssh-server openssh-clients
```

vim /etc/yum.repos.d/gitlab-ce.repo

```
[gitlab-ce]
name=Gitlab CE Repository
baseurl=https://mirrors.tuna.tsinghua.edu.cn/gitlab-ce/yum/el$releasever/
gpgcheck=0
enabled=1
```

```
yum makecache
yum install gitlab-ce
```

配置postfix 使得服务器可以发邮件：
vim /etc/postfix/main.cf
以下配置：

```
inet_interfaces = localhost
inet_protocols = all
```
改成：
```
inet_interfaces = 127.0.0.1 #只能接受内部邮件，其它邮件不接受
inet_protocols = all
```
然后

Ubuntu16.04:

```
sudo update-rc.d -f postfix enable
sudo /etc/init.d/postfix restart
```

CentOS7:

```
systemctl enable postfix
systemctl restart postfix
```

### 6、修改几处 GitLab 的配置

vi /etc/gitlab/gitlab.rb
1) 修改external_url 'http://git.msfar.cn'  
​	#改成你自己的对外域名

2) 修改你的repo 保存的地方
```
git_data_dir "/data/gitlab/git-data"
```
3) 修改你的repo 备份保存的地方
```
gitlab_rails['backup_path'] = "/data/gitlab/backups"
```
4) 修改postgresql数据库所在目录

```
postgresql['data_dir'] = "/data/gitlab/postgresql/data"
```

5) 修改邮箱配置

```
 gitlab_rails['gitlab_email_from'] = 'gitlab@msfar.cn'
 gitlab_rails['smtp_enable'] = true
 gitlab_rails['smtp_address'] = "smtp.exmail.qq.com"
 gitlab_rails['smtp_port'] = 465
 gitlab_rails['smtp_user_name'] = "gitlab@msfar.cn"
 gitlab_rails['smtp_password'] = "xxxxxx"
 gitlab_rails['gitlab_email_from'] = 'gitlab@msfar.cn'
 gitlab_rails['smtp_authentication'] = "login"
 gitlab_rails['smtp_enable_starttls_auto'] = true
 gitlab_rails['smtp_tls'] = true
```
6)修改ldap配置

```
gitlab_rails['ldap_enabled'] = true
  
gitlab_rails['ldap_servers'] = YAML.load <<-'EOS'
   main: # 'main' is the GitLab 'provider ID' of this LDAP server
     label: 'LDAP'
     host: '172.16.70.224'
     port: 389
     uid: 'sAMAccountName'
     bind_dn: 'administrator@msfar.cn'
     password: 'Msfar2018'
     encryption: 'plain' # "start_tls" or "simple_tls" or "plain"
     active_directory: true
     allow_username_or_email_login: true
     block_auto_created_users: false
     base: 'ou=dev,dc=msfar,dc=cn'
     user_filter: ''
EOS
```

7)修改时区

```
gitlab_rails['time_zone'] = 'Asia/Shanghai'
```

8)默认禁止创建组

```
gitlab_rails['gitlab_default_can_create_group'] = false
```

9)备份配置

```
gitlab_rails['manage_backup_path'] = true
gitlab_rails['backup_path'] = "/data/gitlab/backups"
gitlab_rails['backup_archive_permissions'] = 0644
gitlab_rails['backup_keep_time'] = 86400
```

10)解决gitlab并发超过30引起IP被封

```
 gitlab_rails['rack_attack_git_basic_auth'] = {
   'enabled' => true,
   'ip_whitelist' => ["127.0.0.1","39.97.128.27"],
   'maxretry' => 100,
   'findtime' => 5,
   'bantime' => 60
 }
```

11)使用外部redis

```
redis['enable'] = false
gitlab_rails['redis_host'] = "xxxxxxxxxxxx.redis.rds.aliyuncs.com"
gitlab_rails['redis_port'] = 6379
gitlab_rails['redis_password'] = "xxxxxxxxxxxx"
gitlab_rails['redis_database'] = 0
```

12)使用外部postgresql

```
postgresql['enable'] = false
gitlab_rails['db_adapter'] = 'postgresql'
gitlab_rails['db_encoding'] = 'utf8'
gitlab_rails['db_database'] = 'gitlab'
gitlab_rails['db_username'] = 'gitlab'
gitlab_rails['db_password'] = 'xxxxxxxx'
gitlab_rails['db_host'] = 'rm-xxxxxx.pg.rds.aliyuncs.com'
postgresql['port'] = 3433
```

13)启动https

```
nginx['enable'] = true
nginx['client_max_body_size'] = '250m'
nginx['redirect_http_to_https'] = true
nginx['ssl_certificate'] = "/etc/ssl/msfar.cn.pem"
nginx['ssl_certificate_key'] = "/etc/ssl/msfar.cn.key"
```



然后进行配置：

```
gitlab-ctl reconfigure
```
注意：GitLab 的配置以后也随时可以修改，修改完执行 gitlab-ctl reconfigure，再重
启一下gitLab 即可生效。



###7、启动，停止，重启 GitLab

```
gitlab-ctl start
gitlab-ctl stop
gitlab-ctl restart
```
看到一下几个组件都出来了就对了



### 8、开始使用 GitLab

默认的账号密码：
```
Username: root
Password: 5iveL!fe
```

在你的第一次访问，将被重定向到一个密码重置屏幕提供初始的管理员帐户的密码。
输入你想要的密码，您将被重定向到登录屏幕。

**注意：**千万记得root 登录后，先去改 root的邮箱，不然忘记了 root的密码无法找回。



### 9、迁移，备份，恢复 GitLab 的库

#### 9.1、Gitlab 创建备份

使用 Gitlab 一键安装包安装 Gitlab 非常简单, 同样的备份恢复与迁移也非常简单. 使用
一条命令即可创建完整的Gitlab 备份：
```
gitlab-rake gitlab:backup:create
gitlab-rake gitlab:backup:create SKIP=db
```

使用以上命令会在之前配置 GitLab 的时候你设置的备份目录下，创建一个名称类似为
1393513186_gitlab_backup.tar 的压缩包，这个压缩包就是 Gitlab整个的完整部分，其
中开头的1393513186 是备份创建的日期。
Gitlab 自动备份
```
crontab -e
0 5 * * * /usr/bin/gitlab-rake gitlab:backup:create
```



#### 9.2、Gitlab 恢复

 停止相关数据连接服务
```
gitlab-ctl stop unicorn
gitlab-ctl stop sidekiq
```
从 1393513186 编号备份中恢复
```
gitlab-rake gitlab:backup:restore BACKUP=1393513186
```
启动Gitlab
```
gitlab-ctl start
```



#### 9.3、Gitlab 迁移

迁移如同备份与恢复的步骤一样, 只需要将老服务器自定义的备份目录下的备份文件拷
贝到新服务器上的自定义备份目录下即可。注意：新服务器上的 Gitlab 的版本必须与创建
备份时的Gitlab 版本号相同。



### 10、常用操作

####  git添加文件

当前目录所有文件添加到暂存区

```
git add .   #提交新文件(new)和被修改(modified)文件，不包括被删除(deleted)文件
git add -u  #提交被修改(modified)和被删除(deleted)文件，不包括新文件(new)
git add -A  #是上面两个功能的合集（git add --all的缩写)
```



#### git版本回退

回退到上一个版本

```
git reset --hard HEAD^
```

回退到指定版本

```
git log --pretty=oneline  #查看commit id
git reset --hard commit_id
```

注意：若git log中看不到想要回退的提交记录，可以使用`git reflog`命令查看命令记录。

撤销修改

```
git checkout -- file
```

注意：1、若file修改后没有放到暂存区，执行撤销修改就回到和版本库一样的状态

​	    2、若已添加到暂存区后，又做了修改，执行撤销就回到添加暂存区后的状态

把暂存区的修改撤销，重新放回工作区

```
git reset HEAD file
```

删除文件

```
git rm file
```



#### git分支管理

显示所有分支

```
git branch
```

从当前分支创建一个叫yunwei的分支

```
git branch yunwei
```

切换到yunwei分支

```
git checkout yunwei
```

相当于以上两条命令的组合

```
git checkout -b yunwei
```

切换远程分支

```
git branch -r
git remote set-url origin remote_git_address
```

把yunwei分支的代码合并到master上

```
git checkout master
git merge (--no-ff) yunwei   #--no-ff 不使用fast forward模式，fast forward删除分枝后，会丢掉分枝信息
```

删除yunwei分支，不能在被删除分支上执行

```
git branch -d yunwei
```

更新yunwei分支，与本地的master分支合并

```
git pull origin yunwei:master
```

远程分支与当前分支合并

```
git pull origin yunwei
```

查看合并分支图

```
git log --graph --pretty=oneline --abbrev-commit
```

保存当前工作

```
git stash
```

查看保存的工作

```
git stash list
```

恢复保存的工作

```
git stash apply  #恢复后stash内容不删除
git stash drop   #恢复后同事删除stash内容
```

删除一个没有被合并过的分支

```
git branch -D name
```



#### Git标签管理

查看所有标签

```
git tag
```

从当前分支创建一个名为v1.0的标签

```
git tag v1.0
```

删除名为v1.0的标签

```
git tag -d v1.0
```

已提交版本打标签

```
git log --pretty=oneline --abbrev-commit
git tag v1.01 commit_id
```

查看标签信息

```
git show v1.0
```

创建带有说明的标签，'-a'指定标签明，'-m'指定说明

```
git tag -a v1.0 -m "hahhahahha" commit_id
```

推送一个标签到远程

```
git push origin v1.0
```

推送所有标签到远程

```
git push origin --tags
```

删除远程标签

```
git tag -d v1.0  #先从本地删除
git push origin :refs/tag/v1.0 #再从远程删除
```



#### 特性分支

从develop分支创建，用于特性开发，完成后要合并回develop分支。 
操作过程：

```
git checkout -b newfeature develop     #从develop分支创建newfeature特性分支 
git checkout develop 				   #开发完成后，需要合并回develop分支，先切换到develop分支 
git merge --no-ff newfeature           #合并回develop分支
git branch -d newfeature               #删除特性分支 
git push origin develop                #把合并后的develop分支推送到远程仓库
```

#### 发布分支

从develop分支创建，用于预发布版本，允许小bug修复，完成后要合并回develop和master。 
操作过程：

```
git checkout -b release-1.2 develop    #从develop分支创建一个发布分支 
git checkout master                    #切换到master分支，准备合并 
git merge --no-ff release-1.2          #把release-1.2分支合并到master分支 
git tag 1.2                            #从master分支打一个标签 
git checkout develop                   #切换到develop分支，准备合并 
git merge --no-ff release-1.2          #把release-1.2分支合并到develop分支 
git branch -d release-1.2              #删除这个发布分支
```

#### 修复分支

从master分支创建，用于生产环境上的Bug修复，完成后要合并回develop和master。 
操作过程：

```
git checkout -b hotfix-1.2.1 master    #从master分支创建一个Bug修复分支 
git checkout master                    #切换到master分支，准备合并 
git merge --no-ff hotfix-1.2.1         #合并到master分支 
git tag 1.2.1                          #为master分支创建一个标签 
git checkout develop                   #切换到develop分支，准备合并 
git merge --no-ff hotfix-1.2.1         #合并到develop分支 
git branch -d hotfix-1.2.1             #删除hotfix-1.2.1分支 
```



从原地址克隆一份裸版本库

```
git clone --bare https://git.msfar.cn/jenkins/api.git
```

然后到新的 Git 服务器上创建一个新项目

```
mkdir new_project_name.git
git init --bare new_project_name.git
git remote set-url origin http://git.msfar.cn/jenkins/new_api.git
```

以镜像推送的方式上传代码

```
git push --mirror http://git.msfar.cn/jenkins/new_api.git
```
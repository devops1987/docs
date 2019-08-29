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

3、系统和软件版本

Linux：CentOS7
Openresty: 1.15.8.1



## 二、安装openresty

### 2.1、安装基础依赖包

```
yum -y install pcre-devel openssl-devel gcc curl
```
### 2.2、安装openresty

下载解压

```
curl -Ljk https://openresty.org/download/openresty-1.15.8.1.tar.gz | tar zxf -
cd openresty-1.15.8.1
```

编译

```
./configure --prefix=/opt/apps/openresty --user=work --group=work --with-ipv6 --with-http_stub_status_module --with-http_v2_module --with-http_gzip_static_module --with-http_realip_module --with-http_flv_module --with-http_mp4_module --with-stream --with-stream_ssl_module --with-stream_ssl_preread_module --with-http_ssl_module --with-pcre-jit --with-http_addition_module --with-http_auth_request_module --with-http_secure_link_module --with-http_random_index_module --with-http_sub_module --with-http_dav_module  --with-threads 
```
配置项含义：

--with-file-aio//启用文件修改支持

--with-http_stub_status_module//启用状态统计

--with-http_gzip_static_module//启用gzip静态压缩

--with-http_flv_module //启用flv模块，提供寻求内存使用基于时间的偏移量文件

--with_http_ssl_module//启用ssl模块，提供HTTPS支持

安装

```
make && make install
```



### 2.3、配置环境变量

```
vim /etc/profile
#openresty
export PATH="$PATH:/opt/apps/openresty/nginx/sbin"
```



### 2.4、修改主配置文件

```
cp  prometheus.lua /opt/apps/openresty/nginx/conf
mkdir /data/logs/nginx
cd /opt/apps/openresty/nginx/conf
mkdir vhost
```
vim nginx.conf

```
#设置nginx运行用户
user  nginx;

#设置nginx进程,一般设置为cpu的核数
worker_processes  auto;

#nginx进程绑定cpu
worker_cpu_affinity auto;
#worker_cpu_affinity 00000001 00000010;
#worker_cpu_affinity 0001 0010 0100 1000;
#worker_cpu_affinity 00000001 00000010 00000100 00001000 00010000 00100000 01000000 10000000;

#nginx进程打开的最多文件描述符数
worker_rlimit_nofile 65535;

error_log  /var/log/nginx/error.log  crit;
#error_log  /var/log/nginx/error.log  notice;
#error_log  /var/log/nginx/error.log  info;

pid        /run/nginx.pid;

events {
    # 表示每个工作进程的最大连接数
    worker_connections  10240;
    use epoll;
}

http {

    #设定mime类型,类型由mime.type文件定义
    include            mime.types;
    default_type       application/octet-stream;
    charset            utf-8;
    #开启文件高效传输模式
    sendfile           on;
    tcp_nopush         on;
    tcp_nodelay        on;
    #禁止显示服务器信息
    server_tokens      off;

    #设定日志格式
    log_format  json  '{"@timestamp":"$time_iso8601",'
                      '"@source":"$server_addr",'
                      '"host":"$host",'
                      '"remote_addr":"$remote_addr",'
                      '"remote_user":"$remote_user",'
                      '"remote_port":"$remote_port",'
                      '"http_x_forwarded_for":"$http_x_forwarded_for",'
                      '"status":"$status",'
                      '"request_uri": "$request_uri", '
                      '"request_time":"$request_time",'
                      '"request_method":"$request_method", '
                      '"request_body":"$request_body",'
                      '"body_bytes_sent":"$body_bytes_sent",'
                      '"protocol":"$server_protocol",'
                      '"port":"$server_port",'
                      '"upstream_status":"$upstream_status",'
                      '"upstream_response_time":"$upstream_response_time",'
                      '"upstream_addr":"$upstream_addr",'
                      '"via":"$http_via",'
                      '"http_referer":"$http_referer",'
                      '"http_user_agent":"$http_user_agent"'
                      '}';
 
    access_log  /var/log/nginx/access.log  json;

    #连接超时时间
    keepalive_timeout     65;
    client_header_timeout 20s;
    send_timeout          25s;
 
    #开启gzip压缩
    gzip                  on;
    gzip_vary             on;
    gzip_min_length       1k;
    gzip_buffers          4 32k;
    gzip_http_version     1.0;
    gzip_comp_level       2;
    gzip_types            text/xml application/xml application/atom+xml application/rss+xml application/xhtml+xml image/svg+xml text/javascript application/javascript application/x-javascript text/x-json application/json application/x-web-app-manifest+json text/css text/plain text/x-component font/opentype application/x-font-ttf application/vnd.ms-fontobject image/x-icon;
 
    #设定请求缓冲
    client_header_buffer_size     128k;
    client_max_body_size          200m;
    client_body_buffer_size       1m;
    large_client_header_buffers   4 128k;
    server_names_hash_bucket_size 128;
    fastcgi_buffers               32 8k;

    #ssl配置
    ssl_protocols                 TLSv1 TLSv1.1 TLSv1.2 TLSv1.3;
    ssl_ciphers                   TLS13-AES-256-GCM-SHA384:TLS13-CHACHA20-POLY1305-SHA256:TLS13-AES-128-GCM-SHA256:TLS13-AES-128-CCM-8-SHA256:TLS13-AES-128-CCM-SHA256:EECDH+CHACHA20:EECDH+AES128:RSA+AES128:EECDH+AES256:RSA+AES256:EECDH+3DES:RSA+3DES:!MD5;
    ssl_prefer_server_ciphers     on;
    ssl_session_timeout           10m;
    ssl_session_cache             builtin:1000 shared:SSL:10m;
    ssl_buffer_size               1400;

    #lua
    lua_package_path "/opt/apps/openresty/lualib/?.lua;/opt/apps/openresty/nginx/conf/?.lua;";

    lua_shared_dict prometheus_metrics 10M;
    
    init_by_lua '
      prometheus = require("prometheus").init("prometheus_metrics")
      metric_requests = prometheus:counter(
        "nginx_http_requests_total", "Number of HTTP requests", {"host", "status"})
      metric_latency = prometheus:histogram(
        "nginx_http_request_duration_seconds", "HTTP request latency", {"host"})
      metric_connections = prometheus:gauge(
        "nginx_http_connections", "Number of HTTP connections", {"state"})
    ';
    log_by_lua '
      metric_requests:inc(1, {ngx.var.server_name, ngx.var.status})
      metric_latency:observe(tonumber(ngx.var.request_time), {ngx.var.server_name})
    ';

    server {
      listen 9145;
      location /metrics {
        content_by_lua '
          metric_connections:set(ngx.var.connections_reading, {"reading"})
          metric_connections:set(ngx.var.connections_waiting, {"waiting"})
          metric_connections:set(ngx.var.connections_writing, {"writing"})
          prometheus:collect()
        ';
      }
    }

    server {
        listen       80;
        server_name  localhost;
        root html;
        index index.html index.htm;
        
        #设置nginx状态页面
        location ~ /nginx_status {
            stub_status on;
            access_log off;
            allow 127.0.0.1;
            deny all;
            }

        error_page   500 502 503 504  /50x.html;
        location = /50x.html {
            root   html;
                   }
    }
    include conf.d/*.conf;
}
```



### 2.5、修改启动文件

vim /usr/lib/systemd/system/nginx.service

```
[Unit]
Description=The nginx HTTP and reverse proxy server
After=network.target remote-fs.target nss-lookup.target

[Service]
Type=forking
PIDFile=/run/nginx.pid
ExecStartPost=/bin/sleep 0.1
ExecStartPre=/usr/bin/rm -f /run/nginx.pid
ExecStartPre=/opt/apps/openresty/nginx/sbin/nginx -t
ExecStart=/opt/apps/openresty/nginx/sbin/nginx -c /opt/apps/openresty/nginx/conf/nginx.conf
ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/bin/kill -s QUIT $MAINPID
KillSignal=SIGQUIT
TimeoutStopSec=5
KillMode=process
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```



### 2.6、配置日志分割

vim /etc/logrotate.d/nginx

```
/data/logs/nginx/*.log {
daily
compress
rotate 6
missingok
notifempty
postrotate
if [ -f /run/nginx.pid ]; then
kill -USR1 `cat /run/nginx.pid`
fi
endscript
}
```



## 三、变量说明

| 变量名称                | 变量描述                                     |
| ----------------------- | -------------------------------------------- |
| $server_addr            | 代理服务器的地址                             |
| $server_protocol        | 代理服务器HTTP协议                           |
| $server_port            | 代理服务器端口                               |
| $remote_addr            | 客户端地址                                   |
| $remote_user            | 客户端用户名称                               |
| $remote_port            | 客户端端口                                   |
| $time_local             | 访问时间和时区                               |
| $http_x_forwarded_for   | 获取客户端真实IP                             |
| $request                | 请求的URL和HTTP协议                          |
| $request_uri            | 请求的URL                                    |
| $request_time           | 整个请求的总时间                             |
| $request_method         | 请求的方法（GET、PUT、POST）                 |
| $request_body           | post请求的body数据                           |
| $http_host              | 请求地址，即浏览器中你输入的地址             |
| $status                 | HTTP请求状态码                               |
| $body_bytes_sent        | 发送给客户的文件内容大小                     |
| $http_referer           | 跳转来源                                     |
| $http_user_agent        | 用户终端代理                                 |
| $ssl_protocol           | SSl协议版本                                  |
| $ssl_cipher             | 交换数据中的算法                             |
| $upstream_status        | upstream状态                                 |
| $upstream_addr          | 后端upstream的地址，即真正提供服务的主机地址 |
| $upstream_response_time | 请求过程中，upstream响应时间                 |



## 四、常见错误

| 错误信息                                             | 错误说明                                                     |
| ---------------------------------------------------- | ------------------------------------------------------------ |
| upstream prematurely(过早的) closed connection       | 请求url的时候出现的异常，是由于upstream还未返回应答给用户时，用户断掉连接造成的，对系统没有影响，可以忽略 |
| recv() failed(104: Connection reset by peer)         | 1、服务器的并发连接数超过了其承载量，服务器会将其中一些连接Down掉 <br/>2、客户关掉了浏览器，二服务器还在给客户端发送数据 <br/>3、浏览器端按了stop |
| (111:Connection refused)while connection to upstream | 用户在连接时，若遇到后端upstream挂掉或者不通，会收到该错误   |
|                                                      |                                                              |
|                                                      |                                                              |
|                                                      |                                                              |
|                                                      |                                                              |
|                                                      |                                                              |
|                                                      |                                                              |
|                                                      |                                                              |
|                                                      |                                                              |
|                                                      |                                                              |
|                                                      |                                                              |
|                                                      |                                                              |
|                                                      |                                                              |



## 五、常见状态码

**1xx（临时响应）：**

表示临时响应并需要请求者继续执行操作的状态代码。

| 代码 | 说明                                                         |
| ---- | ------------------------------------------------------------ |
| 100  | （继续） 请求者应当继续提出请求。服务器返回此代码表示已收到请求的第一部分，正在等待其余部分。 |
| 101  | （切换协议） 请求者已要求服务器切换协议，服务器已确认并准备切换。 |

**2xx（成功）：**

表示成功处理了请求的状态代码。

| 状态码 | 说明                                                         |
| :----: | ------------------------------------------------------------ |
|  200   | （成功） 服务器已成功处理了请求。通常，这表示服务器提供了请求的网页。 |
|  201   | （已创建） 请求成功并且服务器创建了新的资源。                |
|  202   | （已接受） 服务器已接受请求，但尚未处理。                    |
|  203   | （非授权信息） 服务器已成功处理了请求，但返回的信息可能来自另一来源。 |
|  204   | （无内容） 服务器成功处理了请求，但没有返回任何内容。        |
|  205   | （重置内容） 服务器成功处理了请求，但没有返回任何内容。      |
|  206   | （部分内容） 服务器成功处理了部分 GET 请求。                 |

**3xx（重定向）：**

表示要完成请求，需要进一步操作。 通常，这些状态代码用来重定向。

| 状态码 | 说明                                                         |
| ------ | ------------------------------------------------------------ |
| 300    | （多种选择） 针对请求，服务器可执行多种操作。服务器可根据请求者 (user agent) 选择一项操作，或提供操作列表供请求者选择。 |
| 301    | （永久移动） 请求的网页已永久移动到新位置。服务器返回此响应（对 GET 或 HEAD 请求的响应）时，会自动将请求者转到新位置。 |
| 302    | （临时移动） 服务器目前从不同位置的网页响应请求，但请求者应继续使用原有位置来进行以后的请求。 |
| 303    | （查看其他位置） 请求者应当对不同的位置使用单独的 GET 请求来检索响应时，服务器返回此代码。 |
| 304    | （未修改） 自从上次请求后，请求的网页未修改过。服务器返回此响应时，不会返回网页内容。 |
| 305    | （使用代理） 请求者只能使用代理访问请求的网页。如果服务器返回此响应，还表示请求者应使用代理。 |
| 307    | （临时重定向） 服务器目前从不同位置的网页响应请求，但请求者应继续使用原有位置来进行以后的请求。 |

**4xx（请求错误）：**

这些状态代码表示请求可能出错，妨碍了服务器的处理。

| 状态码 | 说明                                                         |
| ------ | ------------------------------------------------------------ |
| 400    | （错误请求） 服务器不理解请求的语法。                        |
| 401    | （未授权） 请求要求身份验证。 对于需要登录的网页，服务器可能返回此响应。 |
| 403    | （禁止） 服务器拒绝请求。                                    |
| 404    | （未找到） 服务器找不到请求的网页。                          |
| 405    | （方法禁用） 禁用请求中指定的方法。                          |
| 406    | （不接受） 无法使用请求的内容特性响应请求的网页。            |
| 407    | （需要代理授权） 此状态代码与 401（未授权）类似，但指定请求者应当授权使用代理。 |
| 408    | （请求超时） 服务器等候请求时发生超时。                      |
| 409    | （冲突） 服务器在完成请求时发生冲突。服务器必须在响应中包含有关冲突的信息。 |
| 410    | （已删除） 如果请求的资源已永久删除，服务器就会返回此响应。  |
| 411    | （需要有效长度） 服务器不接受不含有效内容长度标头字段的请求。 |
| 412    | （未满足前提条件） 服务器未满足请求者在请求中设置的其中一个前提条件。 |
| 413    | （请求实体过大） 服务器无法处理请求，因为请求实体过大，超出服务器的处理能力。 |
| 414    | （请求的 URI 过长） 请求的 URI（通常为网址）过长，服务器无法处理。 |
| 415    | （不支持的媒体类型） 请求的格式不受请求页面的支持。          |
| 416    | （请求范围不符合要求） 如果页面无法提供请求的范围，则服务器会返回此状态代码。 |
| 417    | （未满足期望值） 服务器未满足"期望"请求标头字段的要求。      |
|        |                                                              |

**5xx（服务器错误）：**

这些状态代码表示服务器在尝试处理请求时发生内部错误。 这些错误可能是服务器本身的错误，而不是请求出错。

| 状态码 | 说明                                                         |
| ------ | ------------------------------------------------------------ |
| 500    | （服务器内部错误） 服务器遇到错误，无法完成请求。            |
| 501    | （尚未实施） 服务器不具备完成请求的功能。例如，服务器无法识别请求方法时可能会返回此代码。 |
| 502    | （错误网关） 服务器作为网关或代理，从上游服务器收到无效响应。 |
| 503    | （服务不可用） 服务器目前无法使用（由于超载或停机维护）。通常，这只是暂时状态。 |
| 504    | （网关超时） 服务器作为网关或代理，但是没有及时从上游服务器收到请求。 |
| 505    | （HTTP 版本不受支持） 服务器不支持请求中所用的 HTTP 协议版本。 |


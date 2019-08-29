安装kvm

一、安装kvm

1、验证CPU是否支持KVM；如果结果中有vmx（Intel）或svm(AMD)字样，就说明CPU的支持的。

```
egrep '(vmx|svm)' /proc/cpuinfo
```

2、关闭SELinux，将 /etc/sysconfig/selinux 中的 SELinux=enforcing 修改为 SELinux=disabled

3、安装KVM及其依赖项

```
yum -y install qemu-kvm libvirt virt-install bridge-utils
```

4、验证安装结果

```
lsmod | grep kvm
```

5、开启kvm服务，并且设置其开机自动启动

```
systemctl start libvirtd
systemctl enable libvirtd
```

6、查看状态操作结果

```
systemctl status libvirtd
systemctl is-enabled libvirtd
```

7、配置网桥模式

创建br0网卡，内容如下：

```
BOOTPROTO=static
DEVICE=br0
TYPE=Bridge
NM_CONTROLLED=no
IPADDR=10.17.130.236
NETMASK=255.255.255.0
GATEWAY=10.17.130.254
DNS1=10.17.200.1
DNS2=8.8.8.8
```

原网卡配置如下：

```
BOOTPROTO=none
DEVICE=p4p1
NM_CONTROLLED=no
ONBOOT=yes
BRIDGE=br0
```

重启网络服务

```
systemctl restart network
```



二、安装虚拟机

1、准备操作系统安装镜像文件

2、创建虚拟机文件存放的目录

```
mkdir /data/vm
```

3、使用 virt-install 创建虚拟机

```
virt-install -n vm01 --vcpus 2 -r 4096 --disk /data/vm/vm01.img,format=qcow2,size=40 --network bridge=br0 --os-type=linux --os-variant=rhel7 --cdrom /data/iso/CentOS-7-x86_64-Minimal-1810.iso --vnc --vncport=5900 --vnclisten=0.0.0.0
```

不要理会里面提示的错误,继续操作。

4、使用vnc连接该虚拟机进行系统安装

```
查看虚拟机列表
virsh list --all
```



5、使用virt consloe登陆虚拟机

在虚拟机中执行

```
grubby --update-kernel=ALL --args="console=ttyS0"
```

在宿主机上进入虚拟机控制台，想退出时使用 Ctrl 键+ ]  （左方括号）键退出。

```
virsh console vm01
```



三、迁移虚拟机

先关闭虚拟机

```
virsh shutdown vm01
```

创建迁移目录

```
mkdir /data/kvm-img
```

使用 virt-clone 克隆vm01为新的虚拟机

```
virt-clone -o vm01 -n vm02 -f /data/vm/vm02.img
```

开启vm02，修改IP、主机名

```
virsh start vm02
virsh console vm02
修改完成后重启虚拟机
```

将虚拟机镜像迁移到其他服务器上

在新的kvm服务器上操作：

将迁移过来的vm02镜像放到/data/kvm-img目录，将vm02.xml放到/etc/libvirt/qemu目录中，并修改名称为vm03

编辑vm03.xml，将里面所有vm02替换为vm03，修改vnc端口，然后把UUID换为新的(直接使用[这个](https://www.guidgen.com/)在线工具生成吧)

定义新虚拟机

```
virsh define /etc/libvirt/qemu/vm03.xml
```

指定新的IP和主机名即可



四、对虚拟机进行快照管理

1、为vm02创建虚拟机快照

```
virsh snapshot-create-as vm02 vm02snap1
```

2、查看虚拟机镜像快照版本

```
virsh snapshot-list vm02
```

3、查看当前虚拟机镜像快照版本

```
virsh snapshot-current vm02
```

**快照配置文件在/var/lib/libvirt/qemu/snapshot/虚拟机名称/下**

4、恢复虚拟机快照

关闭虚拟机

```
virsh shutdown vm02
virsh domstate vm02 #查看虚拟机状态
```

执行恢复，并确认恢复版本

```
virsh snapshot-current vm02
virsh snapshot-revert vm02 137857777
virsh snapshot-list vm02
virsh snapshot-revert vm02 vm01snap1
```



5、删除虚拟机快照

查看虚拟机快照

```
qemu-img info vm02.qcow2
```

删除快照

```
virsh snapshot-delete vm02 137857777
```











常用操作命令：

查看vm02的xml文件
```
virsh dumpxml vm02
```

编辑虚拟机配置文件

```
virsh shutdown vm02
virsh edit vm02 （更改前要将vm02 shutdown）
virsh reboot vm02
从配置文件启动虚拟机
virsh create /etc/libvirt/qemu/vm02.xml 
```
删除虚拟机
```
virsh destroy vm01 强制关闭虚拟机
virsh undefine vm01 删除虚拟机
```


##创建k8s使用pvc

###在 Ceph 集群操作

1. 创建存储持

   ```
   ceph osd pool create data 128
   ```

2. 新增认证用户 kube

   ```
   ceph auth get-or-create client.kube mon 'allow r' osd 'allow rwx pool=data'
   ```

3. 查看用户 key

   ```
   ceph auth get-key client.admin
   ceph auth get-key client.kube
   ```

###在 k8s 上操作

1、创建 secrets

\# admin key
kubectl create secret generic ceph-secret --type="[kubernetes.io/rbd](http://kubernetes.io/rbd)" --from-literal=key="" --namespace=kube-system

\# kube key
kubectl create secret generic ceph-secret-kube --type="[kubernetes.io/rbd](http://kubernetes.io/rbd)" --from-literal=key="" --namespace=kube-system
kubectl create secret generic ceph-secret-kube --type="[kubernetes.io/rbd](http://kubernetes.io/rbd)" --from-literal=key="" --namespace=db
kubectl create secret generic ceph-secret-kube --type="[kubernetes.io/rbd](http://kubernetes.io/rbd)" --from-literal=key="" --namespace=default



文件系统测试

测试命令:

- ```
  使用dd命令，写512字节，写1万次
  ```

  - ```
    dd if=/dev/zero of=512 bs=512 count=10000 oflag=direct
    ```

- ```
  使用dd命令，写 4k，写1万次
  ```

  - ```
    dd if=/dev/zero of=4k bs=4k count=10000 oflag=direct
    ```

- ```
  使用dd命令，写 1M，写1024次
  ```

  - ```
    dd if=/dev/zero of=1m bs=1M count=1024 oflag=direct
    ```
# ES常用命令

查看_cat所有支持的参数

```
cat '127.0.0.1:9200/_cat'
```

查询集群健康状态

```
curl 'http://127.0.0.1:9200/_cat/health?pretty'
curl 'http://127.0.0.1:9200/_cluster/health?pretty'
curl 'http://127.0.0.1:9200/_cluster/health?level=indices&pretty'
curl 'http://127.0.0.1:9200/_cluster/health?level=shard&pretty'
curl 'http://127.0.0.1:9200/_cluster/health?wait_for_status=green&pretty'
curl 'http://127.0.0.1:9200/_cluster/state?pretty'
curl 'http://127.0.0.1:9200/_cluster/settings?pretty'
curl 'http://127.0.0.1:9200/_cluster/pending_tasks?pretty'
```

查询集群所有节点

```
curl 'http://127.0.0.1:9200/_cat/nodes?pretty'
```

查询所有索引

```
curl 'http://127.0.0.1:9200/_cat/indices?pretty'
```

查询分片

```
curl 'http://127.0.0.1:9200/_cat/shards?pretty'
```

查看索引占用内存情况

```
curl 'http://127.0.0.1:9200/_cat/segments?pretty'
curl 'http://127.0.0.1:9200/_cat/segments/INDEX?v&h=si,sm'
```

查询相关内存

```
curl 'http://127.0.0.1:9200/_cat/nodes?v&h=id,ip,port,r,ramPercent,ramCurrent,heapMax,heapCurrent,fielddataMemory,queryCacheMemory,requestCacheMemory,segmentsMemory'
```

```
curl 'http://127.0.0.1:9200/_cat/nodes?v&h=segments.count,segments.memory,segments.index_writer_memory,segments.version_map_memory,segments.fixed_bitset_memory'
```

⚠️：

fielddata.memory_size(fm)：字段缓存占用内存

filter_cache.memory_size(fcm)：过滤语句缓存占用内存

segments.memory(sm)：每个分片包含的断占用内存

查看节点状态

```
curl 'http://127.0.0.1:9200/_nodes/stats/indices/query_cache,request_cache,fielddata?pretty&human'
```

查看节点limit内存相关

```
curl 'http://127.0.0.1:9200/_nodes/stats/breaker?pretty'
```

```
curl 'http://127.0.0.1:9200/_stats/fielddata?pretty'
```

查看磁盘空间容量

```
curl 'http://127.0.0.1:9200/_cat/allocation?v'
```

修改索引配置

```
curl -XPUT "http://127.0.0.1:9200/k8s-mobile-2019.08.01-000001/_settings" -H 'Content-Type: application/json' -d'
{
   "index.lifecycle.rollover_alias": "k8s-mobile"
}'
```

创建索引模版

```
curl -XPUT "http://127.0.0.1:9200/_template/k8s-index" -H 'Content-Type: application/json' -d'
{
    "order" : 1000,
    "index_patterns" : [
      "k8s-index-*"
    ],
    "settings" : {
      "index" : {
        "lifecycle" : {
          "name" : "ilm-k8s",
          "rollover_alias" : "k8s-index"
        },
        "routing" : {
          "allocation" : {
            "require" : {
              "box_type" : "hot"
            }
          }
        },
        "refresh_interval" : "30s",
        "number_of_shards" : "3",
        "number_of_replicas" : "1"
      }
    },
    "mappings" : { },
    "aliases" : { }
}'
```

创建索引

```
curl -XPUT 'http://127.0.0.1:9200/k8s-test'
```

创建ilm索引

```
curl -XPUT "http://127.0.0.1:9200/<k8s-index-%7Bnow%2Fd%7D-000001>" -H 'Content-Type: application/json' -d'
{
  "aliases": {
    "k8s-index": {
      "is_write_index": true
    }
  }
}'
```

添加ilm别名

```
curl -XPOST "http://192.168.30.14:9200/_aliases" -H 'Content-Type: application/json' -d'
{
	"actions": [{
		"add": {
			"index": "k8s-ingress-2019.08.12-000001",
			"alias": "k8s-ingress",
			"is_write_index": true
		}
	}]
}'
```



向索引中插入一个ID为1的文档

```
curl -H "Content-Type:application/json" -XPUT 127.0.0.1:9200/test-k8s/people/1? -d '{
    "name": "tim"
}'
```

在没有ID的情况下向索引中插入文档，ES会随机生成一个ID

```
curl -H "Content-Type:application/json" -XPOST 127.0.0.1:9200/k8s-kube/_doc? -d '{"name": "tim"}'
```

根据ID查询文档

```
curl -XGET '127.0.0.1:9200/k8s-test/people/1?'
```

更新ID为1的文档，将name字段的值改为daocloud

```
curl -XPOST "127.0.0.1:9200/k8s-test/people/1/_update?
{
  "doc": { "name": "jack" }
}"
```









清理缓存

```
curl -XPOST 'http://127.0.0.1:9200/*/_cache/clear'
curl -XPOST 'http://127.0.0.1:9200/*/_optimize'
```


#!/bin/bash
# Ubuntu VM 上启动 Spark 推荐网关（Windows 刷新推荐时会调用）
cd "$(dirname "$0")"
export SPARK_HOME="${SPARK_HOME:-/opt/bigdata/spark}"
export PATH="$SPARK_HOME/bin:$PATH"
echo "Spark VM gateway -> http://0.0.0.0:5001"
exec python3 vm_recommend_server.py

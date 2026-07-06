#!/bin/bash
# 增量 Spark 推荐：历史评分用预计算缓存，仅重算网站用户推荐（刷新时调用）
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SPARK_HOME="${SPARK_HOME:-/opt/bigdata/spark}"
SPARK_SUBMIT="$SPARK_HOME/bin/spark-submit"

export SPARK_LOCAL_IP="${SPARK_LOCAL_IP:-127.0.0.1}"
WEB_USER_OFFSET="${WEB_USER_OFFSET:-1000000}"
TARGET_USER_ID="${TARGET_USER_ID:-}"

CONF_DIR="$(cd "$(dirname "$0")/conf" 2>/dev/null && pwd || true)"
if [ -n "$CONF_DIR" ] && [ -f "$CONF_DIR/core-site.xml" ]; then
  export HADOOP_CONF_DIR="$CONF_DIR"
else
  unset HADOOP_CONF_DIR
fi

to_file_url() {
  local p="$1"
  if [[ "$p" == file://* ]]; then echo "$p"
  elif [[ "$p" == /* ]]; then echo "file://$p"
  else echo "file://$(cd "$(dirname "$p")" && pwd)/$(basename "$p")"
  fi
}

RATINGS_HISTORY="$ROOT/spark/data/ratings_history.ndjson"
RATINGS_WEB="$ROOT/spark/data/ratings_web.ndjson"
MOVIES_CATALOG="$ROOT/spark/data/movies_catalog.ndjson"
OUTPUT_DIR="$ROOT/spark/output"
CONTENT_INDEX="$OUTPUT_DIR/content_similarity_index.ndjson"
GRAPHX_CACHE="$OUTPUT_DIR/graphx_history_cache.ndjson"
mkdir -p "$OUTPUT_DIR" "$(dirname "$RATINGS_HISTORY")"

echo "===== 增量推荐环境检查 ====="
if [ ! -f "$RATINGS_HISTORY" ]; then
  echo "错误: 缺少历史评分 $RATINGS_HISTORY"
  echo "请先从 Windows 同步 ratings_history.ndjson"
  exit 1
fi
if [ ! -f "$RATINGS_WEB" ]; then
  echo "错误: 缺少网站评分 $RATINGS_WEB"
  exit 1
fi
if [ ! -f "$MOVIES_CATALOG" ]; then
  echo "错误: 缺少 $MOVIES_CATALOG"
  exit 1
fi

HIST_LINES=$(wc -l < "$RATINGS_HISTORY" | tr -d ' ')
WEB_LINES=$(wc -l < "$RATINGS_WEB" | tr -d ' ')
echo "历史评分: $HIST_LINES 行 | 网站评分: $WEB_LINES 行"

JAR="$ROOT/spark/target/movie-recommend-spark-1.0.0.jar"
if [ ! -f "$JAR" ] || [ "${RECOMPILE:-0}" = "1" ]; then
  echo "===== 编译 Spark 项目 ====="
  cd "$ROOT/spark"
  mvn clean package -Dmaven.test.skip=true
fi

SPARK_OPTS="--driver-memory 2g --executor-memory 2g --conf spark.driver.host=127.0.0.1 --conf spark.hadoop.fs.defaultFS=file:/// --conf spark.sql.warehouse.dir=file:///tmp/spark-warehouse"
export SPARK_ALS_MAX_ITER="${SPARK_ALS_MAX_ITER:-5}"

HISTORY_URL="$(to_file_url "$RATINGS_HISTORY")"
WEB_URL="$(to_file_url "$RATINGS_WEB")"
MOVIES_URL="$(to_file_url "$MOVIES_CATALOG")"
INDEX_URL="$(to_file_url "$CONTENT_INDEX")"
CACHE_URL="$(to_file_url "$GRAPHX_CACHE")"
OUTPUT_URL="$(to_file_url "$OUTPUT_DIR")"

# 预计算缓存（历史评分不变时只需构建一次）
if [ ! -f "$CONTENT_INDEX" ] || [ ! -f "$GRAPHX_CACHE" ]; then
  echo ""
  echo "===== 首次构建 Content 索引与 GraphX 缓存 ====="
  if ! "$SPARK_SUBMIT" $SPARK_OPTS --class edu.xt1.spark.MovieBuildSparkCaches "$JAR" \
      "$MOVIES_URL" "$HISTORY_URL" "$INDEX_URL" "$CACHE_URL"; then
    echo "缓存构建失败"
    exit 1
  fi
fi

echo ""
echo "===== 增量推荐（仅网站用户） ====="
INCREMENTAL_ARGS=(
  "$HISTORY_URL"
  "$WEB_URL"
  "$OUTPUT_URL"
  "$WEB_USER_OFFSET"
  "$INDEX_URL"
  "$CACHE_URL"
)
if [ -n "$TARGET_USER_ID" ]; then
  INCREMENTAL_ARGS+=("$TARGET_USER_ID")
fi

if ! "$SPARK_SUBMIT" $SPARK_OPTS --class edu.xt1.spark.MovieRecommendIncremental "$JAR" \
    "${INCREMENTAL_ARGS[@]}"; then
  echo "增量推荐失败"
  exit 1
fi

echo ""
echo "===== 增量推荐完成 ====="
ls -lh "$OUTPUT_DIR"/recommendations_*.json 2>/dev/null || true

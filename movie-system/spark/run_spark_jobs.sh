#!/bin/bash
# Spark 推荐任务运行脚本（Ubuntu 18.04 + Spark 3.3.4）
# 现场演示用在线版即可；本脚本用于答辩展示 Spark 离线批处理。

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CS1_ROOT="$(cd "$ROOT/../.." && pwd)"
SPARK_HOME="${SPARK_HOME:-/opt/bigdata/spark}"
SPARK_SUBMIT="$SPARK_HOME/bin/spark-submit"
FILMS_DATA="${FILMS_DATA:-$CS1_ROOT/films_data}"
DOUBAN_DATA="$FILMS_DATA/cleaned_data/douban"

export SPARK_LOCAL_IP="${SPARK_LOCAL_IP:-127.0.0.1}"

CONF_DIR="$(cd "$(dirname "$0")/conf" 2>/dev/null && pwd || true)"
if [ -n "$CONF_DIR" ] && [ -f "$CONF_DIR/core-site.xml" ]; then
  export HADOOP_CONF_DIR="$CONF_DIR"
else
  unset HADOOP_CONF_DIR
  echo "提示: 未找到 spark/conf/core-site.xml，将仅用 Spark 本地 file:// 配置"
fi

to_file_url() {
  local p="$1"
  if [[ "$p" == file://* ]]; then
    echo "$p"
  elif [[ "$p" == /* ]]; then
    echo "file://$p"
  else
    echo "file://$(cd "$(dirname "$p")" && pwd)/$(basename "$p")"
  fi
}

echo "===== 环境检查 ====="
echo "SPARK_HOME=$SPARK_HOME"
echo "FILMS_DATA=$FILMS_DATA"
java -version
mvn -v | head -1
"$SPARK_SUBMIT" --version 2>&1 | grep "version" | head -1

RATINGS="$ROOT/spark/data/ratings.json"
OUTPUT_DIR="$ROOT/spark/output"
mkdir -p "$OUTPUT_DIR" "$(dirname "$RATINGS")"

echo ""
echo "===== 准备评分数据 ====="
if [ -f "$RATINGS" ]; then
    RATING_LINES=$(wc -l < "$RATINGS" | tr -d ' ')
    RATING_BYTES=$(stat -c%s "$RATINGS" 2>/dev/null || stat -f%z "$RATINGS")
    FIRST_CHAR=$(head -c 1 "$RATINGS")
    echo "使用已有 ratings.json: $RATINGS (${RATING_LINES} 行, ${RATING_BYTES} 字节)"
    if [ "$FIRST_CHAR" = "[" ] || [ "$RATING_LINES" -lt 100 ]; then
        echo "错误: ratings.json 仍是旧版 JSON 数组或行数过少，Spark 只会读到 1 条评分。"
        echo "请从 Windows 复制 NDJSON 版本（约 4700+ 行，首字符为 {）："
        echo "  movie-system/movie-system/spark/data/ratings.json"
        exit 1
    fi
elif [ -f "$ROOT/scripts/export_spark_ratings.py" ] && command -v python3 &>/dev/null; then
    cd "$ROOT"
    python3 scripts/export_spark_ratings.py
else
    echo "错误: 找不到 $RATINGS"
    echo "请从 Windows 运行 export 后复制 spark/data/ratings.json 到虚拟机。"
    exit 1
fi

if [ ! -d "$DOUBAN_DATA" ]; then
    echo "警告: 找不到豆瓣电影数据 ($DOUBAN_DATA)"
    echo "内容推荐将失败。请确保 cs1/films_data/cleaned_data/douban 已同步到 VM。"
elif ! ls "$DOUBAN_DATA"/*/part-*.csv >/dev/null 2>&1; then
    echo "警告: $DOUBAN_DATA 下无 */part-*.csv，TF-IDF 将失败。"
    echo "请同步整个 films_data/cleaned_data/douban/ 目录。"
fi

JAR="$ROOT/spark/target/movie-recommend-spark-1.0.0.jar"
if [ ! -f "$JAR" ] || [ "${RECOMPILE:-0}" = "1" ]; then
    echo ""
    echo "===== 编译 Spark 项目 (Spark 3.3.4 / Scala 2.12) ====="
    echo "首次编译需下载依赖，可能需要 5-20 分钟..."
    cd "$ROOT/spark"
    mvn clean package -Dmaven.test.skip=true
else
    echo ""
    echo "===== 跳过编译，使用已有 JAR: $JAR ====="
    echo "如需重新编译: RECOMPILE=1 bash run_spark_jobs.sh"
fi

SPARK_OPTS="--driver-memory 2g --executor-memory 2g --conf spark.driver.host=127.0.0.1 --conf spark.hadoop.fs.defaultFS=file:/// --conf spark.sql.warehouse.dir=file:///tmp/spark-warehouse"

RATINGS_URL="$(to_file_url "$RATINGS")"
FILMS_DATA_URL="$(to_file_url "$FILMS_DATA")"

run_job() {
    local name="$1"
    shift
    echo ""
    echo "===== $name ====="
    if "$SPARK_SUBMIT" $SPARK_OPTS "$@"; then
        echo "OK: $name"
        return 0
    else
        echo "FAILED: $name (后续任务继续)"
        return 1
    fi
}

FAIL=0

run_job "1/3 ALS 协同过滤 (MLlib)" \
    --class edu.xt1.spark.MovieRecommendALS "$JAR" \
    "$RATINGS_URL" "$OUTPUT_DIR/recommendations_als.json" || FAIL=1

run_job "2/3 GraphX 图协同推荐" \
    --class edu.xt1.spark.MovieRecommendGraphX "$JAR" \
    "$RATINGS_URL" "$OUTPUT_DIR/recommendations_graphx.json" 8 || FAIL=1

run_job "3/3 TF-IDF 内容推荐" \
    --driver-memory 3g --class edu.xt1.spark.MovieRecommendContentBased "$JAR" \
    "$FILMS_DATA_URL" "$RATINGS_URL" "$OUTPUT_DIR/recommendations_content.json" || FAIL=1

echo ""
echo "===== 运行结果 ====="
ls -lh "$OUTPUT_DIR"/*.json 2>/dev/null || echo "无输出文件"
echo ""
echo "输出目录: $OUTPUT_DIR"
echo "  recommendations_als.json      (权重 0.7)"
echo "  recommendations_graphx.json   (权重 0.2)"
echo "  recommendations_content.json  (权重 0.1)"
echo ""
if [ "$FAIL" -ne 0 ]; then
    echo "部分任务失败，请查看上方日志。"
    exit 1
fi
echo "全部完成。现场演示用 Windows 在线版即可，Spark 结果用于答辩展示离线 pipeline。"

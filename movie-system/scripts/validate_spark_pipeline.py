#!/usr/bin/env python3
"""校验 Spark 离线 pipeline：输入 ratings.json + 输出三份 JSON 是否合格。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SPARK_DATA = BASE / "spark" / "data" / "ratings.json"
SPARK_OUTPUT = BASE / "spark" / "output"
WEB_USER_OFFSET = 1_000_000

OUTPUT_FILES = {
    "als": "recommendations_als.json",
    "graphx": "recommendations_graphx.json",
    "content": "recommendations_content.json",
}


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_ratings(path: Path) -> list:
    """支持 NDJSON（每行一条）或 JSON 数组，与 Spark 读取格式一致。"""
    with path.open("r", encoding="utf-8") as f:
        text = f.read().strip()
    if not text:
        return []
    if text.startswith("["):
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError(f"{path.name} 应为 JSON 数组")
        return data
    items: list = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path.name} 第 {line_no} 行 NDJSON 解析失败: {exc}") from exc
    return items


def check_ratings_input() -> list[str]:
    errors: list[str] = []
    if not SPARK_DATA.exists():
        return [f"缺少输入: {SPARK_DATA}"]
    try:
        data = _load_ratings(SPARK_DATA)
    except ValueError as exc:
        return [str(exc)]
    if len(data) == 0:
        errors.append("ratings.json 为空")
        return errors
    sample = data[0]
    for key in ("userId", "movieId", "rating"):
        if key not in sample:
            errors.append(f"ratings.json 缺少字段: {key}")
    web = sum(1 for r in data if int(r.get("userId", 0)) >= WEB_USER_OFFSET)
    print(f"[输入] ratings.json: {len(data)} 条, Web用户评分 {web} 条")
    return errors


def check_output_file(algo: str, filename: str) -> list[str]:
    errors: list[str] = []
    path = SPARK_OUTPUT / filename
    if not path.exists():
        return [f"缺少输出: {path.name}"]
    payload = _load_json(path)
    items = payload.get("items", [])
    if not items:
        errors.append(f"{filename}: items 为空")
        return errors
    web_items = [x for x in items if int(x.get("userId", 0)) >= WEB_USER_OFFSET]
    users = {int(x["userId"]) for x in items}
    web_users = {u for u in users if u >= WEB_USER_OFFSET}
    for key in ("userId", "movieId", "score"):
        if key not in items[0]:
            errors.append(f"{filename}: 缺少字段 {key}")
            break
    print(
        f"[输出] {filename}: {len(items)} 条, "
        f"{len(users)} 用户, Web用户 {len(web_users)} 个, Web条目 {len(web_items)} 条"
    )
    if algo == "als" and len(items) < 100:
        errors.append(f"{filename}: ALS 条目过少 ({len(items)})，可能 Spark ALS 任务异常")
    if len(web_items) == 0:
        errors.append(f"{filename}: 无 Web 用户 (userId>={WEB_USER_OFFSET}) 推荐，导入后网站用户看不到")
    return errors


def check_mysql_movie_ids() -> list[str]:
    errors: list[str] = []
    try:
        sys.path.insert(0, str(BASE / "backend"))
        from app import create_app
        from services.movie_service import get_movie_by_id

        app = create_app()
        with app.app_context():
            for filename in OUTPUT_FILES.values():
                path = SPARK_OUTPUT / filename
                if not path.exists():
                    continue
                items = _load_json(path).get("items", [])[:50]
                missing = 0
                for item in items:
                    mid = int(item["movieId"])
                    if not get_movie_by_id(mid):
                        missing += 1
                if missing > len(items) * 0.2:
                    errors.append(f"{filename}: 抽样 {len(items)} 条中有 {missing} 条 movieId 不在 MySQL")
    except Exception as exc:
        print(f"[警告] 无法连接 MySQL 校验 movieId: {exc}")
    return errors


def main() -> int:
    print("===== Spark Pipeline 校验 =====")
    print(f"项目目录: {BASE}")
    all_errors: list[str] = []
    all_errors.extend(check_ratings_input())
    for algo, fname in OUTPUT_FILES.items():
        all_errors.extend(check_output_file(algo, fname))
    all_errors.extend(check_mysql_movie_ids())

    print()
    if all_errors:
        print("[FAIL] 发现问题:")
        for e in all_errors:
            print(f"  - {e}")
        print()
        print("VM 修复步骤:")
        print("  1. 确保 cs1/films_data 已同步到虚拟机")
        print("  2. 从 Windows 复制 spark/data/ratings.json（或运行 export_spark_ratings.py）")
        print("  3. cd movie-system2/movie-system2/spark && RECOMPILE=1 bash run_spark_jobs.sh")
        print("  4. 将 spark/output/*.json 拷回 Windows 同路径")
        print("  5. 再运行本脚本验证")
        return 1

    print("[OK] Spark 输入/输出校验通过，可拷回 Windows 使用。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

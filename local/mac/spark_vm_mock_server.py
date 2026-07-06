#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mac 本地 Mock Ubuntu VM Spark 推荐网关。
接口与 spark/vm_recommend_server.py 100% 兼容：
- GET  /health
- POST /sync/ratings          保存 spark/data/ratings.json
- POST /sync/movies           保存 spark/data/movies_catalog.ndjson
- POST /spark/recompute       后台用纯 Python 生成 ALS/GraphX/Content 三份推荐 JSON（替代 Spark）
- GET  /spark/status          任务状态
- GET  /output/<name>         下载三份 JSON

启动（Mac 专属，Windows 组员继续用真 Ubuntu VM）：
  export SPARK_VM_HOST=127.0.0.1
  export SPARK_VM_PORT=5001
  python3 local/mac/spark_vm_mock_server.py
"""
from __future__ import annotations

import json
import math
import os
import threading
import time
from collections import Counter, defaultdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn
from urllib.parse import unquote

try:
    from http.server import ThreadingHTTPServer
except ImportError:  # pragma: no cover - py<3.7
    class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
        daemon_threads = True


# ---------------------------------------------------------------------------
# 基础路径（和 vm_recommend_server.py 对齐）
# ---------------------------------------------------------------------------
HOST = os.environ.get("SPARK_VM_HOST", "127.0.0.1")
PORT = int(os.environ.get("SPARK_VM_PORT", "5001"))

SCRIPT_DIR = Path(__file__).resolve().parent            # local/mac/
PROJECT_ROOT = SCRIPT_DIR.parent.parent / "movie-system"  # GitHub/movie-system
SPARK_DIR = PROJECT_ROOT / "spark"
SPARK_DATA_DIR = SPARK_DIR / "data"
SPARK_OUTPUT_DIR = SPARK_DIR / "output"
LOG_FILE = Path(os.environ.get("SPARK_VM_LOG", "/tmp/spark_mock_recommend_job.log"))

SPARK_USER_OFFSET = 1000000
TOP_N_PER_USER = 40


def _to_real_uid(raw_uid: int) -> int:
    """将 Spark 导出的 userId（Web 用户已 +1e6 偏移）还原为真实用户 id。"""
    if raw_uid >= SPARK_USER_OFFSET:
        return raw_uid - SPARK_USER_OFFSET
    return raw_uid

_job_lock = threading.Lock()
_job_state: dict = {
    "running": False,
    "started_at": None,
    "finished_at": None,
    "exit_code": None,
    "error": None,
}


# ---------------------------------------------------------------------------
# HTTP 小工具
# ---------------------------------------------------------------------------
def _json_response(handler: BaseHTTPRequestHandler, code: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_body(handler: BaseHTTPRequestHandler) -> bytes:
    length = int(handler.headers.get("Content-Length", 0))
    return handler.rfile.read(length) if length > 0 else b""


def _tail_log(max_lines: int = 30) -> str:
    if not LOG_FILE.exists():
        return ""
    text = LOG_FILE.read_text(encoding="utf-8", errors="replace")
    return "\n".join(text.splitlines()[-max_lines:])


# ========================================================================
# 纯 Python 推荐算法（替代 Spark Scala jar）
# 目标：给每个用户生成 3 份 TopN 推荐列表，格式和 Spark 输出完全一致
# ========================================================================
def _load_ratings_ndjson(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _load_movies_ndjson(path: Path) -> dict[str, dict]:
    movies: dict[str, dict] = {}
    if not path.exists():
        return movies
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            mid = str(obj.get("movieId") or obj.get("movie_id") or obj.get("id") or "")
            if mid:
                movies[mid] = obj
    return movies


def _split_genres(raw: str | None) -> list[str]:
    if not raw:
        return []
    text = str(raw).replace(" ", "").replace("、", "/").replace(",", "/")
    return [g for g in text.split("/") if g]


def _log(log_fh, msg: str) -> None:
    line = "[%s] %s\n" % (time.strftime("%H:%M:%S"), msg)
    log_fh.write(line)
    log_fh.flush()
    print(line.rstrip())


# --------- 算法 A：近似 ALS（基于用户评分偏好的类型/高分/人气加权） ---------
def _recommend_als(
    user_rows: list[dict],
    all_rated_by_user: dict[int, set[str]],
    movies: dict[str, dict],
) -> dict[int, list[tuple[str, float]]]:
    """用户自己高分的类型/年份/评分人加权，替代 Spark MLlib ALS。"""
    recs: dict[int, list[tuple[str, float]]] = {}

    all_rating_avg: dict[str, tuple[float, int]] = {}
    global_ratings: dict[str, list[float]] = defaultdict(list)
    for row in user_rows:
        mid = str(row.get("movieId") or row.get("movie_id") or "")
        score = float(row.get("score") or row.get("rating") or 0)
        if mid:
            global_ratings[mid].append(score)
    for mid, scores in global_ratings.items():
        all_rating_avg[mid] = (sum(scores) / len(scores), len(scores))

    for uid, rated_set in all_rated_by_user.items():
        pref = Counter()
        year_pref = Counter()
        my_ratings: list[tuple[str, float]] = []
        for row in user_rows:
            r_uid_raw = int(row.get("userId") or row.get("user_id") or 0)
            r_uid = _to_real_uid(r_uid_raw)
            if r_uid != uid:
                continue
            mid = str(row.get("movieId") or row.get("movie_id") or "")
            s = float(row.get("score") or row.get("rating") or 0)
            my_ratings.append((mid, s))
            m = movies.get(mid, {})
            w = max(1.0, s - 5.0)
            for g in _split_genres(m.get("genres")):
                pref[g] += w
            yr = str(m.get("year") or "")
            if yr.isdigit():
                year_pref[int(yr)] += w

        if not pref and not my_ratings:
            recs[uid] = []
            continue

        max_pref = max(pref.values()) if pref else 1.0
        candidate_scores: dict[str, float] = {}
        rated_num = len(rated_set) or 1
        for mid, m in movies.items():
            if mid in rated_set or not mid:
                continue
            rating_avg, rating_cnt = all_rating_avg.get(mid, (0.0, 0))
            genre_match = 0.0
            for g in _split_genres(m.get("genres")):
                genre_match += pref.get(g, 0)
            if max_pref > 0:
                genre_match = genre_match / max_pref * 6.0
            rating_score = rating_avg if rating_avg else 6.0
            popularity = min(3.0, math.log10(max(1, rating_cnt) + 1) * 1.3)
            yr = str(m.get("year") or "")
            year_bonus = 0.0
            if yr.isdigit() and year_pref:
                year_bonus = year_pref.get(int(yr), 0) * 0.05
            score = genre_match + rating_score * 0.4 + popularity + year_bonus
            score = min(9.9, max(0.0, score + (rated_num - 1) * 0.02))
            candidate_scores[mid] = score

        ranked = sorted(candidate_scores.items(), key=lambda kv: -kv[1])[:TOP_N_PER_USER]
        recs[uid] = ranked
    return recs


# --------- 算法 B：近似 GraphX（用户-用户相似性扩展） ---------
def _recommend_graphx(
    user_rows: list[dict],
    all_rated_by_user: dict[int, set[str]],
    movies: dict[str, dict],
) -> dict[int, list[tuple[str, float]]]:
    """Jaccard 重叠相似度找相似用户，相似用户高分的我没看过的推荐。"""
    recs: dict[int, list[tuple[str, float]]] = {}
    ratings_by_user: dict[int, dict[str, float]] = defaultdict(dict)
    for row in user_rows:
        uid_raw = int(row.get("userId") or row.get("user_id") or 0)
        uid = _to_real_uid(uid_raw)
        mid = str(row.get("movieId") or row.get("movie_id") or "")
        s = float(row.get("score") or row.get("rating") or 0)
        if uid and mid:
            ratings_by_user[uid][mid] = s

    user_ids = list(all_rated_by_user.keys())
    for uid in user_ids:
        mine = ratings_by_user.get(uid, {})
        mine_set = set(mine)
        if not mine_set:
            recs[uid] = []
            continue
        sim_scores: list[tuple[int, float]] = []
        for other_uid, other_map in ratings_by_user.items():
            if other_uid == uid or not other_map:
                continue
            other_set = set(other_map)
            inter = len(mine_set & other_set)
            if inter < 1:
                continue
            union = len(mine_set | other_set)
            jaccard = inter / union if union else 0
            sim_scores.append((other_uid, jaccard))
        sim_scores.sort(key=lambda kv: -kv[1])
        sim_scores = sim_scores[:20]

        candidate: dict[str, float] = defaultdict(float)
        for other_uid, sim in sim_scores:
            other_map = ratings_by_user[other_uid]
            for mid, s in other_map.items():
                if mid in mine_set or mid not in movies:
                    continue
                weight = sim * max(0.0, (s - 5.0))
                candidate[mid] += weight
        ranked = sorted(candidate.items(), key=lambda kv: -kv[1])[:TOP_N_PER_USER]
        if not ranked:
            fallback = _fallback_popular(movies, mine_set)
            recs[uid] = fallback
            continue
        max_v = max(1e-6, ranked[0][1])
        scaled = [(mid, 5.0 + (v / max_v) * 4.5) for mid, v in ranked]
        recs[uid] = scaled
    return recs


# --------- 算法 C：近似 TF-IDF 内容推荐 ---------
def _recommend_content(
    user_rows: list[dict],
    all_rated_by_user: dict[int, set[str]],
    movies: dict[str, dict],
) -> dict[int, list[tuple[str, float]]]:
    """基于类型/导演/演员关键词匹配的内容相似度。"""
    recs: dict[int, list[tuple[str, float]]] = {}

    def _tokens(m: dict) -> list[str]:
        tokens: list[str] = []
        for g in _split_genres(m.get("genres")):
            tokens.append("G:" + g)
        for director in str(m.get("director") or "").split("/"):
            d = director.strip()
            if d:
                tokens.append("D:" + d)
        for actor in str(m.get("actors") or m.get("casts") or "").split("/"):
            a = actor.strip()
            if a:
                tokens.append("A:" + a)
        yr = str(m.get("year") or "")
        if yr.isdigit():
            tokens.append("Y:" + yr)
        return tokens

    idf: dict[str, float] = defaultdict(float)
    movie_tokens: dict[str, list[str]] = {}
    total = max(1, len(movies))
    for mid, m in movies.items():
        ts = list(dict.fromkeys(_tokens(m)))
        movie_tokens[mid] = ts
        for t in ts:
            idf[t] += 1
    for t in list(idf):
        idf[t] = math.log(total / (1 + idf[t])) + 1

    for uid, rated_set in all_rated_by_user.items():
        my_rows = [r for r in user_rows
                   if _to_real_uid(int(r.get("userId") or r.get("user_id") or 0)) == uid]
        if not my_rows:
            recs[uid] = []
            continue
        profile: dict[str, float] = defaultdict(float)
        for r in my_rows:
            mid = str(r.get("movieId") or r.get("movie_id") or "")
            s = float(r.get("score") or r.get("rating") or 0)
            w = max(0.3, s / 7.0)
            for tok in movie_tokens.get(mid, []):
                profile[tok] += idf.get(tok, 0.5) * w
        if not profile:
            recs[uid] = _fallback_popular(movies, rated_set)
            continue
        prof_norm = math.sqrt(sum(v * v for v in profile.values())) or 1.0

        scored: dict[str, float] = {}
        for mid, toks in movie_tokens.items():
            if mid in rated_set or not toks:
                continue
            m_vec: dict[str, float] = defaultdict(float)
            for t in toks:
                m_vec[t] += idf.get(t, 0.5)
            dot = sum(profile[t] * m_vec[t] for t in m_vec)
            m_norm = math.sqrt(sum(v * v for v in m_vec.values())) or 1.0
            cosine = dot / (prof_norm * m_norm)
            rated_bonus = min(2.0, math.log10(len(toks) + 1))
            scored[mid] = cosine * 10.0 + rated_bonus
        ranked = sorted(scored.items(), key=lambda kv: -kv[1])[:TOP_N_PER_USER]
        if not ranked:
            recs[uid] = _fallback_popular(movies, rated_set)
        else:
            recs[uid] = ranked
    return recs


def _fallback_popular(movies: dict[str, dict], exclude: set[str]) -> list[tuple[str, float]]:
    items = []
    for mid, m in movies.items():
        if mid in exclude:
            continue
        rating = float(m.get("rating") or 0)
        votes = int(m.get("vote_count") or m.get("ratings_count") or 0)
        score = rating * 0.7 + min(2.5, math.log10(max(1, votes) + 1) * 0.9)
        items.append((mid, score))
    items.sort(key=lambda kv: -kv[1])
    return items[:TOP_N_PER_USER]


def _write_output_json(filename: str, algorithm: str,
                       all_recs: dict[int, list[tuple[str, float]]]) -> Path:
    items: list[dict] = []
    for uid, ranked in all_recs.items():
        spark_uid = uid if uid >= SPARK_USER_OFFSET else uid + SPARK_USER_OFFSET
        for mid, score in ranked:
            items.append({"userId": spark_uid, "movieId": str(mid), "score": float(score)})
    payload = {"algorithm": algorithm, "items": items}
    SPARK_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = SPARK_OUTPUT_DIR / filename
    with out.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    return out


# --------- 批处理主入口（替代 run_spark_jobs.sh + spark-submit jar） ---------
def _run_spark_jobs_py() -> None:
    global _job_state
    SPARK_DATA_DIR.mkdir(parents=True, exist_ok=True)
    SPARK_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with _job_lock:
        _job_state.update({
            "running": True,
            "started_at": time.time(),
            "finished_at": None,
            "exit_code": None,
            "error": None,
        })

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    exit_code = -1
    error: str | None = None
    with LOG_FILE.open("w", encoding="utf-8") as log:
        try:
            _log(log, "===== [Mac Mock] Spark-like recompute started %s =====" % time.ctime())
            ratings_path = SPARK_DATA_DIR / "ratings.json"
            movies_path = SPARK_DATA_DIR / "movies_catalog.ndjson"
            _log(log, "read ratings: %s (%s)" % (ratings_path, ratings_path.exists()))
            _log(log, "read movies catalog: %s (%s)" % (movies_path, movies_path.exists()))

            ratings_rows = _load_ratings_ndjson(ratings_path)
            movies_map = _load_movies_ndjson(movies_path)
            _log(log, "rows: %d ratings, %d movies" % (len(ratings_rows), len(movies_map)))

            all_rated_by_user: dict[int, set[str]] = defaultdict(set)
            for r in ratings_rows:
                uid = int(r.get("userId") or r.get("user_id") or 0)
                mid = str(r.get("movieId") or r.get("movie_id") or "")
                if uid and mid:
                    real_uid = uid - SPARK_USER_OFFSET if uid >= SPARK_USER_OFFSET else uid
                    all_rated_by_user[real_uid].add(mid)
            _log(log, "distinct users: %d" % len(all_rated_by_user))

            _log(log, ">>> generating ALS-like recommendations")
            als_recs = _recommend_als(ratings_rows, all_rated_by_user, movies_map)
            als_path = _write_output_json("recommendations_als.json", "als", als_recs)
            _log(log, "    wrote %s (%d users)" % (als_path.name, len(als_recs)))

            _log(log, ">>> generating GraphX-like recommendations")
            gx_recs = _recommend_graphx(ratings_rows, all_rated_by_user, movies_map)
            gx_path = _write_output_json("recommendations_graphx.json", "graphx", gx_recs)
            _log(log, "    wrote %s (%d users)" % (gx_path.name, len(gx_recs)))

            _log(log, ">>> generating TF-IDF content recommendations")
            ct_recs = _recommend_content(ratings_rows, all_rated_by_user, movies_map)
            ct_path = _write_output_json("recommendations_content.json", "content", ct_recs)
            _log(log, "    wrote %s (%d users)" % (ct_path.name, len(ct_recs)))

            _log(log, "all done. exit=0")
            exit_code = 0
        except Exception as exc:
            error = "%s: %s" % (type(exc).__name__, exc)
            log.write("\nERROR: %s\n" % error)
            log.flush()
            exit_code = 1
            raise

    with _job_lock:
        _job_state.update({
            "running": False,
            "finished_at": time.time(),
            "exit_code": exit_code,
            "error": error,
        })


def _start_recompute() -> tuple[int, dict]:
    with _job_lock:
        if _job_state.get("running"):
            return 409, {"error": "Spark 任务正在运行", "status": dict(_job_state)}
    thread = threading.Thread(target=_run_spark_jobs_py)
    thread.daemon = True
    thread.start()
    return 202, {"message": "Spark-like 批处理已启动（Mac 本地 Python 实现）",
                 "status": dict(_job_state)}


# ========================================================================
# HTTP Handler（与 vm_recommend_server.py 完全相同）
# ========================================================================
class MockRecommendHandler(BaseHTTPRequestHandler):
    server_version = "SparkVMMock/1.0"

    def log_message(self, fmt: str, *args) -> None:
        print("[mock-spark-vm %s] %s" % (self.address_string(), fmt % args))

    def do_GET(self) -> None:
        path = unquote(self.path.split("?", 1)[0])
        if path == "/health":
            _json_response(self, 200, {"ok": True, "service": "spark-vm-mock", "mode": "mac-local-python"})
            return
        if path == "/spark/status":
            with _job_lock:
                payload = dict(_job_state)
            payload["log_tail"] = _tail_log()
            outputs: dict[str, dict] = {}
            for name in ("recommendations_als.json",
                         "recommendations_graphx.json",
                         "recommendations_content.json"):
                fp = SPARK_OUTPUT_DIR / name
                outputs[name] = {
                    "exists": fp.exists(),
                    "size": fp.stat().st_size if fp.exists() else 0,
                    "mtime": fp.stat().st_mtime if fp.exists() else None,
                }
            payload["outputs"] = outputs
            _json_response(self, 200, payload)
            return
        if path.startswith("/output/"):
            filename = path.split("/output/", 1)[1]
            if filename not in ("recommendations_als.json",
                                "recommendations_graphx.json",
                                "recommendations_content.json"):
                _json_response(self, 404, {"error": "unknown file"})
                return
            fp = SPARK_OUTPUT_DIR / filename
            if not fp.exists():
                _json_response(self, 404, {"error": "%s not found" % filename})
                return
            data = fp.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        _json_response(self, 404, {"error": "not found"})

    def do_POST(self) -> None:
        path = unquote(self.path.split("?", 1)[0])
        if path == "/sync/ratings":
            body = _read_body(self)
            if not body.strip():
                _json_response(self, 400, {"error": "empty body"})
                return
            SPARK_DATA_DIR.mkdir(parents=True, exist_ok=True)
            dest = SPARK_DATA_DIR / "ratings.json"
            dest.write_bytes(body)
            lines = len([ln for ln in body.decode("utf-8", errors="replace").splitlines() if ln.strip()])
            _json_response(self, 200, {
                "message": "ratings synced", "path": str(dest),
                "lines": lines, "bytes": len(body),
            })
            return
        if path == "/sync/movies":
            body = _read_body(self)
            if not body.strip():
                _json_response(self, 400, {"error": "empty body"})
                return
            SPARK_DATA_DIR.mkdir(parents=True, exist_ok=True)
            dest = SPARK_DATA_DIR / "movies_catalog.ndjson"
            dest.write_bytes(body)
            lines = len([ln for ln in body.decode("utf-8", errors="replace").splitlines() if ln.strip()])
            _json_response(self, 200, {
                "message": "movies catalog synced", "path": str(dest),
                "lines": lines, "bytes": len(body),
            })
            return
        if path == "/spark/recompute":
            code, payload = _start_recompute()
            _json_response(self, code, payload)
            return
        _json_response(self, 404, {"error": "not found"})


def main() -> None:
    httpd = ThreadingHTTPServer((HOST, PORT), MockRecommendHandler)
    print("[mock-spark-vm] listening on http://%s:%d" % (HOST, PORT))
    print("  project    : %s" % PROJECT_ROOT)
    print("  data dir   : %s" % SPARK_DATA_DIR)
    print("  output dir : %s" % SPARK_OUTPUT_DIR)
    print("  log        : %s" % LOG_FILE)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[mock-spark-vm] stopped.")


if __name__ == "__main__":
    main()

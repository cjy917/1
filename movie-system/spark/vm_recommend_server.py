#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ubuntu VM 上的 Spark 推荐网关（兼容 Python 3.6+）。
- POST /sync/ratings     接收 Windows 同步的 ratings.json（NDJSON）
- POST /spark/recompute  后台运行 run_spark_jobs.sh
- GET  /spark/status     查询批处理状态
- GET  /output/<name>    下载 recommendations_*.json

启动: python3 vm_recommend_server.py
默认: http://0.0.0.0:5001
"""
import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn
from urllib.parse import unquote

try:
    from http.server import ThreadingHTTPServer
except ImportError:

    class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
        daemon_threads = True


if sys.version_info < (3, 6):
    sys.exit("需要 Python 3.6 或更高版本，当前: %s" % sys.version)

HOST = os.environ.get("SPARK_VM_HOST", "0.0.0.0")
PORT = int(os.environ.get("SPARK_VM_PORT", "5001"))

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SPARK_DATA_DIR = SCRIPT_DIR / "data"
SPARK_OUTPUT_DIR = SCRIPT_DIR / "output"
RUN_SCRIPT = SCRIPT_DIR / "run_spark_jobs.sh"
LOG_FILE = Path(os.environ.get("SPARK_VM_LOG", "/tmp/spark_recommend_job.log"))

_job_lock = threading.Lock()
_job_state = {
    "running": False,
    "started_at": None,
    "finished_at": None,
    "exit_code": None,
    "error": None,
}


def _json_response(handler, code, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_body(handler):
    length = int(handler.headers.get("Content-Length", 0))
    return handler.rfile.read(length) if length > 0 else b""


def _tail_log(max_lines=30):
    if not LOG_FILE.exists():
        return ""
    text = LOG_FILE.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    return "\n".join(lines[-max_lines:])


def _run_spark_jobs():
    global _job_state
    SPARK_DATA_DIR.mkdir(parents=True, exist_ok=True)
    SPARK_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.setdefault("SPARK_HOME", "/opt/bigdata/spark")
    env.setdefault("FILMS_DATA", str(Path.home() / "cs1/films_data"))
    env["RECOMPILE"] = "0"
    env["PATH"] = env["SPARK_HOME"] + "/bin:" + env.get("PATH", "")

    with _job_lock:
        _job_state = {
            "running": True,
            "started_at": time.time(),
            "finished_at": None,
            "exit_code": None,
            "error": None,
        }

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    exit_code = -1
    error = None
    try:
        with LOG_FILE.open("w", encoding="utf-8") as log:
            log.write("===== Spark recompute started %s =====\n" % time.ctime())
            log.flush()
            proc = subprocess.run(
                ["bash", str(RUN_SCRIPT)],
                cwd=str(SCRIPT_DIR),
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        exit_code = proc.returncode
        error = None if exit_code == 0 else "run_spark_jobs.sh exited with %s" % exit_code
    except Exception as exc:
        exit_code = -1
        error = str(exc)
        with LOG_FILE.open("a", encoding="utf-8") as log:
            log.write("\nERROR: %s\n" % exc)

    with _job_lock:
        _job_state["running"] = False
        _job_state["finished_at"] = time.time()
        _job_state["exit_code"] = exit_code
        _job_state["error"] = error


def _start_recompute():
    with _job_lock:
        if _job_state.get("running"):
            return 409, {"error": "Spark 任务正在运行", "status": dict(_job_state)}
    thread = threading.Thread(target=_run_spark_jobs)
    thread.daemon = True
    thread.start()
    return 202, {"message": "Spark 批处理已启动", "status": dict(_job_state)}


class RecommendHandler(BaseHTTPRequestHandler):
    server_version = "SparkVMRecommend/1.0"

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.address_string(), fmt % args))

    def do_GET(self):
        path = unquote(self.path.split("?", 1)[0])

        if path == "/health":
            _json_response(self, 200, {"ok": True, "service": "spark-vm-gateway"})
            return

        if path == "/spark/status":
            with _job_lock:
                payload = dict(_job_state)
            payload["log_tail"] = _tail_log()
            outputs = {}
            for name in (
                "recommendations_als.json",
                "recommendations_graphx.json",
                "recommendations_content.json",
            ):
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
            if filename not in (
                "recommendations_als.json",
                "recommendations_graphx.json",
                "recommendations_content.json",
            ):
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

    def do_POST(self):
        path = unquote(self.path.split("?", 1)[0])

        if path == "/sync/ratings":
            body = _read_body(self)
            if not body.strip():
                _json_response(self, 400, {"error": "empty body"})
                return
            SPARK_DATA_DIR.mkdir(parents=True, exist_ok=True)
            dest = SPARK_DATA_DIR / "ratings.json"
            dest.write_bytes(body)
            text = body.decode("utf-8", errors="replace")
            lines = len([ln for ln in text.splitlines() if ln.strip()])
            _json_response(
                self,
                200,
                {
                    "message": "ratings synced",
                    "path": str(dest),
                    "lines": lines,
                    "bytes": len(body),
                },
            )
            return

        if path == "/spark/recompute":
            code, payload = _start_recompute()
            _json_response(self, code, payload)
            return

        _json_response(self, 404, {"error": "not found"})


def main():
    if not RUN_SCRIPT.exists():
        raise SystemExit("找不到 %s" % RUN_SCRIPT)
    httpd = ThreadingHTTPServer((HOST, PORT), RecommendHandler)
    print("Spark VM gateway listening on http://%s:%s" % (HOST, PORT))
    print("  Python: %s" % sys.version.split()[0])
    print("  project: %s" % PROJECT_ROOT)
    print("  ratings: %s" % (SPARK_DATA_DIR / "ratings.json"))
    print("  output:  %s" % SPARK_OUTPUT_DIR)
    httpd.serve_forever()


if __name__ == "__main__":
    main()

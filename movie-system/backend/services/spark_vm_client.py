#!/usr/bin/env python3
"""Windows 后端调用 Ubuntu VM Spark 网关。"""
from __future__ import annotations

import time
from pathlib import Path

import requests

from config import (
    SPARK_DATA_DIR,
    SPARK_OUTPUT_DIR,
    SPARK_RECOMPUTE_POLL_INTERVAL,
    SPARK_RECOMPUTE_TIMEOUT,
    SPARK_VM_ENABLED,
    SPARK_VM_URL,
)


class SparkVMError(RuntimeError):
    pass


def _vm_url(path: str) -> str:
    return f"{SPARK_VM_URL.rstrip('/')}{path}"


def vm_available() -> bool:
    if not SPARK_VM_ENABLED:
        return False
    try:
        resp = requests.get(_vm_url("/health"), timeout=5)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def sync_ratings_to_vm(ratings_path: Path | None = None) -> dict:
    ratings_path = ratings_path or (SPARK_DATA_DIR / "ratings.json")
    if not ratings_path.exists():
        raise SparkVMError(f"缺少评分文件: {ratings_path}")
    body = ratings_path.read_bytes()
    try:
        resp = requests.post(
            _vm_url("/sync/ratings"),
            data=body,
            headers={"Content-Type": "application/x-ndjson"},
            timeout=120,
        )
    except requests.RequestException as exc:
        raise SparkVMError(f"无法连接 VM Spark 网关 ({SPARK_VM_URL}): {exc}") from exc
    if resp.status_code != 200:
        raise SparkVMError(f"同步 ratings 失败: {resp.text}")
    return resp.json()


def trigger_recompute_on_vm() -> dict:
    try:
        resp = requests.post(_vm_url("/spark/recompute"), timeout=30)
    except requests.RequestException as exc:
        raise SparkVMError(f"无法触发 VM Spark 重算: {exc}") from exc
    if resp.status_code not in (200, 202):
        raise SparkVMError(f"触发 Spark 重算失败: {resp.text}")
    return resp.json()


def get_vm_job_status() -> dict:
    try:
        resp = requests.get(_vm_url("/spark/status"), timeout=15)
    except requests.RequestException as exc:
        raise SparkVMError(f"无法查询 VM Spark 状态: {exc}") from exc
    if resp.status_code != 200:
        raise SparkVMError(f"查询 Spark 状态失败: {resp.text}")
    return resp.json()


def wait_for_vm_job(timeout: int | None = None) -> dict:
    deadline = time.time() + (timeout if timeout is not None else SPARK_RECOMPUTE_TIMEOUT)
    last_status: dict = {}
    while time.time() < deadline:
        last_status = get_vm_job_status()
        if not last_status.get("running"):
            exit_code = last_status.get("exit_code")
            if exit_code not in (None, 0):
                tail = last_status.get("log_tail") or ""
                raise SparkVMError(
                    f"VM Spark 批处理失败 (exit={exit_code})。\n{tail[-800:]}"
                )
            return last_status
        time.sleep(SPARK_RECOMPUTE_POLL_INTERVAL)
    raise SparkVMError(
        f"等待 VM Spark 完成超时（>{SPARK_RECOMPUTE_TIMEOUT}s）。"
        "请稍后在 VM 上查看日志并重试。"
    )


def download_output_from_vm() -> list[str]:
    SPARK_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    for name in (
        "recommendations_als.json",
        "recommendations_graphx.json",
        "recommendations_content.json",
    ):
        try:
            resp = requests.get(_vm_url(f"/output/{name}"), timeout=120)
        except requests.RequestException as exc:
            raise SparkVMError(f"下载 {name} 失败: {exc}") from exc
        if resp.status_code != 200:
            raise SparkVMError(f"VM 上缺少 {name}（HTTP {resp.status_code}）")
        dest = SPARK_OUTPUT_DIR / name
        dest.write_bytes(resp.content)
        saved.append(name)
    return saved


def run_spark_pipeline_on_vm() -> dict:
    """评分同步 → 触发 Spark 重算 → 等待完成 → 拉回三份 JSON。"""
    if not SPARK_VM_ENABLED:
        raise SparkVMError("SPARK_VM_ENABLED=false，未启用 VM Spark 网关")
    if not vm_available():
        raise SparkVMError(
            f"VM Spark 网关不可用 ({SPARK_VM_URL})。"
            "请在 Ubuntu 上运行: python3 spark/vm_recommend_server.py"
        )
    sync_info = sync_ratings_to_vm()
    trigger_recompute_on_vm()
    status = wait_for_vm_job()
    files = download_output_from_vm()
    return {"sync": sync_info, "status": status, "files": files}

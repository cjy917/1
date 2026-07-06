#!/usr/bin/env python3

"""Windows 后端调用 Ubuntu VM Spark 网关。"""

from __future__ import annotations



import time

from pathlib import Path



import requests



from config import (

    SPARK_DATA_DIR,

    SPARK_HISTORY_RATINGS,

    SPARK_OUTPUT_DIR,

    SPARK_RECOMPUTE_POLL_INTERVAL,

    SPARK_RECOMPUTE_TIMEOUT,

    SPARK_USER_OFFSET,

    SPARK_VM_ENABLED,

    SPARK_VM_URL,

    SPARK_WEB_RATINGS,

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





def get_history_status_on_vm() -> dict:

    try:

        resp = requests.get(_vm_url("/spark/history/status"), timeout=15)

    except requests.RequestException as exc:

        raise SparkVMError(f"无法查询 VM 历史评分状态: {exc}") from exc

    if resp.status_code != 200:

        raise SparkVMError(f"查询历史评分状态失败: {resp.text}")

    return resp.json()





def sync_ratings_file_to_vm(ratings_path: Path, endpoint: str) -> dict:

    if not ratings_path.exists():

        raise SparkVMError(f"缺少评分文件: {ratings_path}")

    body = ratings_path.read_bytes()

    try:

        resp = requests.post(

            _vm_url(endpoint),

            data=body,

            headers={"Content-Type": "application/x-ndjson"},

            timeout=300,

        )

    except requests.RequestException as exc:

        raise SparkVMError(f"无法连接 VM Spark 网关 ({SPARK_VM_URL}): {exc}") from exc

    if resp.status_code != 200:

        raise SparkVMError(f"同步 {ratings_path.name} 失败: {resp.text}")

    return resp.json()





def sync_history_ratings_to_vm(ratings_path: Path | None = None) -> dict:

    ratings_path = ratings_path or SPARK_HISTORY_RATINGS

    return sync_ratings_file_to_vm(ratings_path, "/sync/ratings/history")





def sync_web_ratings_to_vm(ratings_path: Path | None = None) -> dict:

    ratings_path = ratings_path or SPARK_WEB_RATINGS

    return sync_ratings_file_to_vm(ratings_path, "/sync/ratings/web")





def sync_ratings_to_vm(ratings_path: Path | None = None) -> dict:

    """兼容旧版全量 ratings.json 同步。"""

    ratings_path = ratings_path or (SPARK_DATA_DIR / "ratings.json")

    return sync_ratings_file_to_vm(ratings_path, "/sync/ratings")





def ensure_history_ratings_on_vm(*, local_line_count: int | None = None) -> dict:

    """历史评分首次或本地行数变化时同步到 VM。"""

    status = get_history_status_on_vm()

    vm_lines = int(status.get("lines") or 0)

    if local_line_count is None:

        history_path = SPARK_HISTORY_RATINGS

        if history_path.exists():

            local_line_count = sum(1 for ln in history_path.read_text(encoding="utf-8").splitlines() if ln.strip())

        else:

            local_line_count = 0



    if vm_lines > 0 and vm_lines == local_line_count:

        return {"skipped": True, "lines": vm_lines, "message": "history already on VM"}



    return sync_history_ratings_to_vm()





def sync_movies_catalog_to_vm(catalog_path: Path | None = None) -> dict:

    catalog_path = catalog_path or (SPARK_DATA_DIR / "movies_catalog.ndjson")

    if not catalog_path.exists():

        raise SparkVMError(f"缺少电影特征文件: {catalog_path}")

    body = catalog_path.read_bytes()

    try:

        resp = requests.post(

            _vm_url("/sync/movies"),

            data=body,

            headers={"Content-Type": "application/x-ndjson"},

            timeout=120,

        )

    except requests.RequestException as exc:

        raise SparkVMError(f"无法连接 VM Spark 网关 ({SPARK_VM_URL}): {exc}") from exc

    if resp.status_code != 200:

        raise SparkVMError(f"同步 movies catalog 失败: {resp.text}")

    return resp.json()





def trigger_recompute_on_vm() -> dict:

    try:

        resp = requests.post(_vm_url("/spark/recompute"), timeout=30)

    except requests.RequestException as exc:

        raise SparkVMError(f"无法触发 VM Spark 重算: {exc}") from exc

    if resp.status_code not in (200, 202):

        raise SparkVMError(f"触发 Spark 重算失败: {resp.text}")

    return resp.json()





def trigger_incremental_recompute_on_vm(target_spark_user_id: int | None = None) -> dict:

    payload = {}

    if target_spark_user_id is not None:

        payload["target_user_id"] = target_spark_user_id

    try:

        resp = requests.post(_vm_url("/spark/recompute/incremental"), json=payload, timeout=30)

    except requests.RequestException as exc:

        raise SparkVMError(f"无法触发 VM 增量 Spark 重算: {exc}") from exc

    if resp.status_code not in (200, 202):

        raise SparkVMError(f"触发增量 Spark 重算失败: {resp.text}")

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

    """全量：评分与片库同步 → 触发 Spark 重算 → 等待完成 → 拉回三份 JSON。"""

    if not SPARK_VM_ENABLED:

        raise SparkVMError("SPARK_VM_ENABLED=false，未启用 VM Spark 网关")

    if not vm_available():

        raise SparkVMError(

            f"VM Spark 网关不可用 ({SPARK_VM_URL})。"

            "请在 Ubuntu 上运行: python3 spark/vm_recommend_server.py"

        )

    sync_info = {

        "ratings": sync_ratings_to_vm(),

        "movies": sync_movies_catalog_to_vm(),

    }

    trigger_recompute_on_vm()

    status = wait_for_vm_job()

    files = download_output_from_vm()

    return {"sync": sync_info, "status": status, "files": files, "mode": "full"}





def run_spark_incremental_on_vm(user_id: int) -> dict:

    """增量：历史评分按需同步 → 仅同步网站评分 → 增量 Spark → 拉回 JSON。"""

    if not SPARK_VM_ENABLED:

        raise SparkVMError("SPARK_VM_ENABLED=false，未启用 VM Spark 网关")

    if not vm_available():

        raise SparkVMError(

            f"VM Spark 网关不可用 ({SPARK_VM_URL})。"

            "请在 Ubuntu 上运行: python3 spark/vm_recommend_server.py"

        )



    history_info = ensure_history_ratings_on_vm()

    sync_info = {

        "history": history_info,

        "web": sync_web_ratings_to_vm(),

        "movies": sync_movies_catalog_to_vm(),

    }

    target_spark_uid = SPARK_USER_OFFSET + user_id

    trigger_incremental_recompute_on_vm(target_spark_uid)

    status = wait_for_vm_job(timeout=min(SPARK_RECOMPUTE_TIMEOUT, 300))

    files = download_output_from_vm()

    return {

        "sync": sync_info,

        "status": status,

        "files": files,

        "mode": "incremental",

        "target_user_id": target_spark_uid,

    }


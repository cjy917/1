from __future__ import annotations

import io
import json
import logging
import os
import socket
import ssl
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any
from urllib.request import HTTPSHandler, HTTPHandler, ProxyHandler, build_opener

from config import HTTPS_PROXY, HTTP_PROXY, NO_PROXY, SOCKS_PROXY

logger = logging.getLogger("ai_http_helper")

_NO_PROXY_SET = {s.strip() for s in (NO_PROXY or "").split(",") if s.strip()}

_DETECTED_OS_HTTP_PROXY: str | None = None
_DETECTED_OS_HTTPS_PROXY: str | None = None
_DETECTED_OS_SOCKS_PROXY: str | None = None
_OS_PROXY_DETECTED: bool = False


def _run_command(cmd: list[str], timeout: int = 5) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (proc.stdout or "") + (proc.stderr or "")
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return ""


def _parse_scutil_proxy(output: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    try:
        for raw_line in output.splitlines():
            stripped = raw_line.strip()
            if not stripped or stripped in ("{", "}") or stripped.startswith("<"):
                continue
            if ":" not in stripped:
                continue
            if stripped.endswith("{") or stripped.endswith("}"):
                continue
            k, _, v = stripped.partition(":")
            k = k.strip().rstrip(":").strip()
            v = v.strip().rstrip(",").strip()
            if not k or k.startswith("<"):
                continue
            if v.startswith("<"):
                continue
            if v.isdigit() and not k.lower().endswith("address"):
                try:
                    result[k] = int(v)
                    continue
                except Exception:
                    pass
            result[k] = v
    except Exception:
        pass
    return result


def _detect_macos_system_proxy() -> None:
    global _DETECTED_OS_HTTP_PROXY, _DETECTED_OS_HTTPS_PROXY, _DETECTED_OS_SOCKS_PROXY, _OS_PROXY_DETECTED
    if _OS_PROXY_DETECTED:
        return
    _OS_PROXY_DETECTED = True
    if sys.platform != "darwin":
        return
    raw = _run_command(["scutil", "--proxy"])
    if not raw:
        return
    parsed = _parse_scutil_proxy(raw)
    logger.debug("macOS scutil --proxy 解析结果: %s", json.dumps(parsed, ensure_ascii=False))

    def pick(cfg: dict[str, Any], enable_key: str, host_key: str, port_key: str) -> tuple[str, int] | None:
        enabled = False
        host = ""
        port = 0
        try:
            for k, v in cfg.items():
                k_low = k.lower()
                if "enable" in k_low and enable_key.lower() in k_low:
                    enabled = str(v) in ("1", "true", "True", "yes", "YES")
                if enable_key and k.lower() == enable_key.lower():
                    enabled = str(v) in ("1", "true", "True", "yes", "YES")
                if host_key and k.lower() == host_key.lower():
                    host = str(v)
                if "address" in k_low and host_key.lower() in k_low.replace(" ", "") and "port" not in k_low:
                    host = str(v)
                if port_key and k.lower() == port_key.lower():
                    try:
                        port = int(v)
                    except Exception:
                        port = 0
                if "port" in k_low and port_key.lower() in k_low.replace(" ", ""):
                    try:
                        port = int(v)
                    except Exception:
                        pass
            if not (enabled and host and port > 0):
                return None
            return (host, port)
        except Exception:
            return None

    http_info = pick(parsed, "HTTPEnable", "HTTPProxy", "HTTPPort")
    if http_info:
        host, port = http_info
        _DETECTED_OS_HTTP_PROXY = f"http://{host}:{port}"
    https_info = pick(parsed, "HTTPSEnable", "HTTPSProxy", "HTTPSPort")
    if https_info:
        host, port = https_info
        _DETECTED_OS_HTTPS_PROXY = f"http://{host}:{port}"
    socks_info = pick(parsed, "SOCKSEnable", "SOCKSProxy", "SOCKSPort")
    if socks_info:
        host, port = socks_info
        _DETECTED_OS_SOCKS_PROXY = f"socks5://{host}:{port}"


def _env_all_proxy() -> str | None:
    for k in ("ALL_PROXY", "all_proxy", "ALLPROXY"):
        v = os.environ.get(k)
        if v:
            return v
    return None


def _get_effective_proxies() -> tuple[str | None, str | None, str | None]:
    effective_http = HTTP_PROXY or _env_all_proxy() or None
    effective_https = HTTPS_PROXY or _env_all_proxy() or None
    effective_socks = SOCKS_PROXY or _env_all_proxy() or None

    need_detect = not (effective_http or effective_https or effective_socks)
    if need_detect and sys.platform == "darwin":
        _detect_macos_system_proxy()
        if not effective_http and _DETECTED_OS_HTTP_PROXY:
            effective_http = _DETECTED_OS_HTTP_PROXY
            logger.info("✨ 自动检测到 macOS HTTP 代理: %s", _mask_api_key(effective_http))
        if not effective_https and _DETECTED_OS_HTTPS_PROXY:
            effective_https = _DETECTED_OS_HTTPS_PROXY
            logger.info("✨ 自动检测到 macOS HTTPS 代理: %s", _mask_api_key(effective_https))
        if not effective_socks and _DETECTED_OS_SOCKS_PROXY and not (effective_http and effective_https):
            effective_socks = _DETECTED_OS_SOCKS_PROXY
            logger.info("✨ 自动检测到 macOS SOCKS 代理: %s", _mask_api_key(effective_socks))
    return effective_http, effective_https, effective_socks


def _should_bypass_proxy(hostname: str) -> bool:
    if not hostname:
        return True
    for rule in _NO_PROXY_SET:
        rule = rule.strip().lower()
        if not rule:
            continue
        if "*" in rule:
            prefix = rule.rstrip("*").rstrip(".")
            if hostname.lower().startswith(prefix):
                return True
        if hostname.lower() == rule or hostname.lower().endswith("." + rule):
            return True
    return False


def _mask_api_key(url_or_header: str) -> str:
    if not url_or_header:
        return ""
    if len(url_or_header) <= 8:
        return "*" * len(url_or_header)
    return url_or_header[:4] + "*" * (len(url_or_header) - 8) + url_or_header[-4:]


class _SOCKS5Socket:
    def __init__(self, family: int = socket.AF_INET, type_: int = socket.SOCK_STREAM, proto: int = 0, *, proxy_url: str, target_host: str, target_port: int, timeout: float = 30.0):
        self._sock = socket.socket(family, type_, proto)
        parsed = urllib.parse.urlparse(proxy_url)
        self._proxy_host = parsed.hostname or "127.0.0.1"
        self._proxy_port = int(parsed.port or 1080)
        self._username = parsed.username
        self._password = parsed.password
        self._target_host = target_host
        self._target_port = target_port
        self._timeout = timeout

    def __getattr__(self, name: str):
        return getattr(self._sock, name)

    def _socks5_connect(self) -> None:
        self._sock.settimeout(self._timeout)
        self._sock.connect((self._proxy_host, self._proxy_port))
        methods = bytearray([0x05, 0x01, 0x00])
        if self._username and self._password:
            methods = bytearray([0x05, 0x02, 0x00, 0x02])
        self._sock.sendall(bytes(methods))
        resp = self._recv_exact(2)
        if resp[0] != 0x05:
            raise ConnectionError("SOCKS5: 服务器返回版本不支持")
        method = resp[1]
        if method == 0x02:
            if not self._username or not self._password:
                raise ConnectionError("SOCKS5: 服务器要求用户名密码认证但未提供")
            u = self._username.encode("utf-8")
            p = self._password.encode("utf-8")
            pkt = bytes([0x01, len(u)]) + u + bytes([len(p)]) + p
            self._sock.sendall(pkt)
            resp2 = self._recv_exact(2)
            if resp2[1] != 0x00:
                raise ConnectionError("SOCKS5: 用户名密码认证失败")
        elif method != 0x00:
            raise ConnectionError(f"SOCKS5: 不支持的握手方法 0x{method:02x}")

        host_bytes = self._target_host.encode("idna") if not _is_ip_address(self._target_host) else None
        if host_bytes:
            atyp = 0x03
            addr_pkt = bytes([0x03, len(host_bytes)]) + host_bytes
        elif ":" in self._target_host:
            atyp = 0x04
            addr_pkt = b"\x04" + socket.inet_pton(socket.AF_INET6, self._target_host)
        else:
            atyp = 0x01
            addr_pkt = b"\x01" + socket.inet_aton(self._target_host)
        req = bytearray([0x05, 0x01, 0x00]) + addr_pkt + struct.pack(">H", self._target_port)
        self._sock.sendall(bytes(req))
        resp3 = self._recv_exact(4)
        if resp3[0] != 0x05 or resp3[1] != 0x00:
            raise ConnectionError(f"SOCKS5: 连接失败 状态=0x{resp3[1]:02x}")
        atyp2 = resp3[3]
        if atyp2 == 0x01:
            self._recv_exact(4)
        elif atyp2 == 0x03:
            ln = self._recv_exact(1)[0]
            self._recv_exact(ln)
        elif atyp2 == 0x04:
            self._recv_exact(16)
        self._recv_exact(2)

    def _recv_exact(self, n: int) -> bytes:
        buf = bytearray()
        while len(buf) < n:
            chunk = self._sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("SOCKS5: 连接意外关闭")
            buf.extend(chunk)
        return bytes(buf)

    def connect(self, address) -> None:
        self._socks5_connect()

    def makefile(self, mode="r", buffering=None, *args, **kwargs):
        class _SockFile(io.BufferedIOBase):
            def __init__(self, socksock: "_SOCKS5Socket"):
                self._sock = socksock
                self._rbuf = b""

            def readable(self):
                return True

            def writable(self):
                return True

            def read(self, size=-1):
                if size is None or size < 0:
                    while True:
                        try:
                            chunk = self._sock._sock.recv(4096)
                        except socket.timeout:
                            break
                        if not chunk:
                            break
                        self._rbuf += chunk
                    result = self._rbuf
                    self._rbuf = b""
                    return result
                while len(self._rbuf) < size:
                    try:
                        chunk = self._sock._sock.recv(size - len(self._rbuf))
                    except socket.timeout:
                        break
                    if not chunk:
                        break
                    self._rbuf += chunk
                result = self._rbuf[:size]
                self._rbuf = self._rbuf[size:]
                return result

            def read1(self, size=-1):
                if self._rbuf:
                    take = size if size and size > 0 else len(self._rbuf)
                    result = self._rbuf[:take]
                    self._rbuf = self._rbuf[take:]
                    return result
                try:
                    return self._sock._sock.recv(4096 if size is None or size <= 0 else size)
                except socket.timeout:
                    return b""

            def write(self, data):
                return self._sock._sock.send(data)

            def flush(self):
                return None

            def close(self):
                self._sock.close()

        return _SockFile(self)

    def sendall(self, data, *args, **kwargs):
        return self._sock.sendall(data, *args, **kwargs)

    def send(self, data, *args, **kwargs):
        return self._sock.send(data, *args, **kwargs)

    def recv(self, size, *args, **kwargs):
        return self._sock.recv(size, *args, **kwargs)

    def settimeout(self, value):
        self._sock.settimeout(value)
        self._timeout = value

    def close(self):
        try:
            self._sock.close()
        except Exception:
            pass


def _is_ip_address(s: str) -> bool:
    try:
        socket.inet_aton(s)
        return True
    except Exception:
        try:
            socket.inet_pton(socket.AF_INET6, s)
            return True
        except Exception:
            return False


class _SOCKS5HTTPHandler(HTTPHandler):
    def __init__(self, proxy_url: str, debuglevel: int = 0):
        super().__init__(debuglevel=debuglevel)
        self._proxy_url = proxy_url

    def http_open(self, req):
        target = urllib.parse.urlparse(req.full_url if hasattr(req, "full_url") else req.get_full_url())
        host = target.hostname
        port = target.port or 80

        def _connect_factory(address, timeout: float = 30.0) -> _SOCKS5Socket:
            sock = _SOCKS5Socket(proxy_url=self._proxy_url, target_host=host, target_port=port, timeout=timeout)
            sock.connect(address)
            return sock

        return self.do_open(_SockConnWrapper(self._proxy_url, host, port), req)


class _SockConnWrapper:
    def __init__(self, proxy_url: str, target_host: str, target_port: int):
        self._proxy_url = proxy_url
        self._target_host = target_host
        self._target_port = target_port

    def __call__(self, address, timeout: float = 30.0, *args, **kwargs):
        sock = _SOCKS5Socket(proxy_url=self._proxy_url, target_host=self._target_host, target_port=self._target_port, timeout=timeout)
        sock.connect(address)
        return sock


class _SOCKS5HTTPSHandler(HTTPSHandler):
    def __init__(self, proxy_url: str, ssl_ctx: ssl.SSLContext | None = None, debuglevel: int = 0):
        super().__init__(context=ssl_ctx, debuglevel=debuglevel) if ssl_ctx is not None else super().__init__(debuglevel=debuglevel)
        self._proxy_url = proxy_url
        self._ssl_ctx = ssl_ctx

    def https_open(self, req):
        target = urllib.parse.urlparse(req.full_url if hasattr(req, "full_url") else req.get_full_url())
        host = target.hostname
        port = target.port or 443
        ssl_ctx = self._ssl_ctx or ssl.create_default_context()

        class _WrappedConn:
            def __init__(s, addr, timeout: float = 30.0, *av, **kw):
                s._raw = _SOCKS5Socket(proxy_url=self._proxy_url, target_host=host, target_port=port, timeout=timeout)
                s._raw.connect(addr)
                s._sock = ssl_ctx.wrap_socket(s._raw, server_hostname=host)

            def __getattr__(s, name):
                return getattr(s._sock, name)

            def makefile(s, *a, **kw):
                return s._sock.makefile(*a, **kw)

            def close(s):
                try:
                    s._sock.close()
                except Exception:
                    pass

        return self.do_open(_WrappedConn, req)


def _build_socks_opener(proxy_url: str, ssl_ctx: ssl.SSLContext):
    http_handler = _SOCKS5HTTPHandler(proxy_url)
    https_handler = _SOCKS5HTTPSHandler(proxy_url, ssl_ctx=ssl_ctx)
    return build_opener(http_handler, https_handler)


def build_opener_with_proxy(url_hostname: str):
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    bypass = _should_bypass_proxy(url_hostname)
    proxies: dict[str, str] = {}
    use_socks_only = False

    if not bypass:
        eff_http, eff_https, eff_socks = _get_effective_proxies()
        if eff_http:
            proxies["http"] = eff_http
        if eff_https:
            proxies["https"] = eff_https
        if not proxies and eff_socks:
            use_socks_only = True
            parsed = urllib.parse.urlparse(eff_socks)
            scheme = parsed.scheme.lower() if parsed.scheme else "socks5"
            if scheme.startswith("socks"):
                proxies["_socks"] = eff_socks

    if use_socks_only and "_socks" in proxies:
        opener = _build_socks_opener(proxies["_socks"], ssl_ctx)
        logger.debug("HTTP 使用 SOCKS5 代理=%s target=%s", _mask_api_key(proxies["_socks"]), url_hostname)
        return opener, {"socks": proxies["_socks"]}
    if proxies:
        handler = ProxyHandler({k: v for k, v in proxies.items() if k in ("http", "https")})
        opener = build_opener(handler, HTTPHandler(), HTTPSHandler(context=ssl_ctx))
        logger.debug(
            "HTTP 使用代理 https_proxy=%s http_proxy=%s target=%s",
            _mask_api_key(proxies.get("https", "")),
            _mask_api_key(proxies.get("http", "")),
            url_hostname,
        )
        return opener, {k: v for k, v in proxies.items() if k in ("http", "https")}
    else:
        opener = build_opener(HTTPHandler(), HTTPSHandler(context=ssl_ctx))
        logger.debug("HTTP 直连 (不使用代理) target=%s bypass=%s", url_hostname, bypass)
        return opener, proxies


def classify_error(exc: Exception, url: str, elapsed_ms: int) -> dict[str, Any]:
    info: dict[str, Any] = {
        "category": "unknown",
        "message": str(exc),
        "elapsed_ms": elapsed_ms,
        "url": url,
    }
    msg = str(exc).lower()
    if isinstance(exc, urllib.error.HTTPError):
        code = exc.code
        info["http_status"] = code
        if code == 401:
            info["category"] = "auth_failed"
            info["hint"] = "API Key 无效或已过期，请检查 secrets.local 中的 AI_ASSISTANT_API_KEY / AI_WEB_SEARCH_API_KEY"
        elif code == 429:
            info["category"] = "rate_limited"
            info["hint"] = "AI 服务请求频率超限，请稍后再试或升级套餐"
        elif code == 400:
            info["category"] = "bad_request"
            info["hint"] = "请求参数错误，请检查模型名和消息格式"
        elif 500 <= code < 600:
            info["category"] = "upstream_5xx"
            info["hint"] = "上游 AI 服务故障，稍后重试；如持续失败可尝试切换代理或改走直连"
        else:
            info["category"] = f"http_{code}"
            info["hint"] = f"上游 AI 服务返回 HTTP {code}"
    elif isinstance(exc, urllib.error.URLError):
        reason = exc.reason
        if isinstance(reason, socket.timeout) or "timeout" in msg or "timed out" in msg:
            info["category"] = "timeout"
            info["hint"] = (
                "请求超时：macOS 下 Shadowrocket 常见原因：1) 节点响应慢，建议切换更快的节点后重试；"
                "2) 路由规则未放行 api.siliconflow.cn / api.tavily.com，需确保走代理而非直连；"
                "3) 已在 secrets.local 手动设置更长超时（当前 AI_ASSISTANT_TIMEOUT 默认 90 秒）。"
            )
        elif isinstance(reason, OSError):
            errno = getattr(reason, "errno", None)
            if errno == 8 or "nodename nor servname" in msg or "getaddrinfo" in msg:
                info["category"] = "dns_failed"
                info["hint"] = (
                    "DNS 解析失败：Shadowrocket 没有正确接管 DNS。请确认 Shadowrocket 已开启「系统代理」，"
                    "或在系统设置 → 网络 → 代理里确认 HTTP/HTTPS/SOCKS 代理主机和端口被正确设置。"
                )
            elif errno == 61 or "connection refused" in msg:
                info["category"] = "proxy_connection_refused"
                info["hint"] = (
                    "代理端口拒绝连接：Shadowrocket 的实际 HTTP/HTTPS/SOCKS 端口与配置不匹配。"
                    "解决：在 macOS 终端执行 `scutil --proxy` 查看实际端口，"
                    "或在 Shadowrocket 设置里手动固定 HTTP 代理端口并写到 secrets.local 的 HTTP_PROXY/HTTPS_PROXY。"
                )
            elif errno == 51 or "network is unreachable" in msg:
                info["category"] = "network_unreachable"
                info["hint"] = "网络不可达：请确认 Shadowrocket 已连接节点，或切换节点后重试"
            elif "socks5" in msg or "SOCKS5" in str(type(reason).__name__):
                info["category"] = "socks5_protocol_error"
                info["hint"] = "SOCKS5 协议握手失败：Shadowrocket 的 SOCKS 端口未启用认证方式不匹配，请在 Shadowrocket 改用 HTTP 代理模式"
            elif "certificate verify failed" in msg or "SSL" in str(type(reason).__name__):
                info["category"] = "ssl_error"
                info["hint"] = "SSL 证书错误：可能是 Shadowrocket 开启了 HTTPS MITM，请关闭 MITM 或把代理根证书加入系统信任"
            else:
                info["category"] = "os_error"
                info["hint"] = f"系统连接错误 (errno={errno})：{str(reason)}"
        else:
            info["category"] = "url_error"
            info["hint"] = f"URL 错误：{str(reason)}"
    elif isinstance(exc, socket.timeout) or "timeout" in msg:
        info["category"] = "timeout"
        info["hint"] = (
            "请求超时：Shadowrocket 路由规则未放行目标域名。请在 Shadowrocket 的「配置 → 规则」里确认"
            "*.siliconflow.cn / *.tavily.com 走代理，不要直连。"
        )
    else:
        info["category"] = "unknown"
        info["hint"] = f"未知错误类型：{type(exc).__name__}，请查看后端日志"
    info[
        "debug_suggestions"
    ] = (
        "macOS + Shadowrocket 用户一键排查：1) 打开 Shadowrocket，确保左上角状态为「已连接」；2) 点击「设置 → 系统代理」，"
        "勾选「设置为系统代理」；3) 终端执行 `scutil --proxy`，检查 HTTPEnable/HTTPSEnable/SOCKSEnable=1 且端口非空；"
        "4) 如果还失败，在 Shadowrocket 首页 → 点击节点旁的 (i) → 勾选「HTTP 代理」并自定义端口如 8888，"
        "然后在 secrets.local 写 HTTP_PROXY=http://127.0.0.1:8888 HTTPS_PROXY=http://127.0.0.1:8888 重启 Flask。"
    )
    return info


def http_json_request(
    url: str,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    logger_tag: str = "AI",
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    start = time.time()
    parsed = urllib.parse.urlparse(url)
    hostname = parsed.hostname or ""
    opener, proxies = build_opener_with_proxy(hostname)

    payload_bytes: bytes | None = None
    if body is not None:
        payload_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")

    headers = {**(headers or {})}
    if payload_bytes is not None and "Content-Type" not in {k.title(): v for k, v in headers.items()}:
        headers["Content-Type"] = "application/json"
    safe_headers = {
        k: (
            _mask_api_key(v)
            if k.lower() == "authorization" or "key" in k.lower() or "token" in k.lower()
            else v
        )
        for k, v in headers.items()
    }
    eff_http, eff_https, eff_socks = _get_effective_proxies()
    logger.info(
        "[%s] %s %s 开始请求 body_size=%s 代理=%s 超时=%ds headers=%s",
        logger_tag,
        method,
        url,
        len(payload_bytes or b""),
        "启用(" + ",".join(proxies.keys()) + ")" if proxies else "禁用",
        timeout,
        safe_headers,
    )
    logger.info(
        "[%s] 当前代理配置：用户配置 HTTP_PROXY=%s HTTPS_PROXY=%s SOCKS_PROXY=%s；OS 检测：HTTP=%s HTTPS=%s SOCKS=%s",
        logger_tag,
        _mask_api_key(HTTP_PROXY) if HTTP_PROXY else "<未设置>",
        _mask_api_key(HTTPS_PROXY) if HTTPS_PROXY else "<未设置>",
        _mask_api_key(SOCKS_PROXY) if SOCKS_PROXY else "<未设置>",
        _mask_api_key(_DETECTED_OS_HTTP_PROXY or "") + ("" if _OS_PROXY_DETECTED else "(未检测 scutil)"),
        _mask_api_key(_DETECTED_OS_HTTPS_PROXY or ""),
        _mask_api_key(_DETECTED_OS_SOCKS_PROXY or ""),
    )

    req = urllib.request.Request(url, data=payload_bytes, headers=headers, method=method.upper())

    try:
        with opener.open(req, timeout=timeout) as resp:
            raw = resp.read()
            status = getattr(resp, "status", resp.getcode())
            elapsed = int((time.time() - start) * 1000)
            logger.info(
                "[%s] %s %s 响应成功 HTTP_%s 耗时=%dms body=%dB",
                logger_tag,
                method,
                url,
                status,
                elapsed,
                len(raw),
            )
            try:
                data = json.loads(raw.decode("utf-8"))
            except Exception:
                data = None
            return data, None
    except Exception as exc:
        elapsed = int((time.time() - start) * 1000)
        err = classify_error(exc, url, elapsed)
        err["proxies_used"] = bool(proxies)
        err["http_proxy_configured"] = bool(HTTP_PROXY or _DETECTED_OS_HTTP_PROXY)
        err["https_proxy_configured"] = bool(HTTPS_PROXY or _DETECTED_OS_HTTPS_PROXY)
        err["socks_proxy_configured"] = bool(SOCKS_PROXY or _DETECTED_OS_SOCKS_PROXY)
        err["proxy_detection_note"] = (
            "macOS 下 Shadowrocket 端口不固定，自动从 scutil 读取；"
            "若端口检测不到，请手动勾选 Shadowrocket「设置 → 系统代理」，或在 secrets.local 固定 HTTP_PROXY 端口"
        )
        logger.warning(
            "[%s] %s %s 请求失败 耗时=%dms 分类=%s 原因=%s 建议=%s",
            logger_tag,
            method,
            url,
            elapsed,
            err["category"],
            err["message"],
            err["hint"],
        )
        return None, err

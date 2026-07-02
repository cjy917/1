"""对外 HTTP 请求：优先 secrets.local / 环境变量，其次读取 Windows 系统代理（Clash 等）。"""
import os
from pathlib import Path

import requests

from config import PROJECT_DIR

SECRETS_FILE = PROJECT_DIR / "secrets.local"


def _load_windows_system_proxy() -> str:
    if os.name != "nt":
        return ""
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        )
        enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
        if not enable:
            return ""
        server, _ = winreg.QueryValueEx(key, "ProxyServer")
        if not server:
            return ""
        server = server.strip()
        if ";" in server:
            server = server.split(";", 1)[0].strip()
        if "://" not in server:
            server = f"http://{server}"
        return server
    except Exception:
        return ""


def _load_external_proxy() -> str:
    proxy = os.environ.get("EXTERNAL_HTTP_PROXY", "").strip()
    if proxy:
        return proxy
    if SECRETS_FILE.exists():
        for line in SECRETS_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("EXTERNAL_HTTP_PROXY="):
                value = line.split("=", 1)[1].strip().strip('"').strip("'")
                if value:
                    return value
    return _load_windows_system_proxy()


_proxy = _load_external_proxy()
_session = requests.Session()
_session.trust_env = False
if _proxy:
    _session.proxies = {"http": _proxy, "https": _proxy}


def external_get(url: str, **kwargs):
    return _session.get(url, **kwargs)

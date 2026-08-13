#!/usr/bin/env python3
"""
OpenXiaoAI API 配置和基础工具
"""

import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlsplit


MAX_RESPONSE_BYTES = 1024 * 1024
MAX_ERROR_DETAIL_CHARS = 500


class ApiError(RuntimeError):
    """Base error for Open-XiaoAI Bridge requests."""


class ApiTransportError(ApiError):
    """The bridge could not be reached or returned an invalid HTTP response."""


class ApiResponseError(ApiError):
    """The bridge returned a valid response that reports an application failure."""


def get_api_config():
    """获取 API 配置"""
    base_url = os.environ.get("OPENXIAOAI_BASE_URL")
    if not base_url:
        raise RuntimeError(
            "OPENXIAOAI_BASE_URL is not set. Example: http://192.168.1.50:9092"
        )
    base_url = base_url.strip().rstrip("/")
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RuntimeError(
            "OPENXIAOAI_BASE_URL must be an http(s) URL, "
            "for example http://192.168.1.50:9092"
        )
    if parsed.username or parsed.password:
        raise RuntimeError("OPENXIAOAI_BASE_URL must not contain credentials")
    if parsed.query or parsed.fragment:
        raise RuntimeError("OPENXIAOAI_BASE_URL must not contain a query or fragment")
    try:
        port = parsed.port
    except ValueError as exc:
        raise RuntimeError("OPENXIAOAI_BASE_URL contains an invalid port") from exc
    if port is not None and not 1 <= port <= 65535:
        raise RuntimeError("OPENXIAOAI_BASE_URL contains an invalid port")
    return base_url


def read_json_response(response):
    """Read a bounded UTF-8 JSON response."""
    raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ApiTransportError("Open-XiaoAI Bridge response exceeds 1 MiB")
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ApiTransportError("Open-XiaoAI Bridge returned invalid JSON") from exc


def error_detail(result):
    """Return one bounded, single-line error detail without dumping the response."""
    if not isinstance(result, dict):
        return f"invalid response type: {type(result).__name__}"
    for key in ("error", "message", "detail"):
        value = result.get(key)
        if value not in (None, ""):
            detail = " ".join(str(value).splitlines())
            access_key = os.environ.get("DOUBAO_ACCESS_KEY")
            if access_key and len(access_key) >= 6:
                detail = detail.replace(access_key, "[REDACTED]")
            return detail[:MAX_ERROR_DETAIL_CHARS]
    return "response reported success=false"


def require_success(result, operation="request"):
    """Convert the Bridge's application-level result into a reliable CLI signal."""
    if not isinstance(result, dict) or result.get("success") is not True:
        raise ApiResponseError(
            f"Open-XiaoAI Bridge {operation} failed: {error_detail(result)}"
        )
    return result


def api_request(path, method="GET", data=None, headers=None, timeout=30):
    """发送 API 请求"""
    if not path.startswith("/"):
        raise ValueError("API path must start with a slash")
    if timeout <= 0:
        raise ValueError("API timeout must be greater than zero")
    base_url = get_api_config()
    full_url = f"{base_url}{path}"

    default_headers = {"Content-Type": "application/json"}
    if headers:
        default_headers.update(headers)

    req = urllib.request.Request(full_url, headers=default_headers, method=method)

    if data is not None:
        req.data = json.dumps(data).encode("utf-8")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return read_json_response(response)
    except urllib.error.HTTPError as e:
        error_msg = f"HTTP 错误: {e.code} - {e.reason}"
        try:
            raw_error = e.read(MAX_RESPONSE_BYTES + 1)
            if len(raw_error) <= MAX_RESPONSE_BYTES:
                error_body = json.loads(raw_error.decode("utf-8"))
                error_msg += f"; 详情: {error_detail(error_body)}"
        except (UnicodeDecodeError, json.JSONDecodeError):
            error_msg += "; 响应正文不是有效 JSON"
        raise ApiTransportError(error_msg) from e
    except urllib.error.URLError as e:
        raise ApiTransportError(
            f"无法连接 Open-XiaoAI Bridge: {full_url} ({e.reason})"
        ) from e


def check_health():
    """检查服务健康状态"""
    return require_success(api_request("/api/health"), "health check")


def get_status():
    """获取音箱状态"""
    return require_success(api_request("/api/status"), "status request")


def wakeup(silent=True):
    """唤醒小爱"""
    return require_success(
        api_request("/api/wakeup", method="POST", data={"silent": silent}),
        "wakeup request",
    )


def interrupt():
    """打断当前播放"""
    return require_success(
        api_request("/api/interrupt", method="POST"),
        "interrupt request",
    )

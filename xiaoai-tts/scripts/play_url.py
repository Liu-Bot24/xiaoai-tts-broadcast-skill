#!/usr/bin/env python3
"""
播放远程音频 URL
"""

import argparse
import os
import sys
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api_client import api_request, require_success
from cli_utils import positive_timeout_value


def play_url(url, blocking=False, timeout=60000):
    """
    播放远程音频 URL

    Args:
        url: 音频 URL
        blocking: 是否阻塞等待（默认 False）
        timeout: 超时时间（毫秒，默认 60000）
    """
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("音频 URL 必须是有效的 http(s) URL")
    if parsed.username or parsed.password:
        raise ValueError("音频 URL 不得包含用户名或密码")
    if timeout <= 0:
        raise ValueError("超时时间必须大于 0")
    data = {"url": url, "blocking": blocking, "timeout": timeout}

    request_timeout = max(30, int(timeout / 1000) + 10) if blocking else 30
    result = require_success(
        api_request(
            "/api/play/url",
            method="POST",
            data=data,
            timeout=request_timeout,
        ),
        "URL playback",
    )

    mode = "阻塞模式" if blocking else "非阻塞模式"
    print(f"OK: 已发送远程音频播放请求 [{mode}]")
    return result


def main():
    parser = argparse.ArgumentParser(description="播放远程音频 URL")
    parser.add_argument("url", help="音频 URL")
    parser.add_argument(
        "--blocking", action="store_true", help="阻塞等待播放完成（默认非阻塞）"
    )
    parser.add_argument(
        "--timeout",
        type=positive_timeout_value,
        default=60000,
        help="超时时间（毫秒，默认 60000）",
    )

    args = parser.parse_args()

    try:
        play_url(args.url, blocking=args.blocking, timeout=args.timeout)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
播放文字（小爱自带 TTS）
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api_client import api_request, require_success
from cli_utils import positive_timeout_value


def play_text(text, blocking=False, timeout=60000, quiet=False):
    """
    使用小爱自带 TTS 播放文字

    Args:
        text: 要播放的文字
        blocking: 是否阻塞等待（默认 False，文档错误更正）
        timeout: 超时时间（毫秒，默认 60000）
    """
    if timeout <= 0:
        raise ValueError("超时时间必须大于 0")
    data = {"text": text, "blocking": blocking, "timeout": timeout}

    request_timeout = max(30, int(timeout / 1000) + 10) if blocking else 30
    result = require_success(
        api_request(
            "/api/play/text",
            method="POST",
            data=data,
            timeout=request_timeout,
        ),
        "text playback",
    )

    if not quiet:
        mode = "阻塞模式" if blocking else "非阻塞模式"
        print(f"OK: 已发送文字播放请求 [{mode}]，{len(text)} 字")
    return result


def main():
    parser = argparse.ArgumentParser(description="小爱 TTS 播放文字")
    parser.add_argument("text", help="要播放的文字内容")
    parser.add_argument(
        "--blocking", action="store_true", help="阻塞等待播放完成（默认非阻塞）"
    )
    parser.add_argument("--no-blocking", action="store_true", help="非阻塞模式（默认）")
    parser.add_argument(
        "--timeout",
        type=positive_timeout_value,
        default=60000,
        help="超时时间（毫秒，默认 60000）",
    )

    args = parser.parse_args()

    # 默认非阻塞（blocking=False）
    blocking = args.blocking

    try:
        play_text(args.text, blocking=blocking, timeout=args.timeout)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

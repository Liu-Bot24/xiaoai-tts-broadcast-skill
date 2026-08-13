#!/usr/bin/env python3
"""
OpenXiaoAI 控制命令
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api_client import check_health, get_status, interrupt, wakeup


def response_data(result):
    data = result.get("data", {})
    if not isinstance(data, dict):
        raise TypeError("Bridge response data must be an object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenXiaoAI 控制命令")
    parser.add_argument(
        "command", choices=["health", "status", "wakeup", "interrupt"], help="控制命令"
    )
    parser.add_argument(
        "--silent", action="store_true", help="静默唤醒（不播放提示音）；默认有声"
    )
    parser.add_argument(
        "--no-silent", dest="silent", action="store_false", help="有声唤醒"
    )
    parser.set_defaults(silent=False)

    args = parser.parse_args()

    try:
        if args.command == "health":
            result = check_health()
            data = response_data(result)
            status = data.get("status", "unknown")
            speaker_ready = data.get("speaker_ready") is True

            status_ok = status == "healthy"
            print(f"{'OK' if status_ok else 'ERROR'}: 服务状态: {status}")
            ready_label = "是" if speaker_ready else "否"
            print(f"{'OK' if speaker_ready else 'ERROR'}: 音箱就绪: {ready_label}")
            if not status_ok or not speaker_ready:
                return 1

        elif args.command == "status":
            result = get_status()
            data = response_data(result)
            status = data.get("status", "unknown")

            status_map = {
                "playing": "播放中",
                "paused": "已暂停",
                "idle": "空闲",
            }
            print(status_map.get(status, f"未知状态: {status}"))

        elif args.command == "wakeup":
            silent = args.silent
            wakeup(silent=silent)
            mode = "静默" if silent else "有声"
            print(f"OK: 已唤醒小爱 [{mode}模式]")

        elif args.command == "interrupt":
            interrupt()
            print("OK: 已打断当前播放")

    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

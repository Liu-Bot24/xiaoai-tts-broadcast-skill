#!/usr/bin/env python3
"""
Stateful XiaoAI broadcast mode for chat channels such as Feishu.
"""

import argparse
import contextlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from broadcast_text import split_text, broadcast

try:
    import fcntl
except ImportError:  # pragma: no cover - non-Unix fallback
    fcntl = None


START_COMMANDS = {
    "/小爱播报",
    "/开始小爱播报",
    "/启动小爱播报",
    "/小爱朗读",
    "/开始播报",
    "/启动播报",
    "/播报模式",
    "/xiaoai-broadcast",
    "/xiaoai-broadcast-on",
    "启动小爱播报模式",
    "开启小爱播报模式",
    "进入小爱播报模式",
    "开始小爱播报模式",
    "启动小爱朗读模式",
    "开启小爱朗读模式",
    "进入小爱朗读模式",
    "启动播报模式",
    "开启播报模式",
    "进入播报模式",
    "开始播报模式",
}

STOP_COMMANDS = {
    "/退出小爱播报",
    "/停止小爱播报",
    "/结束小爱播报",
    "/退出播报",
    "/停止播报",
    "/结束播报",
    "/退出播报模式",
    "/停止播报模式",
    "/xiaoai-broadcast-off",
    "/stop-xiaoai-broadcast",
    "退出小爱播报模式",
    "停止小爱播报模式",
    "结束小爱播报模式",
    "关闭小爱播报模式",
    "退出小爱朗读模式",
    "停止小爱朗读模式",
    "结束小爱朗读模式",
    "退出播报模式",
    "停止播报模式",
    "结束播报模式",
    "关闭播报模式",
    "不用读了",
    "不要播报了",
}


def normalize_command(text: str) -> str:
    return " ".join((text or "").strip().split()).lower()


def default_state_path() -> Path:
    configured = os.environ.get("XIAOAI_TTS_STATE_PATH")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".xiaoai-tts" / "broadcast_state.json"


@contextlib.contextmanager
def locked_state_file(state_path: Path):
    state_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = state_path.with_suffix(state_path.suffix + ".lock")
    with open(lock_path, "w", encoding="utf-8") as lock:
        if fcntl:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def load_state(state_path: Path) -> dict:
    if not state_path.exists():
        return {"version": 1, "scopes": {}}
    try:
        with open(state_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("state root is not an object")
        data.setdefault("version", 1)
        data.setdefault("scopes", {})
        return data
    except Exception:
        backup = state_path.with_suffix(state_path.suffix + f".bad.{int(time.time())}")
        state_path.replace(backup)
        return {"version": 1, "scopes": {}}


def save_state(state_path: Path, data: dict) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=state_path.name + ".",
        suffix=".tmp",
        dir=str(state_path.parent),
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp_name, state_path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def get_scope_state(data: dict, scope: str) -> dict:
    scopes = data.setdefault("scopes", {})
    scope_state = scopes.setdefault(scope, {})
    scope_state.setdefault("enabled", False)
    scope_state.setdefault("message_count", 0)
    return scope_state


def set_mode(scope: str, enabled: bool, state_path: Path) -> dict:
    with locked_state_file(state_path):
        data = load_state(state_path)
        scope_state = get_scope_state(data, scope)
        now = time.time()
        scope_state["enabled"] = enabled
        scope_state["updated_at"] = now
        if enabled:
            scope_state["started_at"] = now
        else:
            scope_state["stopped_at"] = now
        save_state(state_path, data)
    return {"scope": scope, "enabled": enabled, "state_path": str(state_path)}


def get_mode(scope: str, state_path: Path) -> dict:
    with locked_state_file(state_path):
        data = load_state(state_path)
        scope_state = get_scope_state(data, scope)
        save_state(state_path, data)
    return {
        "scope": scope,
        "enabled": bool(scope_state.get("enabled")),
        "message_count": int(scope_state.get("message_count", 0)),
        "state_path": str(state_path),
    }


def note_forward(scope: str, state_path: Path) -> None:
    with locked_state_file(state_path):
        data = load_state(state_path)
        scope_state = get_scope_state(data, scope)
        scope_state["message_count"] = int(scope_state.get("message_count", 0)) + 1
        scope_state["last_forwarded_at"] = time.time()
        save_state(state_path, data)


def read_text(args) -> str:
    if getattr(args, "file", None):
        with open(args.file, "r", encoding="utf-8") as handle:
            return handle.read()
    if getattr(args, "stdin", False):
        return sys.stdin.read()
    if getattr(args, "text", None):
        return args.text
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def print_result(result: dict, json_output: bool = False) -> None:
    if json_output:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return

    action = result.get("action")
    if action == "mode_on":
        print(f"小爱播报模式已开启: scope={result['scope']}")
    elif action == "mode_off":
        print(f"小爱播报模式已关闭: scope={result['scope']}")
    elif action == "forwarded":
        print(f"已转发小爱播报: scope={result['scope']}, chunks={result.get('chunks')}")
    elif action == "ignored":
        print(f"未开启小爱播报模式，已忽略: scope={result['scope']}")
    elif action == "status":
        status = "on" if result.get("enabled") else "off"
        print(f"小爱播报模式状态: {status}, scope={result['scope']}")
    else:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))


def handle_text(args) -> int:
    state_path = default_state_path()
    text = read_text(args).strip()
    command = normalize_command(text)

    if not text:
        print_result(
            {"action": "ignored", "reason": "empty_text", "scope": args.scope},
            args.json,
        )
        return 0

    if command in {normalize_command(item) for item in START_COMMANDS}:
        result = set_mode(args.scope, True, state_path)
        result["action"] = "mode_on"
        print_result(result, args.json)
        return 0

    if command in {normalize_command(item) for item in STOP_COMMANDS}:
        result = set_mode(args.scope, False, state_path)
        result["action"] = "mode_off"
        print_result(result, args.json)
        return 0

    status = get_mode(args.scope, state_path)
    if not status["enabled"] and not args.force:
        result = {
            "action": "ignored",
            "reason": "mode_off",
            "scope": args.scope,
            "enabled": False,
        }
        print_result(result, args.json)
        return 0

    chunks = split_text(text, max_chars=args.max_chars)
    if args.dry_run:
        result = {
            "action": "forwarded",
            "dry_run": True,
            "scope": args.scope,
            "chunks": len(chunks),
            "chars": len(text),
        }
        print_result(result, args.json)
        return 0

    code = broadcast(text, args.max_chars, args.timeout, args.pause)
    if code == 0:
        note_forward(args.scope, state_path)
    result = {
        "action": "forwarded" if code == 0 else "failed",
        "scope": args.scope,
        "chunks": len(chunks),
        "chars": len(text),
        "exit_code": code,
    }
    print_result(result, args.json)
    return code


def mode_command(args) -> int:
    state_path = default_state_path()
    if args.mode == "on":
        result = set_mode(args.scope, True, state_path)
        result["action"] = "mode_on"
    elif args.mode == "off":
        result = set_mode(args.scope, False, state_path)
        result["action"] = "mode_off"
    else:
        result = get_mode(args.scope, state_path)
        result["action"] = "status"
    print_result(result, args.json)
    return 0


def add_text_args(parser):
    parser.add_argument("text", nargs="?", help="当前聊天消息正文")
    parser.add_argument("--file", "-f", help="从 UTF-8 文本文件读取正文")
    parser.add_argument("--stdin", action="store_true", help="从标准输入读取正文")
    parser.add_argument("--scope", default="default", help="播报状态作用域，建议使用飞书会话 ID")
    parser.add_argument("--max-chars", type=int, default=450, help="每段最大字数，默认 450")
    parser.add_argument("--timeout", type=int, default=600000, help="每段播放超时，毫秒，默认 600000")
    parser.add_argument("--pause", type=float, default=0.4, help="分段间隔秒数，默认 0.4")
    parser.add_argument("--force", action="store_true", help="忽略模式状态，强制播报")
    parser.add_argument("--dry-run", action="store_true", help="只判断动作，不实际播报")
    parser.add_argument("--json", action="store_true", help="输出 JSON")


def main():
    parser = argparse.ArgumentParser(description="小爱播报模式状态机")
    subparsers = parser.add_subparsers(dest="command")

    mode_parser = subparsers.add_parser("mode", help="开启、关闭或查看播报模式")
    mode_parser.add_argument("mode", choices=["on", "off", "status"])
    mode_parser.add_argument("--scope", default="default", help="播报状态作用域")
    mode_parser.add_argument("--json", action="store_true", help="输出 JSON")

    handle_parser = subparsers.add_parser("handle", help="处理一条聊天消息：识别开启/退出/转发/忽略")
    add_text_args(handle_parser)

    forward_parser = subparsers.add_parser("forward", help="按当前模式状态转发正文给小爱播报")
    add_text_args(forward_parser)

    args = parser.parse_args()
    if args.command == "mode":
        sys.exit(mode_command(args))
    if args.command in {"handle", "forward"}:
        sys.exit(handle_text(args))
    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()

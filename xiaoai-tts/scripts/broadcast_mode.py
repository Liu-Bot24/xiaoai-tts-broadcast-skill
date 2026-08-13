#!/usr/bin/env python3
"""Stateful XiaoAI broadcast mode for chat channels such as Feishu."""

import argparse
import contextlib
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from broadcast_text import broadcast, split_text
from cli_utils import (
    default_scope,
    max_chars_value,
    nonnegative_pause_value,
    positive_timeout_value,
    read_message_from_env,
)

fcntl: Any
try:
    import fcntl as fcntl_module
except ImportError:  # pragma: no cover - non-Unix fallback
    fcntl = None
else:
    fcntl = fcntl_module

msvcrt: Any
try:
    import msvcrt as msvcrt_module
except ImportError:  # pragma: no cover - non-Windows fallback
    msvcrt = None
else:
    msvcrt = msvcrt_module


DEFAULT_SCOPE = "feishu-default"
COMMAND_EDGE_CHARS = " \t\r\n.,;:!?，。；：！？、\"'“”‘’（）()[]【】<>《》"
WINDOWS_LOCK_TIMEOUT_SECONDS = 24 * 60 * 60


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
    "启动朗读模式",
    "开启朗读模式",
    "进入朗读模式",
    "下面这段用小爱读出来",
    "下面用小爱读出来",
    "后面用小爱读出来",
    "下面这段用小爱播报",
    "下面用小爱播报",
    "后面用小爱播报",
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
    "别读了",
    "不用播了",
    "取消播报模式",
    "取消小爱播报模式",
}


def normalize_command(text: str) -> str:
    value = (text or "").strip().lower().strip(COMMAND_EDGE_CHARS)
    value = re.sub(r"\s+", " ", value)
    return value.strip(COMMAND_EDGE_CHARS)


NORMALIZED_START_COMMANDS = {normalize_command(item) for item in START_COMMANDS}
NORMALIZED_STOP_COMMANDS = {normalize_command(item) for item in STOP_COMMANDS}


def command_matches(command: str, commands: set) -> bool:
    """Match only a complete normalized command, never a substring in prose."""
    return command in commands


def default_state_path() -> Path:
    configured = os.environ.get("XIAOAI_TTS_STATE_PATH")
    if configured:
        return Path(os.path.expandvars(configured)).expanduser()
    return Path.home() / ".xiaoai-tts" / "broadcast_state.json"


def lock_windows_file(lock) -> None:
    if not msvcrt:
        return
    deadline = time.monotonic() + WINDOWS_LOCK_TIMEOUT_SECONDS
    while True:
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            return
        except OSError:
            if time.monotonic() >= deadline:
                raise TimeoutError("timed out waiting for the broadcast lock")
            time.sleep(0.05)


@contextlib.contextmanager
def locked_file(lock_path: Path):
    """Hold a cross-process one-byte exclusive lock."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+b") as lock:
        lock.seek(0, os.SEEK_END)
        if lock.tell() == 0:
            lock.write(b"\0")
            lock.flush()
        lock.seek(0)
        if fcntl:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        elif msvcrt:
            lock_windows_file(lock)
        try:
            yield
        finally:
            if fcntl:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            elif msvcrt:
                lock.seek(0)
                with contextlib.suppress(OSError):
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


@contextlib.contextmanager
def locked_state_file(state_path: Path):
    with locked_file(state_path.with_suffix(state_path.suffix + ".lock")):
        yield


def scope_lock_path(state_path: Path, scope: str) -> Path:
    scope_digest = hashlib.sha256(scope.encode("utf-8")).hexdigest()
    return state_path.parent / f"{state_path.name}.locks" / f"{scope_digest}.lock"


@contextlib.contextmanager
def locked_scope(state_path: Path, scope: str):
    """Serialize all mode changes and broadcasts within one conversation."""
    with locked_file(scope_lock_path(state_path, scope)):
        yield


def new_state() -> dict:
    return {"version": 1, "scopes": {}}


def validate_state(data) -> dict:
    if not isinstance(data, dict):
        raise TypeError("state root is not an object")
    scopes = data.get("scopes", {})
    if not isinstance(scopes, dict):
        raise TypeError("state scopes is not an object")
    data.setdefault("version", 1)
    data["scopes"] = scopes
    return data


def load_state(state_path: Path, recover: bool = True) -> dict:
    if not state_path.exists():
        return new_state()
    try:
        with open(state_path, "r", encoding="utf-8") as handle:
            return validate_state(json.load(handle))
    except (json.JSONDecodeError, UnicodeError, ValueError, TypeError):
        if not recover:
            raise
        backup = state_path.with_suffix(state_path.suffix + f".bad.{time.time_ns()}")
        state_path.replace(backup)
        return new_state()


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
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, state_path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def get_scope_state(data: dict, scope: str) -> dict:
    scopes = data.setdefault("scopes", {})
    scope_state = scopes.setdefault(scope, {})
    if not isinstance(scope_state, dict):
        raise TypeError(f"state for scope {scope!r} is not an object")
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


def get_mode(scope: str, state_path: Path, read_only: bool = False) -> dict:
    if read_only:
        data = load_state(state_path, recover=False)
        scope_state = get_scope_state(data, scope)
    else:
        with locked_state_file(state_path):
            data = load_state(state_path)
            scope_state = get_scope_state(data, scope)
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
    selected_sources = sum(
        bool(value)
        for value in (
            getattr(args, "file", None),
            getattr(args, "stdin", False),
            getattr(args, "from_env", False),
            getattr(args, "text", None) is not None,
        )
    )
    if selected_sources > 1:
        raise ValueError("choose exactly one of text, --file, --stdin, or --from-env")
    if getattr(args, "file", None):
        with open(args.file, "r", encoding="utf-8") as handle:
            return handle.read()
    if getattr(args, "stdin", False):
        return sys.stdin.read()
    if getattr(args, "from_env", False):
        return read_message_from_env()
    if getattr(args, "text", None) is not None:
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
    elif action == "failed":
        print(f"小爱播报失败: {result.get('error', 'unknown error')}", file=sys.stderr)
    else:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))


def handle_text_locked(
    args, state_path: Path, text: str, process_commands: bool
) -> int:
    command = normalize_command(text)

    if process_commands and command_matches(command, NORMALIZED_START_COMMANDS):
        result = {"scope": args.scope, "enabled": True, "state_path": str(state_path)}
        if not args.dry_run:
            result = set_mode(args.scope, True, state_path)
        result["action"] = "mode_on"
        if args.dry_run:
            result["dry_run"] = True
        print_result(result, args.json)
        return 0

    if process_commands and command_matches(command, NORMALIZED_STOP_COMMANDS):
        result = {"scope": args.scope, "enabled": False, "state_path": str(state_path)}
        if not args.dry_run:
            result = set_mode(args.scope, False, state_path)
        result["action"] = "mode_off"
        if args.dry_run:
            result["dry_run"] = True
        print_result(result, args.json)
        return 0

    status = get_mode(args.scope, state_path, read_only=args.dry_run)
    if not status["enabled"] and not args.force:
        print_result(
            {
                "action": "ignored",
                "reason": "mode_off",
                "scope": args.scope,
                "enabled": False,
            },
            args.json,
        )
        return 0

    chunks = split_text(text, max_chars=args.max_chars)
    if args.dry_run:
        print_result(
            {
                "action": "forwarded",
                "dry_run": True,
                "scope": args.scope,
                "chunks": len(chunks),
                "chars": len(text),
            },
            args.json,
        )
        return 0

    code = broadcast(
        text,
        args.max_chars,
        args.timeout,
        args.pause,
        quiet=args.json,
    )
    if code == 0:
        note_forward(args.scope, state_path)
    result = {
        "action": "forwarded" if code == 0 else "failed",
        "scope": args.scope,
        "chunks": len(chunks),
        "chars": len(text),
        "exit_code": code,
    }
    if code != 0:
        result["error"] = "one or more chunks failed to play"
    print_result(result, args.json)
    return code


def handle_text(args, process_commands: bool = True) -> int:
    state_path = default_state_path()
    text = read_text(args)
    if not text.strip():
        print_result(
            {"action": "ignored", "reason": "empty_text", "scope": args.scope},
            args.json,
        )
        return 0

    if args.dry_run:
        return handle_text_locked(args, state_path, text, process_commands)
    with locked_scope(state_path, args.scope):
        return handle_text_locked(args, state_path, text, process_commands)


def mode_command(args) -> int:
    state_path = default_state_path()
    if args.mode == "status":
        result = get_mode(args.scope, state_path, read_only=True)
        result["action"] = "status"
    else:
        with locked_scope(state_path, args.scope):
            enabled = args.mode == "on"
            result = set_mode(args.scope, enabled, state_path)
            result["action"] = "mode_on" if enabled else "mode_off"
    print_result(result, args.json)
    return 0


def add_text_args(parser) -> None:
    parser.add_argument("text", nargs="?", help="当前聊天消息正文")
    parser.add_argument("--file", "-f", help="从 UTF-8 文本文件读取正文")
    parser.add_argument("--stdin", action="store_true", help="从标准输入读取正文")
    parser.add_argument(
        "--from-env",
        action="store_true",
        help="从 XIAOAI_TTS_MESSAGE 环境变量读取正文",
    )
    parser.add_argument(
        "--scope",
        default=default_scope(DEFAULT_SCOPE),
        help="播报状态作用域，建议使用飞书会话 ID",
    )
    parser.add_argument(
        "--max-chars",
        type=max_chars_value,
        default=450,
        help="每段最大字数，默认 450",
    )
    parser.add_argument(
        "--timeout",
        type=positive_timeout_value,
        default=600000,
        help="每段播放超时，毫秒，默认 600000",
    )
    parser.add_argument(
        "--pause",
        type=nonnegative_pause_value,
        default=0.4,
        help="分段间隔秒数，默认 0.4",
    )
    parser.add_argument("--force", action="store_true", help="忽略模式状态，强制播报")
    parser.add_argument("--dry-run", action="store_true", help="只判断动作，不实际播报")
    parser.add_argument("--json", action="store_true", help="输出 JSON")


def main() -> int:
    parser = argparse.ArgumentParser(description="小爱播报模式状态机")
    subparsers = parser.add_subparsers(dest="command")

    mode_parser = subparsers.add_parser("mode", help="开启、关闭或查看播报模式")
    mode_parser.add_argument("mode", choices=["on", "off", "status"])
    mode_parser.add_argument(
        "--scope",
        default=default_scope(DEFAULT_SCOPE),
        help="播报状态作用域",
    )
    mode_parser.add_argument("--json", action="store_true", help="输出 JSON")

    handle_parser = subparsers.add_parser(
        "handle", help="处理一条聊天消息：识别开启/退出/转发/忽略"
    )
    add_text_args(handle_parser)

    forward_parser = subparsers.add_parser(
        "forward", help="按当前模式状态转发正文给小爱播报"
    )
    add_text_args(forward_parser)

    args = parser.parse_args()
    try:
        if args.command == "mode":
            return mode_command(args)
        if args.command == "handle":
            return handle_text(args, process_commands=True)
        if args.command == "forward":
            return handle_text(args, process_commands=False)
    except (OSError, ValueError, TypeError) as exc:
        if getattr(args, "json", False):
            print_result({"action": "failed", "error": str(exc)}, True)
        else:
            print(f"错误: {exc}", file=sys.stderr)
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

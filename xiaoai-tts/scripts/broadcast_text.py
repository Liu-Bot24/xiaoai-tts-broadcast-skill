#!/usr/bin/env python3
"""
Broadcast long text with XiaoAI native TTS.
"""

import argparse
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from play_text import play_text


BREAK_PATTERN = re.compile(r"([。！？!?；;：:\n]+)")


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line).strip()


def split_long_piece(piece: str, max_chars: int) -> list[str]:
    return [piece[i : i + max_chars].strip() for i in range(0, len(piece), max_chars) if piece[i : i + max_chars].strip()]


def split_text(text: str, max_chars: int) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []

    parts = BREAK_PATTERN.split(text)
    sentences: list[str] = []
    current = ""
    for part in parts:
        if not part:
            continue
        current += part
        if BREAK_PATTERN.fullmatch(part):
            sentences.append(current.strip())
            current = ""
    if current.strip():
        sentences.append(current.strip())

    chunks: list[str] = []
    current_chunk = ""
    for sentence in sentences:
        if len(sentence) > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            chunks.extend(split_long_piece(sentence, max_chars))
            continue

        candidate = f"{current_chunk}{sentence}" if not current_chunk else f"{current_chunk}\n{sentence}"
        if len(candidate) <= max_chars:
            current_chunk = candidate
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def read_text(args) -> str:
    if args.file:
        with open(args.file, "r", encoding="utf-8") as handle:
            return handle.read()
    if args.stdin:
        return sys.stdin.read()
    if args.text:
        return args.text
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def broadcast(text: str, max_chars: int, timeout: int, pause: float) -> int:
    chunks = split_text(text, max_chars=max_chars)
    if not chunks:
        print("错误: 没有可播报的文本", file=sys.stderr)
        return 1

    print(f"准备播报 {len(chunks)} 段文本")
    for index, chunk in enumerate(chunks, start=1):
        print(f"播报第 {index}/{len(chunks)} 段，{len(chunk)} 字")
        result = play_text(chunk, blocking=True, timeout=timeout)
        if not result.get("success"):
            print(f"第 {index} 段播报失败: {result}", file=sys.stderr)
            return 1
        if index < len(chunks) and pause > 0:
            time.sleep(pause)

    print("播报完成")
    return 0


def main():
    parser = argparse.ArgumentParser(description="小爱长文本分段播报")
    parser.add_argument("text", nargs="?", help="要播报的文本；长文本建议使用 --file 或 stdin")
    parser.add_argument("--file", "-f", help="从 UTF-8 文本文件读取内容")
    parser.add_argument("--stdin", action="store_true", help="从标准输入读取内容")
    parser.add_argument("--max-chars", type=int, default=450, help="每段最大字数，默认 450")
    parser.add_argument("--timeout", type=int, default=600000, help="每段播放超时时间，毫秒，默认 600000")
    parser.add_argument("--pause", type=float, default=0.4, help="分段之间停顿秒数，默认 0.4")
    args = parser.parse_args()

    if args.max_chars < 50:
        print("错误: --max-chars 不能小于 50", file=sys.stderr)
        sys.exit(1)

    text = read_text(args)
    sys.exit(broadcast(text, args.max_chars, args.timeout, args.pause))


if __name__ == "__main__":
    main()

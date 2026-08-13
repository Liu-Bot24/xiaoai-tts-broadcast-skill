#!/usr/bin/env python3
"""
火山 TTS 语音合成脚本
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api_client import api_request, require_success
from cli_utils import positive_timeout_value, speed_value


# 默认音色（2.0 高质量）
DEFAULT_SPEAKER = None


def tts_doubao(
    text,
    speaker=None,
    speed=1.0,
    emotion=None,
    context_texts=None,
    app_id=None,
    access_key=None,
    resource_id=None,
    blocking=False,
    timeout=60000,
):
    """
    使用火山 TTS 播放文字

    Args:
        text: 要合成的文本
        speaker: 音色 ID（默认 zh_female_vv_uranus_bigtts）
        speed: 语速 0.8-2.0（默认 1.0）
        emotion: 情感参数（仅多情感音色支持）
        context_texts: 上下文指令（仅 2.0 音色支持）
        app_id: 火山 App ID（可选，默认从环境变量读取）
        access_key: 火山 Access Key（可选，默认从环境变量读取）
        resource_id: 资源 ID（可选，自动检测）
        blocking: 是否阻塞等待（默认 False，文档错误更正）
    """
    if not 0.8 <= speed <= 2.0:
        raise ValueError("语速必须在 0.8-2.0 之间")
    if timeout <= 0:
        raise ValueError("请求超时时间必须大于 0")

    data = {
        "text": text,
        "speaker_id": speaker or DEFAULT_SPEAKER,
        "speed": speed,
        "blocking": blocking,
    }

    # 可选参数
    if emotion:
        data["emotion"] = emotion
    if context_texts:
        data["context_texts"] = (
            context_texts if isinstance(context_texts, list) else [context_texts]
        )
    if app_id:
        data["app_id"] = app_id
    if access_key:
        data["access_key"] = access_key
    if resource_id:
        data["resource_id"] = resource_id

    request_timeout = max(30, int(timeout / 1000) + 10) if blocking else 30
    result = require_success(
        api_request(
            "/api/tts/doubao",
            method="POST",
            data=data,
            timeout=request_timeout,
        ),
        "Doubao TTS playback",
    )

    mode = "阻塞模式" if blocking else "非阻塞模式"
    speaker_info = f"[{speaker or DEFAULT_SPEAKER or '服务端默认'}]"
    emotion_info = f"[{emotion}]" if emotion else ""
    print(f"OK: 火山 TTS [{mode}]{speaker_info}{emotion_info}，{len(text)} 字")
    return result


def main():
    parser = argparse.ArgumentParser(description="火山 TTS 语音合成")
    parser.add_argument("text", help="要合成的文本")
    parser.add_argument(
        "--speaker",
        "-s",
        default=DEFAULT_SPEAKER,
        help=f"音色 ID（默认: {DEFAULT_SPEAKER}）",
    )
    parser.add_argument(
        "--speed", type=speed_value, default=1.0, help="语速 0.8-2.0（默认 1.0）"
    )
    parser.add_argument(
        "--emotion", "-e", help="情感参数（如: happy, sad, angry, lovey-dovey）"
    )
    parser.add_argument("--context", "-c", help="上下文指令（仅 2.0 音色支持）")
    parser.add_argument(
        "--blocking", action="store_true", help="阻塞等待播放完成（默认非阻塞）"
    )
    parser.add_argument(
        "--timeout",
        type=positive_timeout_value,
        default=60000,
        help="请求超时时间（毫秒，默认 60000）",
    )

    args = parser.parse_args()

    try:
        context = args.context
        if context:
            context = [context]

        tts_doubao(
            text=args.text,
            speaker=args.speaker,
            speed=args.speed,
            emotion=args.emotion,
            context_texts=context,
            app_id=os.environ.get("DOUBAO_APP_ID"),
            access_key=os.environ.get("DOUBAO_ACCESS_KEY"),
            blocking=args.blocking,
            timeout=args.timeout,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

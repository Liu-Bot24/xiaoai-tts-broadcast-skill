#!/usr/bin/env python3
"""
上传并播放本地音频文件
"""

import argparse
import http.client
import json
import mimetypes
import os
import sys
import uuid
from urllib.parse import quote, urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api_client import MAX_RESPONSE_BYTES, get_api_config, require_success


UPLOAD_CHUNK_BYTES = 64 * 1024


def play_file(file_path, blocking=False):
    """
    上传并播放本地音频文件

    Args:
        file_path: 本地音频文件路径
        blocking: 是否阻塞等待（默认 False）
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"文件不存在或不是普通文件: {file_path}")

    base_url = get_api_config()
    full_url = f"{base_url}/api/play/file?blocking={'true' if blocking else 'false'}"

    boundary = f"----xiaoai-tts-{uuid.uuid4().hex}"
    filename = os.path.basename(file_path)
    safe_filename = (
        filename.replace("\\", "_")
        .replace('"', "_")
        .replace("\r", "_")
        .replace("\n", "_")
    )
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    prefix = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{safe_filename}"; '
        f"filename*=UTF-8''{quote(filename, safe='')}\r\n"
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8")
    suffix = f"\r\n--{boundary}--\r\n".encode()
    content_length = len(prefix) + os.path.getsize(file_path) + len(suffix)

    parsed = urlsplit(full_url)
    connection_class = (
        http.client.HTTPSConnection
        if parsed.scheme == "https"
        else http.client.HTTPConnection
    )
    connection = connection_class(parsed.hostname, parsed.port, timeout=60)
    request_target = parsed.path or "/"
    if parsed.query:
        request_target += f"?{parsed.query}"

    try:
        connection.putrequest("POST", request_target)
        connection.putheader(
            "Content-Type", f"multipart/form-data; boundary={boundary}"
        )
        connection.putheader("Content-Length", str(content_length))
        connection.endheaders()
        connection.send(prefix)
        with open(file_path, "rb") as handle:
            while True:
                chunk = handle.read(UPLOAD_CHUNK_BYTES)
                if not chunk:
                    break
                connection.send(chunk)
        connection.send(suffix)

        response = connection.getresponse()
        raw_response = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw_response) > MAX_RESPONSE_BYTES:
            raise RuntimeError("Open-XiaoAI Bridge response exceeds 1 MiB")
        if response.status >= 400:
            raise RuntimeError(f"HTTP 错误: {response.status} - {response.reason}")
        try:
            result = json.loads(raw_response.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("Open-XiaoAI Bridge returned invalid JSON") from exc
        require_success(result, "file playback")

        mode = "阻塞模式" if blocking else "非阻塞模式"
        print(f"OK: 已上传音频文件并请求播放 [{mode}]")
        return result
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="上传并播放本地音频文件")
    parser.add_argument("file", help="本地音频文件路径")
    parser.add_argument(
        "--blocking", action="store_true", help="阻塞等待播放完成（默认非阻塞）"
    )

    args = parser.parse_args()

    try:
        play_file(args.file, blocking=args.blocking)
    except (
        http.client.HTTPException,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "xiaoai-tts" / "tools" / "xiaoai-tts"
ROOT_TOOL = ROOT / "tools" / "xiaoai-tts"
ROOT_CMD = ROOT / "tools" / "xiaoai-tts.cmd"
NESTED_CMD = ROOT / "xiaoai-tts" / "tools" / "xiaoai-tts.cmd"
ROOT_PS1 = ROOT / "tools" / "xiaoai-tts.ps1"
NESTED_PS1 = ROOT / "xiaoai-tts" / "tools" / "xiaoai-tts.ps1"
SCRIPTS = ROOT / "xiaoai-tts" / "scripts"

sys.path.insert(0, str(SCRIPTS))
import play_file as play_file_module  # noqa: E402


def tool_env(**overrides):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update({key: str(value) for key, value in overrides.items()})
    return env


def run_tool(args, *, env=None, timeout=10):
    return subprocess.run(
        [sys.executable, "-B", str(TOOL), *args],
        cwd=ROOT,
        env=env or tool_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


class FakeBridge:
    def __init__(self, responder, request_delay=0):
        self.responder = responder
        self.request_delay = request_delay
        self.requests = []
        self.active = 0
        self.max_active = 0
        self.first_request = threading.Event()
        self._lock = threading.Lock()
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            def _handle(self):
                length = int(self.headers.get("Content-Length", "0"))
                raw_body = self.rfile.read(length) if length else b""
                try:
                    body = json.loads(raw_body.decode("utf-8")) if raw_body else None
                except (UnicodeDecodeError, json.JSONDecodeError):
                    body = raw_body

                with bridge._lock:
                    bridge.active += 1
                    bridge.max_active = max(bridge.max_active, bridge.active)
                    bridge.requests.append((self.command, self.path, body))
                bridge.first_request.set()

                try:
                    if bridge.request_delay:
                        time.sleep(bridge.request_delay)
                    status, payload = bridge.responder(self.command, self.path, body)
                    encoded = json.dumps(payload).encode("utf-8")
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(encoded)))
                    self.end_headers()
                    self.wfile.write(encoded)
                finally:
                    with bridge._lock:
                        bridge.active -= 1

            do_GET = _handle
            do_POST = _handle

            def log_message(self, *_args):
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def base_url(self):
        return f"http://127.0.0.1:{self.server.server_port}"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_exc_info):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


class SecurityContractTests(unittest.TestCase):
    def test_skill_uses_structured_environment_instead_of_shell_interpolation(self):
        paths = (ROOT / "SKILL.md", ROOT / "xiaoai-tts" / "SKILL.md")
        for path in paths:
            text = path.read_text(encoding="utf-8")
            self.assertIn("--from-env", text, path)
            self.assertIn("XIAOAI_TTS_MESSAGE", text, path)
            self.assertNotIn('handle "<用户原文>"', text, path)
        self.assertEqual(
            paths[0].read_text(encoding="utf-8"),
            paths[1].read_text(encoding="utf-8"),
        )

    def test_doubao_credentials_are_not_cli_arguments(self):
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPTS / "tts_doubao.py"), "--help"],
            cwd=ROOT,
            env=tool_env(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertNotIn("--access-key", result.stdout)
        self.assertNotIn("--app-id", result.stdout)

    def test_cmd_launchers_are_not_shipped(self):
        for launcher in (ROOT_CMD, NESTED_CMD):
            self.assertFalse(
                launcher.exists(),
                f"batch files reparse arbitrary arguments before their body runs: {launcher}",
            )

    def test_root_python_launcher_preserves_exit_code(self):
        result = subprocess.run(
            [sys.executable, "-B", str(ROOT_TOOL), "definitely-invalid-command"],
            cwd=ROOT,
            env=tool_env(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
        self.assertNotEqual(0, result.returncode, result.stdout + result.stderr)

    @unittest.skipUnless(sys.platform == "win32", "Windows launcher regression")
    def test_powershell_launchers_preserve_arguments_and_exit_codes(self):
        pwsh = shutil.which("pwsh") or shutil.which("powershell")
        if not pwsh:
            self.skipTest("PowerShell is not installed")
        payload = '普通正文" & echo PS_INJECTION_MARKER & rem "'
        with tempfile.TemporaryDirectory() as temp_dir:
            env = tool_env(
                XIAOAI_TTS_STATE_PATH=Path(temp_dir) / "state.json",
            )
            for launcher in (ROOT_PS1, NESTED_PS1):
                result = subprocess.run(
                    [
                        pwsh,
                        "-NoProfile",
                        "-File",
                        str(launcher),
                        "handle",
                        payload,
                        "--dry-run",
                        "--json",
                    ],
                    cwd=ROOT,
                    env=env,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=10,
                    check=False,
                )
                output = result.stdout + result.stderr
                self.assertNotIn("PS_INJECTION_MARKER", output, launcher)
                self.assertEqual(0, result.returncode, output)
                self.assertEqual("ignored", json.loads(result.stdout)["action"])

                invalid = subprocess.run(
                    [
                        pwsh,
                        "-NoProfile",
                        "-File",
                        str(launcher),
                        "definitely-invalid-command",
                    ],
                    cwd=ROOT,
                    env=env,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=10,
                    check=False,
                )
                self.assertNotEqual(
                    0, invalid.returncode, invalid.stdout + invalid.stderr
                )


class ApiSemanticsTests(unittest.TestCase):
    def test_application_failures_return_nonzero(self):
        def fail(_method, _path, _body):
            return 200, {"success": False, "error": "synthetic failure"}

        with FakeBridge(fail) as bridge, tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "sample.mp3"
            audio_path.write_bytes(b"not-real-audio")
            env = tool_env(
                OPENXIAOAI_BASE_URL=bridge.base_url,
                XIAOAI_TTS_STATE_PATH=Path(temp_dir) / "state.json",
            )
            cases = (
                ["health"],
                ["status"],
                ["wakeup"],
                ["text", "hello"],
                ["url", "https://example.invalid/audio.mp3"],
                ["file", str(audio_path)],
                ["tts", "hello"],
            )
            for args in cases:
                with self.subTest(command=args[0]):
                    result = run_tool(args, env=env)
                    self.assertNotEqual(
                        0, result.returncode, result.stdout + result.stderr
                    )

    def test_unhealthy_health_payload_returns_nonzero(self):
        def unhealthy(_method, _path, _body):
            return 200, {
                "success": True,
                "data": {"status": "unhealthy", "speaker_ready": False},
            }

        with FakeBridge(unhealthy) as bridge:
            result = run_tool(
                ["health"],
                env=tool_env(OPENXIAOAI_BASE_URL=bridge.base_url),
            )
        self.assertNotEqual(0, result.returncode, result.stdout + result.stderr)

    def test_doubao_business_failure_falls_back_to_native_tts(self):
        def responder(_method, path, _body):
            if path == "/api/tts/doubao":
                return 200, {"success": False, "error": "doubao unavailable"}
            return 200, {"success": True}

        with FakeBridge(responder) as bridge:
            result = run_tool(
                ["tts", "hello"],
                env=tool_env(OPENXIAOAI_BASE_URL=bridge.base_url),
            )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual(
            ["/api/tts/doubao", "/api/play/text"],
            [request[1] for request in bridge.requests],
        )

    def test_tts_timeout_is_accepted_by_doubao_path(self):
        def succeed(_method, _path, _body):
            return 200, {"success": True}

        with FakeBridge(succeed) as bridge:
            result = run_tool(
                ["tts", "hello", "--timeout", "12345"],
                env=tool_env(OPENXIAOAI_BASE_URL=bridge.base_url),
            )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual(["/api/tts/doubao"], [item[1] for item in bridge.requests])

    def test_interrupt_is_exposed_by_public_cli(self):
        def succeed(_method, _path, _body):
            return 200, {"success": True}

        with FakeBridge(succeed) as bridge:
            result = run_tool(
                ["interrupt"],
                env=tool_env(OPENXIAOAI_BASE_URL=bridge.base_url),
            )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual(["/api/interrupt"], [item[1] for item in bridge.requests])

    def test_user_content_and_access_key_are_not_logged(self):
        content_marker = "PRIVATE_CONTENT_MARKER"
        access_key = "PRIVATE_ACCESS_KEY_123456"

        def succeed(_method, _path, _body):
            return 200, {"success": True}

        with FakeBridge(succeed) as bridge:
            env = tool_env(
                OPENXIAOAI_BASE_URL=bridge.base_url,
                DOUBAO_ACCESS_KEY=access_key,
            )
            text_result = run_tool(["text", content_marker], env=env)
            tts_result = run_tool(["tts", content_marker], env=env)
            url_result = run_tool(
                ["url", f"https://example.invalid/{content_marker}.mp3"], env=env
            )

        for result in (text_result, tts_result, url_result):
            output = result.stdout + result.stderr
            self.assertEqual(0, result.returncode, output)
            self.assertNotIn(content_marker, output)
            self.assertNotIn(access_key, output)

    def test_bridge_errors_redact_access_key(self):
        access_key = "PRIVATE_ACCESS_KEY_123456"

        def fail(_method, _path, _body):
            return 200, {"success": False, "error": f"rejected {access_key}"}

        with FakeBridge(fail) as bridge:
            result = run_tool(
                ["tts", "hello"],
                env=tool_env(
                    OPENXIAOAI_BASE_URL=bridge.base_url,
                    DOUBAO_ACCESS_KEY=access_key,
                ),
            )
        self.assertNotEqual(0, result.returncode)
        self.assertNotIn(access_key, result.stdout + result.stderr)

    def test_invalid_tts_numbers_fail_before_fallback(self):
        for args in (
            ["tts", "hello", "--timeout", "0"],
            ["tts", "hello", "--speed", "3"],
        ):
            with self.subTest(args=args):
                result = run_tool(args)
                self.assertNotEqual(0, result.returncode)
                self.assertNotIn("Traceback", result.stderr)
                self.assertNotIn("回退", result.stderr)


class BroadcastModeTests(unittest.TestCase):
    def test_dry_run_does_not_create_or_modify_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "state.json"
            env = tool_env(XIAOAI_TTS_STATE_PATH=state_path)
            result = run_tool(
                ["handle", "普通消息", "--dry-run", "--json"],
                env=env,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertFalse(state_path.exists())
            self.assertEqual([], list(Path(temp_dir).iterdir()))

    def test_command_matching_requires_the_complete_normalized_message(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "state.json"
            env = tool_env(XIAOAI_TTS_STATE_PATH=state_path)
            run_tool(["mode", "on", "--scope", "audit"], env=env)

            negative = run_tool(
                [
                    "handle",
                    "他说‘不用读了’只是台词",
                    "--scope",
                    "audit",
                    "--dry-run",
                    "--json",
                ],
                env=env,
            )
            positive = run_tool(
                [
                    "handle",
                    "退出播报模式。",
                    "--scope",
                    "audit",
                    "--dry-run",
                    "--json",
                ],
                env=env,
            )

            self.assertEqual("forwarded", json.loads(negative.stdout)["action"])
            self.assertEqual("mode_off", json.loads(positive.stdout)["action"])

    def test_structured_environment_input(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env = tool_env(
                XIAOAI_TTS_STATE_PATH=Path(temp_dir) / "state.json",
                XIAOAI_TTS_MESSAGE='正文"; Write-Output INJECTION_MARKER; #',
                XIAOAI_TTS_SCOPE="safe-scope",
            )
            result = run_tool(
                ["handle", "--from-env", "--dry-run", "--json"],
                env=env,
            )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("safe-scope", payload["scope"])
        self.assertEqual("ignored", payload["action"])

    def test_json_mode_emits_one_json_document_for_real_forward(self):
        def succeed(_method, _path, _body):
            return 200, {"success": True}

        with FakeBridge(succeed) as bridge, tempfile.TemporaryDirectory() as temp_dir:
            env = tool_env(
                OPENXIAOAI_BASE_URL=bridge.base_url,
                XIAOAI_TTS_STATE_PATH=Path(temp_dir) / "state.json",
            )
            result = run_tool(
                ["handle", "hello", "--force", "--pause", "0", "--json"],
                env=env,
            )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("forwarded", payload["action"])

    def test_invalid_max_chars_is_reported_without_traceback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_tool(
                ["handle", "hello", "--force", "--max-chars", "0"],
                env=tool_env(
                    XIAOAI_TTS_STATE_PATH=Path(temp_dir) / "state.json",
                ),
            )
        self.assertNotEqual(0, result.returncode)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("max-chars", result.stderr.lower())

    def test_same_scope_broadcasts_are_serialized(self):
        def succeed(_method, _path, _body):
            return 200, {"success": True}

        with FakeBridge(
            succeed, request_delay=0.2
        ) as bridge, tempfile.TemporaryDirectory() as temp_dir:
            env = tool_env(
                OPENXIAOAI_BASE_URL=bridge.base_url,
                XIAOAI_TTS_STATE_PATH=Path(temp_dir) / "state.json",
            )
            enabled = run_tool(["mode", "on", "--scope", "same-chat"], env=env)
            self.assertEqual(0, enabled.returncode, enabled.stdout + enabled.stderr)

            def command(character):
                return [
                    sys.executable,
                    "-B",
                    str(TOOL),
                    "handle",
                    character * 70 + "。",
                    "--scope",
                    "same-chat",
                    "--max-chars",
                    "50",
                    "--pause",
                    "0",
                ]

            first = subprocess.Popen(
                command("A"),
                cwd=ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertTrue(
                bridge.first_request.wait(3), "first broadcast never reached bridge"
            )
            second = subprocess.Popen(
                command("B"),
                cwd=ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            first_output = first.communicate(timeout=10)
            second_output = second.communicate(timeout=10)

        self.assertEqual(0, first.returncode, "".join(first_output))
        self.assertEqual(0, second.returncode, "".join(second_output))
        self.assertEqual(1, bridge.max_active)
        initials = [request[2]["text"][0] for request in bridge.requests]
        self.assertIn(initials, (["A", "A", "B", "B"], ["B", "B", "A", "A"]))

    def test_stop_cannot_commit_between_mode_check_and_playback(self):
        def succeed(_method, _path, _body):
            return 200, {"success": True}

        with contextlib.ExitStack() as stack:
            bridge = stack.enter_context(FakeBridge(succeed, request_delay=0.4))
            temp_dir = stack.enter_context(tempfile.TemporaryDirectory())
            env = tool_env(
                OPENXIAOAI_BASE_URL=bridge.base_url,
                XIAOAI_TTS_STATE_PATH=Path(temp_dir) / "state.json",
            )
            enabled = run_tool(["mode", "on", "--scope", "ordered-chat"], env=env)
            self.assertEqual(0, enabled.returncode, enabled.stdout + enabled.stderr)

            playback = subprocess.Popen(
                [
                    sys.executable,
                    "-B",
                    str(TOOL),
                    "handle",
                    "first message",
                    "--scope",
                    "ordered-chat",
                    "--pause",
                    "0",
                ],
                cwd=ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertTrue(
                bridge.first_request.wait(3), "playback never reached bridge"
            )
            stop = subprocess.Popen(
                [
                    sys.executable,
                    "-B",
                    str(TOOL),
                    "handle",
                    "退出播报模式",
                    "--scope",
                    "ordered-chat",
                ],
                cwd=ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            time.sleep(0.1)
            self.assertIsNone(
                stop.poll(), "stop bypassed the in-flight scope transaction"
            )
            playback_output = playback.communicate(timeout=10)
            stop_output = stop.communicate(timeout=10)
            status = run_tool(
                ["mode", "status", "--scope", "ordered-chat", "--json"], env=env
            )

        self.assertEqual(0, playback.returncode, "".join(playback_output))
        self.assertEqual(0, stop.returncode, "".join(stop_output))
        self.assertFalse(json.loads(status.stdout)["enabled"])


class FileUploadTests(unittest.TestCase):
    def test_file_upload_reads_in_bounded_chunks(self):
        total_size = play_file_module.UPLOAD_CHUNK_BYTES * 2 + 7

        class TrackingFile:
            def __init__(self):
                self.remaining = total_size
                self.read_sizes = []

            def __enter__(self):
                return self

            def __exit__(self, *_exc_info):
                return False

            def read(self, size=-1):
                self.read_sizes.append(size)
                if size <= 0:
                    raise AssertionError("upload attempted an unbounded read")
                count = min(size, self.remaining)
                self.remaining -= count
                return b"x" * count

        class FakeResponse:
            status = 200
            reason = "OK"

            @staticmethod
            def read(size=-1):
                if size <= 0:
                    raise AssertionError("response attempted an unbounded read")
                return b'{"success": true}'

        class FakeConnection:
            def __init__(self):
                self.sent_sizes = []

            def putrequest(self, *_args):
                return None

            def putheader(self, *_args):
                return None

            def endheaders(self):
                return None

            def send(self, data):
                self.sent_sizes.append(len(data))

            def getresponse(self):
                return FakeResponse()

            def close(self):
                return None

        tracking_file = TrackingFile()
        connection = FakeConnection()
        with contextlib.ExitStack() as stack:
            stack.enter_context(
                mock.patch.object(play_file_module.os.path, "isfile", return_value=True)
            )
            stack.enter_context(
                mock.patch.object(
                    play_file_module.os.path, "getsize", return_value=total_size
                )
            )
            stack.enter_context(
                mock.patch.object(
                    play_file_module,
                    "get_api_config",
                    return_value="http://127.0.0.1:9092",
                )
            )
            stack.enter_context(
                mock.patch.object(
                    play_file_module.mimetypes,
                    "guess_type",
                    return_value=("audio/mpeg", None),
                )
            )
            stack.enter_context(
                mock.patch.object(
                    play_file_module.http.client,
                    "HTTPConnection",
                    return_value=connection,
                )
            )
            stack.enter_context(mock.patch("builtins.open", return_value=tracking_file))
            stack.enter_context(mock.patch("sys.stdout"))
            result = play_file_module.play_file("sample.mp3")

        self.assertTrue(result["success"])
        self.assertTrue(tracking_file.read_sizes)
        self.assertEqual(
            {play_file_module.UPLOAD_CHUNK_BYTES}, set(tracking_file.read_sizes)
        )


if __name__ == "__main__":
    unittest.main()

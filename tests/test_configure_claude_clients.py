"""Actual Claude CLI configuration and Messages requests using only loopback fixtures."""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.parse import urlsplit

from test_configure_claude import setup


@unittest.skipUnless(os.environ.get("TOKENLAB_INSTALLED_CLIENT_TESTS") == "1",
                     "Set TOKENLAB_INSTALLED_CLIENT_TESTS=1 for the pinned installed-client check")
class InstalledClaudeAuthenticationTests(unittest.TestCase):
    def test_actual_client_authentication_preserves_existing_account_and_permission_settings(self):
        executable = shutil.which("claude")
        self.assertIsNotNone(executable)
        self.assertEqual(setup.detect_claude(executable)[1], "2.1.263")
        with tempfile.TemporaryDirectory(prefix="tokenlab-claude-client-") as directory:
            root = Path(directory)
            config = root / "claude"
            config.mkdir()
            workspace = root / "project"
            workspace.mkdir()
            original = json.dumps({"model": "claude-haiku-4-5", "permissions": {"defaultMode": "plan"},
                                   "env": {"ANTHROPIC_API_KEY": "sk-existing-fixture"}}).encode()
            account = b'{"fixtureExistingAccount":"not-a-token"}'
            (config / "settings.json").write_bytes(original)
            (config / ".credentials.json").write_bytes(account)
            environment = {key: os.environ[key] for key in
                           ("PATH", "SYSTEMROOT", "SystemRoot", "WINDIR", "COMSPEC", "PATHEXT") if key in os.environ}
            environment.update(HOME=directory, USERPROFILE=directory, CLAUDE_CONFIG_DIR=str(config),
                               APPDATA=directory, LOCALAPPDATA=directory, TMPDIR=directory,
                               TMP=directory, TEMP=directory, DISABLE_AUTOUPDATER="1",
                               CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1")
            helper = [sys.executable, setup.__file__, "--claude-bin", executable,
                      "--claude-config-dir", str(config)]
            configuration = ["--model", "claude-sonnet-5"]

            def run(command):
                return subprocess.run(command, cwd=workspace, env=environment, capture_output=True,
                                      text=True, timeout=30)

            preview = run([*helper, *configuration])
            self.assertEqual(preview.returncode, 0, preview.stderr)
            launcher = config / "tokenlab-claude.py"
            self.assertFalse(launcher.exists())
            applied = run([*helper, *configuration, "--apply"])
            self.assertEqual(applied.returncode, 0, applied.stderr)
            missing = run([sys.executable, str(launcher), "--auth-status"])
            self.assertEqual(missing.returncode, 1)
            self.assertIn("Set a complete TOKENLAB_API_KEY", missing.stderr)
            token = "sk-tokenlab-client-fixture-not-a-real-key"
            environment["TOKENLAB_API_KEY"] = token
            status = run([sys.executable, str(launcher), "--auth-status"])
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIn("session Bearer credential", status.stdout)
            self.assertNotIn(token, status.stdout + status.stderr)
            self.assertEqual((config / "settings.json").read_bytes(), original)
            self.assertEqual((config / ".credentials.json").read_bytes(), account)
            for file in root.rglob("*"):
                if file.is_file():
                    self.assertNotIn(token.encode(), file.read_bytes(), file.name)
            restored = run([*helper, "--restore", "--apply"])
            self.assertEqual(restored.returncode, 0, restored.stderr)
            self.assertFalse(launcher.exists())
            self.assertEqual((config / "settings.json").read_bytes(), original)
            self.assertEqual((config / ".credentials.json").read_bytes(), account)

    def test_actual_launcher_completes_messages_request_without_changing_existing_settings(self):
        executable = shutil.which("claude")
        self.assertIsNotNone(executable)
        model = "claude-sonnet-5"
        prompt = "Reply exactly: TokenLab local Messages fixture completed."
        reply = "TokenLab local Messages fixture completed."
        fixture_key = "sk-tokenlab-messages-fixture-not-a-real-key"
        requests = []
        receiver_errors = []

        class Receiver(BaseHTTPRequestHandler):
            def setup(self):
                super().setup()
                self.connection.settimeout(5)

            def log_message(self, *_):
                pass

            def do_POST(self):
                try:
                    body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                    requests.append({"path": self.path, "body": body,
                                     "fixture_auth": self.headers.get("Authorization") == f"Bearer {fixture_key}",
                                     "api_key": self.headers.get("x-api-key"),
                                     "old_header": self.headers.get("X-Fixture"),
                                     "anthropic_version": self.headers.get("anthropic-version"),
                                     "content_type": self.headers.get("Content-Type")})
                    events = [
                        {"type": "message_start", "message": {
                            "id": "msg_tokenlab_local_fixture", "type": "message", "role": "assistant",
                            "model": model, "content": [], "stop_reason": None, "stop_sequence": None,
                            "usage": {"input_tokens": 20, "output_tokens": 0,
                                      "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}}},
                        {"type": "content_block_start", "index": 0,
                         "content_block": {"type": "text", "text": ""}},
                        {"type": "content_block_delta", "index": 0,
                         "delta": {"type": "text_delta", "text": reply}},
                        {"type": "content_block_stop", "index": 0},
                        {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                         "usage": {"output_tokens": 8}},
                        {"type": "message_stop"},
                    ]
                    payload = "".join(f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"
                                      for event in events).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Content-Length", str(len(payload)))
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(payload)
                    self.wfile.flush()
                except Exception as error:
                    receiver_errors.append(type(error).__name__)

        with tempfile.TemporaryDirectory(prefix="tokenlab-claude-request-") as directory:
            root = Path(directory)
            config = root / "claude"
            config.mkdir()
            workspace = root / "project"
            workspace.mkdir()
            marker = root / "old-key-helper-ran"
            old_helper = root / "old-key-helper.py"
            old_helper.write_text("from pathlib import Path\n"
                                  f"Path({str(marker)!r}).touch()\n"
                                  "print('sk-existing-helper-fixture')\n", encoding="utf-8")
            helper_command = [sys.executable, str(old_helper)]
            original = json.dumps({
                "model": "claude-haiku-4-5", "permissions": {"defaultMode": "plan"},
                "env": {"ANTHROPIC_API_KEY": "sk-existing-fixture", "ANTHROPIC_CUSTOM_HEADERS": "X-Fixture: old"},
                "apiKeyHelper": (subprocess.list2cmdline(helper_command) if os.name == "nt"
                                 else shlex.join(helper_command)),
                "fallbackModel": ["claude-haiku-4-5"],
            }).encode()
            (config / "settings.json").write_bytes(original)
            (config / ".credentials.json").write_bytes(b'{"fixtureExistingAccount":"not-a-token"}')

            def snapshot(path):
                metadata = path.stat()
                return path.read_bytes(), metadata.st_mtime_ns, metadata.st_mode

            protected = {config / name: snapshot(config / name)
                         for name in ("settings.json", ".credentials.json")}
            environment = {key: os.environ[key] for key in
                           ("PATH", "SYSTEMROOT", "SystemRoot", "WINDIR", "COMSPEC", "PATHEXT") if key in os.environ}
            environment.update(HOME=directory, USERPROFILE=directory, CLAUDE_CONFIG_DIR=str(config),
                               APPDATA=directory, LOCALAPPDATA=directory, TMPDIR=directory,
                               TMP=directory, TEMP=directory, PYTHONDONTWRITEBYTECODE="1",
                               DISABLE_AUTOUPDATER="1", CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1")
            server = HTTPServer(("127.0.0.1", 0), Receiver)
            thread = threading.Thread(target=server.serve_forever, name="claude-messages-fixture")
            thread.start()
            sandbox = (["/usr/bin/sandbox-exec", "-p",
                        '(version 1)(allow default)(deny network*)'
                        f'(allow network-outbound (remote ip "localhost:{server.server_port}"))'
                        '(deny mach-lookup (global-name "com.apple.securityd"))']
                       if sys.platform == "darwin" else [])

            def run(command):
                # The launcher owns a child CLI. Kill the whole process group/tree
                # on timeout so a failing request cannot leave that child running.
                process = subprocess.Popen([*sandbox, *command], cwd=workspace, env=environment,
                                           stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                           text=True, encoding="utf-8", errors="replace",
                                           start_new_session=os.name != "nt",
                                           creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)
                try:
                    output, errors = process.communicate(timeout=45)
                except BaseException:
                    if os.name == "nt":
                        subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)],
                                       capture_output=True, timeout=10)
                    else:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    process.communicate(timeout=10)
                    raise
                self.assertFalse(fixture_key in output + errors, "Fixture credential leaked to client output")
                return subprocess.CompletedProcess(command, process.returncode, output, errors)

            try:
                helper = [sys.executable, setup.__file__, "--claude-bin", executable,
                          "--claude-config-dir", str(config)]
                applied = run([*helper, "--model", model, "--apply"])
                self.assertEqual(applied.returncode, 0, applied.stderr)
                # The real helper detects the client in a separate credential-free HOME.
                self.assertIn("Claude Code 2.1.263;", applied.stdout)
                launcher = config / "tokenlab-claude.py"
                launcher_before = snapshot(launcher)
                environment["TOKENLAB_API_KEY"] = fixture_key
                # Override only the endpoint constant in this child Python process.
                # The generated launcher and installed helper bytes remain untouched.
                driver = ("import runpy, sys; sys.path.insert(0, sys.argv[1]); "
                          "import configure_claude; configure_claude.BASE_URL = sys.argv[2]; "
                          "sys.argv = sys.argv[3:]; runpy.run_path(sys.argv[0], run_name='__main__')")
                completed = run([sys.executable, "-c", driver, str(Path(setup.__file__).parent),
                                 f"http://127.0.0.1:{server.server_port}", str(launcher),
                                 "--print", prompt, "--output-format", "stream-json", "--no-session-persistence"])
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertFalse(receiver_errors, receiver_errors)
                events = [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]
                init = next(event for event in events
                            if event.get("type") == "system" and event.get("subtype") == "init")
                self.assertEqual(init["model"], model)
                self.assertEqual(init["permissionMode"], "plan")
                self.assertEqual(init["apiKeySource"], "none")
                results = [event for event in events if event.get("type") == "result"]
                self.assertEqual(len(results), 1)
                self.assertEqual(results[0]["subtype"], "success")
                self.assertFalse(results[0]["is_error"])
                self.assertEqual(results[0]["result"], reply)
                assistants = [event["message"] for event in events if event.get("type") == "assistant"]
                self.assertEqual(len(assistants), 1)
                self.assertEqual(assistants[0]["model"], model)
                # Claude emits its assistant event before message_delta updates
                # stop_reason. The separate success result proves stream completion.
                self.assertEqual(assistants[0]["content"], [{"type": "text", "text": reply}])
                self.assertEqual(len(requests), 1, "A successful text task must not silently retry or dispatch elsewhere")
                for request in requests:
                    self.assertEqual(urlsplit(request["path"]).path, "/v1/messages")
                    self.assertTrue(request["fixture_auth"])
                    self.assertIsNone(request["api_key"])
                    self.assertIsNone(request["old_header"])
                    self.assertEqual(request["anthropic_version"], "2023-06-01")
                    self.assertEqual(request["content_type"], "application/json")
                    body = request["body"]
                    self.assertEqual(body["model"], model)
                    self.assertIs(body["stream"], True)
                    self.assertIsInstance(body["max_tokens"], int)
                    self.assertGreater(body["max_tokens"], 0)
                    user_contents = [message["content"] for message in body["messages"] if message["role"] == "user"]
                    self.assertTrue(any(content == prompt if isinstance(content, str) else
                                        any(block.get("type") == "text" and block.get("text") == prompt for block in content)
                                        for content in user_contents), "The Messages request must include the exact user prompt")
                self.assertEqual(snapshot(launcher), launcher_before)
                restored = run([*helper, "--restore", "--apply"])
                self.assertEqual(restored.returncode, 0, restored.stderr)
                self.assertFalse(launcher.exists())
                self.assertFalse((config / ".tokenlab-claude.py.tokenlab-backup").exists())
                self.assertFalse(marker.exists(), "The existing key helper must never run")
                for path, expected in protected.items():
                    self.assertEqual(snapshot(path), expected, path.name)
                for path in root.rglob("*"):
                    if path.is_file():
                        self.assertFalse(fixture_key.encode() in path.read_bytes(),
                                         f"Fixture credential persisted in {path.name}")
                print(json.dumps({"client": "claude", "version": "2.1.263", "permission_mode": init["permissionMode"],
                                  "result": results[0]["subtype"], "reply": results[0]["result"],
                                  "captured_requests": [{"path": request["path"], "model": request["body"]["model"],
                                                         "stream": request["body"]["stream"],
                                                         "max_tokens": request["body"]["max_tokens"],
                                                         "message_roles": [message["role"] for message in request["body"]["messages"]]}
                                                        for request in requests]}))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                self.assertFalse(thread.is_alive(), "The local receiver must stop before its temporary HOME is removed")


if __name__ == "__main__":
    unittest.main()

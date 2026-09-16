"""Pinned official Hermes CLI completes a local Chat Completions tool round trip."""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import unittest

from test_configure_claude_clients import run_in_windows_job


SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "tokenlab-api-integration" / "scripts"


@unittest.skipUnless(os.environ.get("TOKENLAB_HERMES_CLIENT_TESTS") == "1",
                     "Set TOKENLAB_HERMES_CLIENT_TESTS=1 for the pinned installed Hermes check")
class InstalledHermesTests(unittest.TestCase):
    def test_official_cli_completes_read_only_tool_round_trip_and_preserves_existing_settings(self):
        executable = os.environ.get("TOKENLAB_HERMES_BIN") or shutil.which("hermes")
        self.assertIsNotNone(executable, "Install the pinned official Hermes 0.21.3 client")
        python = os.environ.get("TOKENLAB_HERMES_PYTHON", sys.executable)
        fixture_key = "sk-tokenlab-hermes-fixture-not-a-real-key"
        model = "fixture-tool-model"
        prompt = "Read fixture.txt with read_file, then report its exact content."
        file_content = "TokenLab local Hermes read-only tool completed."
        reply = "Verified: " + file_content
        requests = []
        metadata_requests = []
        receiver_errors = []

        class Receiver(BaseHTTPRequestHandler):
            def setup(self):
                super().setup()
                self.connection.settimeout(5)

            def log_message(self, *_):
                pass

            def send_json(self, status, body):
                payload = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(payload)

            def do_GET(self):
                # Hermes refreshes public model metadata separately from inference.
                # Keep that optional lookup local as well as both inference turns.
                if self.path == "/catalog":
                    self.send_json(200, {"fixture": {"id": "fixture", "models": {}}})
                elif self.path.removeprefix("/existing") in (
                        "/api/v1/models", "/api/tags", "/v1/props", "/props", "/version", "/v1/models", "/models",
                        "/v1/models/fixture-existing-model", f"/v1/models/{model}"):
                    # The pinned client probes LM Studio, Ollama, llama.cpp and
                    # OpenAI metadata shapes when any provider URL is loopback.
                    metadata_requests.append("GET " + self.path)
                    self.send_json(404, {"error": "No local model metadata"})
                else:
                    receiver_errors.append("Unexpected GET " + self.path)
                    self.send_json(404, {"error": {"message": "Unexpected fixture path"}})

            def do_POST(self):
                try:
                    body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                    if self.path in ("/api/show", "/existing/api/show"):
                        # Loopback endpoints trigger Hermes' Ollama metadata probe.
                        # This receiver implements Chat Completions, not Ollama.
                        metadata_requests.append("POST " + self.path)
                        self.send_json(404, {"error": "No Ollama model metadata"})
                        return
                    requests.append({"path": self.path, "body": body,
                                     "fixture_auth": self.headers.get("Authorization") == f"Bearer {fixture_key}",
                                     "content_type": self.headers.get("Content-Type")})
                    if self.path != "/v1/chat/completions" or len(requests) > 2:
                        self.send_json(400, {"error": {"message": "Unexpected fixture inference request"}})
                        return
                    tool_calls = [{"id": "call_tokenlab_read_fixture", "type": "function",
                                   "function": {"name": "read_file", "arguments": json.dumps({"path": "fixture.txt"})}}]
                    first = len(requests) == 1
                    message = ({"role": "assistant", "content": None, "tool_calls": tool_calls}
                               if first else {"role": "assistant", "content": reply})
                    reason = "tool_calls" if first else "stop"
                    common = {"id": f"chatcmpl-tokenlab-local-{len(requests)}", "created": 1, "model": model}
                    usage = {"prompt_tokens": 30, "completion_tokens": 12, "total_tokens": 42}
                    if body.get("stream"):
                        delta = ({"role": "assistant", "tool_calls": [{"index": 0, **tool_calls[0]}]}
                                 if first else {"role": "assistant", "content": reply})
                        chunks = [
                            {**common, "object": "chat.completion.chunk",
                             "choices": [{"index": 0, "delta": delta, "finish_reason": None}]},
                            {**common, "object": "chat.completion.chunk",
                             "choices": [{"index": 0, "delta": {}, "finish_reason": reason}]},
                            {**common, "object": "chat.completion.chunk", "choices": [], "usage": usage},
                        ]
                        payload = ("".join("data: " + json.dumps(chunk) + "\n\n" for chunk in chunks)
                                   + "data: [DONE]\n\n").encode()
                        self.send_response(200)
                        self.send_header("Content-Type", "text/event-stream")
                        self.send_header("Content-Length", str(len(payload)))
                        self.send_header("Connection", "close")
                        self.end_headers()
                        self.wfile.write(payload)
                    else:
                        self.send_json(200, {**common, "object": "chat.completion", "usage": usage,
                                            "choices": [{"index": 0, "message": message, "finish_reason": reason}]})
                    self.wfile.flush()
                except Exception as error:
                    receiver_errors.append(type(error).__name__)

        with tempfile.TemporaryDirectory(prefix="tokenlab-hermes-client-") as directory:
            root = Path(directory)
            config = root / "hermes"
            config.mkdir()
            workspace = root / "project"
            workspace.mkdir()
            fixture = workspace / "fixture.txt"
            fixture.write_text(file_content + "\n", encoding="utf-8")
            server = HTTPServer(("127.0.0.1", 0), Receiver)
            self.addCleanup(server.server_close)
            thread = threading.Thread(target=server.serve_forever, name="hermes-chat-fixture")
            origin = f"http://127.0.0.1:{server.server_port}"
            original = ("# Preserve this provider, default, and approval policy.\r\n"
                        "_config_version: 44\r\n"
                        "model: {default: fixture-existing-model, provider: 'custom:existing'}\r\n"
                        "providers:\r\n"
                        "  existing:\r\n"
                        f"    api: '{origin}/existing/v1'\r\n"
                        "    key_env: EXISTING_API_KEY\r\n"
                        "    transport: chat_completions\r\n"
                        "    default_model: fixture-existing-model\r\n"
                        "approvals: {mode: manual, single_query_mode: deny, timeout: 1, deny: ['rm *']}\r\n"
                        "platform_toolsets: {cli: [file]}\r\n"
                        "updates: {check: false}\r\n"
                        f"models_dev: {{url: '{origin}/catalog'}}\r\n"
                        "auxiliary: {title_generation: {enabled: false}}\r\n"
                        "memory: {memory_enabled: false, user_profile_enabled: false}\r\n").encode()
            target = config / "config.yaml"
            target.write_bytes(original)
            (config / ".env").write_bytes(b"# Existing account key stays unchanged\nEXISTING_API_KEY=sk-existing-fixture\n")
            (config / "auth.json").write_bytes(
                b'{"version":1,"active_provider":"custom:existing","providers":{"custom:existing":{"api_key":"sk-existing-account-fixture"}}}')
            (config / "active_profile").write_bytes(b"default\n")

            def snapshot(path):
                metadata = path.stat()
                return path.read_bytes(), metadata.st_mtime_ns, metadata.st_mode

            protected = {path: snapshot(path) for path in
                         (config / ".env", config / "auth.json", config / "active_profile", fixture)}
            original_mode = target.stat().st_mode
            environment = {key: os.environ[key] for key in
                           ("PATH", "SYSTEMROOT", "SystemRoot", "WINDIR", "COMSPEC", "PATHEXT") if key in os.environ}
            environment.update(HOME=directory, USERPROFILE=directory, HERMES_HOME=str(config),
                               APPDATA=directory, LOCALAPPDATA=directory, TMPDIR=directory, TMP=directory, TEMP=directory,
                               XDG_CONFIG_HOME=str(root / "xdg-config"), XDG_DATA_HOME=str(root / "xdg-data"),
                               XDG_CACHE_HOME=str(root / "xdg-cache"), XDG_STATE_HOME=str(root / "xdg-state"),
                               HERMES_DISABLE_LAZY_INSTALLS="1", HERMES_SKIP_NODE_BOOTSTRAP="1",
                               HERMES_GUEST_ONBOARDING="0", PYTHONDONTWRITEBYTECODE="1", NO_COLOR="1")
            # The installed Python console entry point loads this test-only audit
            # hook. It blocks non-loopback Python sockets on all three CI OSes.
            # macOS additionally denies external networking at the OS boundary.
            guard = root / "network-guard"
            guard.mkdir()
            (guard / "sitecustomize.py").write_text(
                "import sys\n"
                f"port = {server.server_port}\n"
                "def local_only(event, args):\n"
                "    if event == 'socket.connect' and isinstance(args[1], tuple):\n"
                "        if args[1][0] not in ('127.0.0.1', '::1', 'localhost') or args[1][1] != port:\n"
                "            raise OSError('This test permits only its loopback receiver')\n"
                "    if event == 'socket.getaddrinfo':\n"
                "        if args[0] not in ('127.0.0.1', '::1', 'localhost') or int(args[1]) != port:\n"
                "            raise OSError('This test permits only its loopback receiver')\n"
                "sys.addaudithook(local_only)\n", encoding="utf-8")
            environment["PYTHONPATH"] = str(guard)
            sandbox = (["/usr/bin/sandbox-exec", "-p",
                        '(version 1)(allow default)(deny network*)'
                        f'(allow network-outbound (remote ip "localhost:{server.server_port}"))'
                        '(deny mach-lookup (global-name "com.apple.securityd"))']
                       if sys.platform == "darwin" else [])

            def run(command):
                if os.name == "nt":
                    result = run_in_windows_job(command, cwd=workspace, env=environment, timeout=90)
                else:
                    process = subprocess.Popen([*sandbox, *command], cwd=workspace, env=environment,
                                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                               text=True, encoding="utf-8", errors="replace", start_new_session=True)
                    try:
                        output, errors = process.communicate(timeout=90)
                        result = subprocess.CompletedProcess(command, process.returncode, output, errors)
                    finally:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        process.communicate(timeout=10)
                self.assertFalse(fixture_key in result.stdout + result.stderr, "Fixture key leaked to client output")
                return result

            thread.start()
            try:
                helper = [sys.executable, str(SCRIPTS / "configure_hermes.py"), "--hermes-home", str(config),
                          "--hermes-bin", executable, "--hermes-python", python, "--provider", "tokenlab"]
                preview = run([*helper, "--model", model])
                self.assertEqual(preview.returncode, 0, preview.stderr)
                self.assertEqual(target.read_bytes(), original)
                applied = run([*helper, "--model", model, "--apply"])
                self.assertEqual(applied.returncode, 0, applied.stderr)
                self.assertIn("Hermes 0.21.3;", applied.stdout)
                configured = target.read_bytes()
                self.assertEqual(target.stat().st_mode, original_mode)
                configured_snapshot = snapshot(target)
                applied_again = run([*helper, "--model", model, "--apply"])
                self.assertEqual(applied_again.returncode, 0, applied_again.stderr)
                self.assertIn("unchanged", applied_again.stdout)
                self.assertEqual(snapshot(target), configured_snapshot)
                client = [executable, "--profile", "default"]
                for key, expected in (("model", {"default": "fixture-existing-model", "provider": "custom:existing"}),
                                      ("approvals.mode", "manual"), ("approvals.single_query_mode", "deny")):
                    loaded = run([*client, "config", "get", key, "--json"])
                    self.assertEqual(loaded.returncode, 0, loaded.stderr)
                    value = json.loads(loaded.stdout)
                    if key == "model":
                        for name, selection in expected.items():
                            self.assertEqual(value[name], selection)
                    else:
                        self.assertEqual(value, expected)
                self.assertEqual(target.read_bytes(), configured)
                self.assertEqual(configured.count(b"https://api.tokenlab.sh/v1"), 1)
                local_config = configured.replace(b"https://api.tokenlab.sh/v1", (origin + "/v1").encode())
                target.write_bytes(local_config)
                environment["TOKENLAB_API_KEY"] = fixture_key
                completed = run([*client, "chat", "--provider", "custom:tokenlab", "--model", model,
                                 "--toolsets", "file", "--quiet", "--oneshot", "--max-turns", "3", "-q", prompt])
                self.assertEqual(completed.returncode, 0, completed.stdout + "\n" + completed.stderr + "\n" + json.dumps([
                    {"path": request["path"], "model": request["body"].get("model"),
                     "roles": [message["role"] for message in request["body"].get("messages", [])],
                     "tools": [message for message in request["body"].get("messages", []) if message["role"] == "tool"]}
                    for request in requests]))
                output_lines = completed.stdout.splitlines()
                scanner_notice = ("⚠ tirith security scanner enabled but not available — "
                                  "command scanning will use pattern matching only")
                if output_lines and output_lines[0].strip() == scanner_notice:
                    output_lines = output_lines[1:]
                self.assertEqual("\n".join(output_lines).strip(), reply)
                self.assertIn("session_id:", completed.stderr)
                self.assertFalse(receiver_errors, receiver_errors)
                self.assertEqual(len(requests), 2, "Exactly one read-only tool call and its continuation are required")
                for request in requests:
                    self.assertEqual(request["path"], "/v1/chat/completions")
                    self.assertTrue(request["fixture_auth"])
                    self.assertEqual(request["content_type"], "application/json")
                    self.assertEqual(request["body"]["model"], model)
                first, second = [request["body"] for request in requests]
                self.assertTrue(any(message["role"] == "user" and message["content"] == prompt
                                    for message in first["messages"]))
                self.assertTrue(any(tool.get("function", {}).get("name") == "read_file" for tool in first["tools"]))
                results = [message for message in second["messages"] if message["role"] == "tool"]
                self.assertEqual(len(results), 1)
                self.assertEqual(results[0]["tool_call_id"], "call_tokenlab_read_fixture")
                self.assertIn(file_content, results[0]["content"])
                self.assertEqual(target.read_bytes(), local_config, "The real client must not rewrite configured settings")
                # Restore the deliberate endpoint-only fixture edit before the
                # helper verifies ownership and restores the original bytes.
                target.write_bytes(configured)
                restored = run([*helper, "--restore", "--apply"])
                self.assertEqual(restored.returncode, 0, restored.stderr)
                self.assertEqual(target.read_bytes(), original)
                self.assertEqual(target.stat().st_mode, original_mode)
                self.assertFalse((config / ".config.yaml.tokenlab.tokenlab-backup").exists())
                for path, before in protected.items():
                    self.assertEqual(snapshot(path), before, path.name)
                for path in root.rglob("*"):
                    if path.is_file():
                        self.assertFalse(fixture_key.encode() in path.read_bytes(),
                                         f"Fixture credential persisted in {path.name}")
                print(json.dumps({"client": "hermes", "version": "0.21.3", "result": "success", "reply": reply,
                                  "tool": "read_file", "metadata_probes": metadata_requests, "captured_requests": [
                                      {"path": request["path"], "model": request["body"]["model"],
                                       "stream": request["body"].get("stream", False),
                                       "message_roles": [message["role"] for message in request["body"]["messages"]]}
                                      for request in requests]}))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                self.assertFalse(thread.is_alive(), "The fixture receiver must stop before its temporary HOME is removed")


if __name__ == "__main__":
    unittest.main()

"""Opt-in pinned Codex checks in disposable homes, with loopback-only Responses."""

import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import unittest

from test_configure_codex import setup


@unittest.skipUnless(os.environ.get("TOKENLAB_INSTALLED_CLIENT_TESTS") == "1"
                     or (sys.platform == "darwin" and os.environ.get("TOKENLAB_CODEX_OFFLINE_TEST") == "1"),
                     "Set TOKENLAB_INSTALLED_CLIENT_TESTS=1 for the pinned installed-client check")
class InstalledCodexTests(unittest.TestCase):
    def test_real_cli_completes_responses_request_and_preserves_original_settings(self):
        executable = shutil.which("codex")
        self.assertIsNotNone(executable)
        self.assertEqual(setup.detect_codex(executable)[1], "0.149.0")
        requests = []
        fixture_key = "sk-tokenlab-codex-request-fixture-not-a-real-key"
        model = "gpt-5.6-sol"
        reply_parts = ("Local Codex ", "reply complete.")
        reply = "".join(reply_parts)

        class Receiver(BaseHTTPRequestHandler):
            def setup(self):
                super().setup()
                self.connection.settimeout(5)

            def log_message(self, *_):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append({"path": self.path, "body": body,
                                 "fixture_auth": self.headers.get("Authorization") == f"Bearer {fixture_key}"})
                response = {"id": "resp_local_fixture", "object": "response", "created_at": 1,
                            "status": "in_progress", "model": model, "output": []}
                item = {"id": "msg_local_fixture", "type": "message", "role": "assistant",
                        "status": "in_progress", "content": []}
                part = {"type": "output_text", "text": "", "annotations": []}
                completed_part = dict(part, text=reply)
                completed_item = dict(item, status="completed", content=[completed_part])
                usage = {"input_tokens": 5, "output_tokens": 4, "total_tokens": 9,
                         "input_tokens_details": {"cached_tokens": 0},
                         "output_tokens_details": {"reasoning_tokens": 0}}
                events = [
                    {"type": "response.created", "response": response},
                    {"type": "response.in_progress", "response": response},
                    {"type": "response.output_item.added", "output_index": 0, "item": item},
                    {"type": "response.content_part.added", "item_id": item["id"],
                     "output_index": 0, "content_index": 0, "part": part},
                    *[{"type": "response.output_text.delta", "item_id": item["id"],
                       "output_index": 0, "content_index": 0, "delta": text} for text in reply_parts],
                    {"type": "response.output_text.done", "item_id": item["id"],
                     "output_index": 0, "content_index": 0, "text": reply},
                    {"type": "response.content_part.done", "item_id": item["id"],
                     "output_index": 0, "content_index": 0, "part": completed_part},
                    {"type": "response.output_item.done", "output_index": 0, "item": completed_item},
                    {"type": "response.completed", "response": dict(response, status="completed",
                     output=[completed_item], usage=usage)},
                ]
                payload = "".join(f"event: {event['type']}\ndata: {json.dumps(dict(event, sequence_number=index))}\n\n"
                                  for index, event in enumerate(events))
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(payload.encode())))
                self.end_headers()
                self.wfile.write(payload.encode())

        with tempfile.TemporaryDirectory(prefix="tokenlab-codex-request-") as directory, \
                ThreadingHTTPServer(("127.0.0.1", 0), Receiver) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                root = Path(directory)
                config = root / "codex"
                config.mkdir()
                workspace = root / "workspace"
                workspace.mkdir()
                original = b'''model = "existing-model"\nmodel_provider = "existing"\napproval_policy = "on-request"\nsandbox_mode = "read-only"\n[model_providers.existing]\nname = "Existing"\nbase_url = "https://example.invalid/v1"\nwire_api = "responses"\nenv_key = "TOKENLAB_OFFLINE_BASE_KEY"\n'''
                (config / "config.toml").write_bytes(original)
                (config / "auth.json").write_bytes(b'{"OPENAI_API_KEY":"sk-existing-account-fixture-not-a-real-key"}')
                protected = {path: (path.read_bytes(), path.stat().st_mtime_ns, path.stat().st_mode)
                             for path in (config / "config.toml", config / "auth.json")}
                environment = {key: os.environ[key] for key in
                               ("PATH", "SYSTEMROOT", "SystemRoot", "WINDIR", "COMSPEC", "PATHEXT") if key in os.environ}
                environment.update(HOME=directory, USERPROFILE=directory, CODEX_HOME=str(config),
                                   APPDATA=directory, LOCALAPPDATA=directory, TMPDIR=directory,
                                   TMP=directory, TEMP=directory, TOKENLAB_API_KEY=fixture_key)
                network = (["/usr/bin/sandbox-exec", "-p",
                            f'(version 1)(allow default)(deny network*)(allow network-outbound (remote ip "localhost:{server.server_port}"))']
                           if sys.platform == "darwin" else [])

                def run(command):
                    process = subprocess.Popen([*network, *command], cwd=workspace, env=environment,
                                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                               text=True, encoding="utf-8", errors="replace",
                                               start_new_session=os.name != "nt",
                                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)
                    try:
                        output, errors = process.communicate(timeout=45)
                    except BaseException:
                        # npm's Windows shim can own a native child process.
                        # A timeout must stop that whole isolated client tree.
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
                    return subprocess.CompletedProcess(command, process.returncode, output, errors)

                helper = [sys.executable, setup.__file__, "--codex-bin", executable,
                          "--codex-home", str(config)]
                applied = run([*helper, "--model", model, "--reasoning-effort", "xhigh", "--apply"])
                self.assertEqual(applied.returncode, 0, applied.stderr)
                target = config / "tokenlab.config.toml"
                published_profile = target.read_bytes()
                # Only the endpoint changes in this disposable profile. Retain
                # the real helper's model, Responses protocol and environment auth.
                local_profile = published_profile.replace(b"https://api.tokenlab.sh/v1",
                                                          f"http://127.0.0.1:{server.server_port}/v1".encode())
                self.assertNotEqual(local_profile, published_profile)
                target.write_bytes(local_profile)
                completed = run([executable, "--profile", "tokenlab", "exec", "--skip-git-repo-check",
                                 "--json", "Return a short confirmation without using tools or changing files."])
                self.assertEqual(completed.returncode, 0, completed.stderr)
                events = [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]
                messages = [event["item"]["text"] for event in events
                            if event.get("type") == "item.completed" and event.get("item", {}).get("type") == "agent_message"]
                self.assertEqual(messages, [reply])
                self.assertEqual(sum(event.get("type") == "turn.completed" for event in events), 1)
                self.assertFalse(any(event.get("type") in ("turn.failed", "error") for event in events))
                self.assertEqual(len(requests), 1, "A successful text task must not silently retry or dispatch elsewhere")
                request = requests[0]
                self.assertEqual(request["path"], "/v1/responses")
                self.assertTrue(request["fixture_auth"])
                self.assertEqual(request["body"]["model"], model)
                self.assertIs(request["body"]["stream"], True)
                self.assertEqual(request["body"]["reasoning"]["effort"], "xhigh")
                self.assertNotIn("temperature", request["body"])
                self.assertNotIn("max_tokens", request["body"])
                self.assertEqual(target.read_bytes(), local_profile)
                for path, expected in protected.items():
                    self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns, path.stat().st_mode), expected)
                self.assertNotIn(fixture_key, completed.stdout + completed.stderr)
                for path in root.rglob("*"):
                    if path.is_file():
                        self.assertNotIn(fixture_key.encode(), path.read_bytes(), path.name)
                # The endpoint substitution intentionally invalidates the helper's
                # managed checksum. Return its exact bytes before testing restore.
                target.write_bytes(published_profile)
                restored = run([*helper, "--restore", "--apply"])
                self.assertEqual(restored.returncode, 0, restored.stderr)
                self.assertFalse(target.exists())
                ordinary = run([executable, "exec", "--skip-git-repo-check", "Check the existing configuration"])
                self.assertEqual(ordinary.returncode, 1)
                self.assertIn("provider: existing", ordinary.stderr)
                self.assertIn("model: existing-model", ordinary.stderr)
                self.assertIn("sandbox: read-only", ordinary.stderr)
                self.assertIn("Missing environment variable: `TOKENLAB_OFFLINE_BASE_KEY`", ordinary.stderr)
                self.assertEqual(len(requests), 1)
                for path, expected in protected.items():
                    self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns, path.stat().st_mode), expected)
                print(json.dumps({"client": "codex", "version": "0.149.0", "path": request["path"],
                                  "model": model, "stream": request["body"]["stream"],
                                  "reasoning": request["body"]["reasoning"], "completed": True,
                                  "original_files_unchanged": True}))
            finally:
                server.shutdown()
                worker.join(timeout=5)
                self.assertFalse(worker.is_alive(), "The local receiver must stop before removing its temporary HOME")

    def test_real_cli_selects_profile_and_stops_at_missing_environment_key(self):
        executable = shutil.which("codex")
        self.assertIsNotNone(executable)
        self.assertEqual(setup.detect_codex(executable)[1], "0.149.0",
                         "Refresh this explicitly versioned client check before claiming a newer version")
        with tempfile.TemporaryDirectory(prefix="tokenlab-codex-offline-") as directory:
            task_root = Path(directory)
            config_root = task_root / "codex"
            config_root.mkdir()
            workspace = task_root / "workspace"
            workspace.mkdir()
            original = b'''model = "existing-model"\nmodel_provider = "existing"\napproval_policy = "on-request"\nsandbox_mode = "read-only"\n[model_providers.existing]\nname = "Existing"\nbase_url = "https://example.invalid/v1"\nwire_api = "responses"\nenv_key = "TOKENLAB_OFFLINE_BASE_KEY"\n'''
            (config_root / "config.toml").write_bytes(original)
            environment = {key: os.environ[key] for key in
                           ("PATH", "SYSTEMROOT", "SystemRoot", "WINDIR", "COMSPEC", "PATHEXT") if key in os.environ}
            environment.update(HOME=directory, USERPROFILE=directory, CODEX_HOME=str(config_root),
                               APPDATA=directory, LOCALAPPDATA=directory, TMPDIR=directory,
                               TMP=directory, TEMP=directory)
            deny_network = (["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)"]
                            if sys.platform == "darwin" else [])
            helper = [*deny_network, sys.executable, setup.__file__,
                      "--codex-bin", executable, "--codex-home", str(config_root)]
            configuration = ["--model", "gpt-5.6-sol", "--reasoning-effort", "xhigh"]
            target = config_root / "tokenlab.config.toml"
            for applying in [False, True, True]:
                before = target.stat().st_mtime_ns if target.exists() else None
                result = subprocess.run([*helper, *configuration, *(["--apply"] if applying else [])],
                                        cwd=workspace, env=environment, capture_output=True,
                                        text=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr)
                if not applying:
                    self.assertIn("Preview: create", result.stdout)
                    self.assertFalse(target.exists())
                elif before is not None:
                    self.assertIn("Apply: unchanged", result.stdout)
                    self.assertEqual(target.stat().st_mtime_ns, before)
                else:
                    self.assertIn("Apply: create", result.stdout)
                    self.assertTrue(target.exists())
            for profile in [False, True]:
                command = [*deny_network, executable]
                if profile:
                    command += ["--profile", "tokenlab"]
                command += ["exec", "--skip-git-repo-check", "Offline configuration check"]
                result = subprocess.run(command, cwd=workspace, env=environment, input="",
                                        capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, 1)
                self.assertIn("provider: tokenlab" if profile else "provider: existing", result.stderr)
                self.assertIn("model: gpt-5.6-sol" if profile else "model: existing-model", result.stderr)
                self.assertIn("sandbox: read-only", result.stderr)
                if profile:
                    self.assertIn("reasoning effort: xhigh", result.stderr)
                missing_key = "TOKENLAB_API_KEY" if profile else "TOKENLAB_OFFLINE_BASE_KEY"
                self.assertIn(f"Missing environment variable: `{missing_key}`", result.stderr)
            result = subprocess.run([*helper, "--restore", "--apply"], cwd=workspace,
                                    env=environment, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(target.exists())
            self.assertEqual((config_root / "config.toml").read_bytes(), original)


if __name__ == "__main__":
    unittest.main()

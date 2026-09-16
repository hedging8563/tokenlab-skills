"""Capture real client requests on loopback. No production URL or real credential."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import unittest

from test_configure_providers import SCRIPTS


@unittest.skipUnless(os.environ.get("TOKENLAB_INSTALLED_CLIENT_TESTS") == "1",
                     "Set TOKENLAB_INSTALLED_CLIENT_TESTS=1 for pinned installed-client checks")
class InstalledProviderRequestTests(unittest.TestCase):
    def test_official_opencode_sends_selected_chat_model_without_temperature(self):
        self.check_request("opencode")

    def test_official_pi_sends_selected_chat_model_without_temperature(self):
        self.check_request("pi")

    def check_request(self, name):
        executable = shutil.which(name)
        self.assertIsNotNone(executable)
        requests = []
        fixture_key = "sk-tokenlab-local-request-fixture-not-a-real-key"

        class Receiver(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append({"path": self.path, "body": body,
                                 "fixture_auth": self.headers.get("Authorization") == f"Bearer {fixture_key}"})
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                chunk = {"id": "chatcmpl-local-fixture", "object": "chat.completion.chunk", "created": 1,
                         "model": body["model"], "choices": [{"index": 0, "delta": {"role": "assistant", "content": "OK"}, "finish_reason": None}]}
                end = dict(chunk, choices=[{"index": 0, "delta": {}, "finish_reason": "stop"}],
                           usage={"prompt_tokens": 5, "completion_tokens": 1, "total_tokens": 6})
                payload = "".join("data: " + json.dumps(value) + "\n\n" for value in (chunk, end)) + "data: [DONE]\n\n"
                self.wfile.write(payload.encode())

        with ThreadingHTTPServer(("127.0.0.1", 0), Receiver) as server, tempfile.TemporaryDirectory(prefix=f"tokenlab-{name}-request-") as directory:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.addCleanup(server.shutdown)
            root = Path(directory)
            environment = {key: os.environ[key] for key in
                           ("PATH", "SYSTEMROOT", "SystemRoot", "WINDIR", "COMSPEC", "PATHEXT") if key in os.environ}
            environment.update(HOME=directory, USERPROFILE=directory, APPDATA=directory, LOCALAPPDATA=directory,
                               TMPDIR=directory, TMP=directory, TEMP=directory, XDG_CONFIG_HOME=str(root / "config"),
                               XDG_DATA_HOME=str(root / "data"), XDG_CACHE_HOME=str(root / "cache"),
                               XDG_STATE_HOME=str(root / "state"), PI_CODING_AGENT_DIR=str(root / "pi"), PI_OFFLINE="1",
                               OPENCODE_DISABLE_AUTOUPDATE="true", OPENCODE_DISABLE_MODELS_FETCH="true",
                               TOKENLAB_API_KEY=fixture_key)
            target = root / "tokenlab.jsonc" if name == "opencode" else root / "pi" / "models.json"
            args = ["--config", str(target)] if name == "opencode" else ["--agent-dir", str(target.parent)]
            helper = [sys.executable, str(SCRIPTS / f"configure_{name}.py"), *args,
                      f"--{name}-bin", executable, "--model", "gpt-5.6-luna", "--apply"]
            configured = subprocess.run(helper, cwd=root, env=environment, capture_output=True, text=True, timeout=30)
            self.assertEqual(configured.returncode, 0, configured.stderr)
            # Change only the endpoint in this disposable generated file. Model,
            # SDK choice and options remain exactly what the setup helper wrote.
            target.write_bytes(target.read_bytes().replace(b"https://api.tokenlab.sh/v1",
                               f"http://127.0.0.1:{server.server_port}/v1".encode()))
            if name == "opencode":
                environment["OPENCODE_CONFIG"] = str(target)
                command = [executable, "run", "--format", "json", "--model", "tokenlab/gpt-5.6-luna", "Reply OK only."]
            else:
                command = [executable, "--provider", "tokenlab", "--model", "gpt-5.6-luna", "--offline", "--no-session", "--no-tools",
                           "--no-extensions", "--no-skills", "--no-prompt-templates", "--no-themes", "--no-context-files", "--print", "Reply OK only."]
            denied = (["/usr/bin/sandbox-exec", "-p", f'(version 1)(allow default)(deny network*)(allow network-outbound (remote ip "localhost:{server.server_port}"))']
                      if sys.platform == "darwin" else [])
            completed = subprocess.run([*denied, *command], cwd=root, env=environment, capture_output=True, text=True, timeout=45)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("OK", completed.stdout)
            self.assertTrue(requests, "The actual client must send a request to the local receiver")
            for request in requests:
                self.assertEqual(request["path"], "/v1/chat/completions")
                self.assertTrue(request["fixture_auth"])
                self.assertEqual(request["body"]["model"], "gpt-5.6-luna")
                self.assertNotIn("temperature", request["body"])
                # The public model detail captured on 2026-09-17 declares Chat
                # Completions and a 128000 output-token ceiling. It does not
                # publish parameter exclusions; do not infer them from this test.
                for key in ("max_tokens", "max_completion_tokens"):
                    if key in request["body"]:
                        self.assertLessEqual(request["body"][key], 128000)
            print(json.dumps({"client": name, "captured_requests": [
                {"path": request["path"], "options": {key: value for key, value in request["body"].items()
                                                     if key not in ("messages", "tools")}} for request in requests]}))
            server.shutdown()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()

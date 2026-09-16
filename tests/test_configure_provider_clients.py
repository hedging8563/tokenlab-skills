"""Pinned official clients load provider additions in disposable homes; no inference."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from test_configure_providers import SCRIPTS, shared


@unittest.skipUnless(os.environ.get("TOKENLAB_INSTALLED_CLIENT_TESTS") == "1",
                     "Set TOKENLAB_INSTALLED_CLIENT_TESTS=1 for pinned installed-client checks")
class InstalledProviderTests(unittest.TestCase):
    def test_official_opencode_loads_added_provider_and_preserves_default_and_permissions(self):
        self.check_client("opencode", "1.18.31")

    def test_official_pi_loads_added_provider_and_preserves_default_and_account(self):
        self.check_client("pi", "0.85.1")

    def check_client(self, name, version):
        executable = shutil.which(name)
        self.assertIsNotNone(executable)
        self.assertEqual(shared.inspect_client(name, executable, tuple(map(int, version.split(".")))), version,
                         "Refresh the pinned fixture before claiming a newer client")
        with tempfile.TemporaryDirectory(prefix=f"tokenlab-{name}-client-") as directory:
            root = Path(directory)
            workspace = root / "workspace"
            workspace.mkdir()
            environment = {key: os.environ[key] for key in
                           ("PATH", "SYSTEMROOT", "SystemRoot", "WINDIR", "COMSPEC", "PATHEXT") if key in os.environ}
            environment.update(HOME=directory, USERPROFILE=directory, APPDATA=directory,
                               LOCALAPPDATA=directory, TMPDIR=directory, TMP=directory, TEMP=directory,
                               XDG_CONFIG_HOME=str(root / "config"), XDG_DATA_HOME=str(root / "data"),
                               XDG_CACHE_HOME=str(root / "cache"), XDG_STATE_HOME=str(root / "state"),
                               OPENCODE_DISABLE_AUTOUPDATE="true", OPENCODE_DISABLE_MODELS_FETCH="true",
                               PI_CODING_AGENT_DIR=str(root / "pi"), PI_OFFLINE="1")
            # macOS provides an OS network-deny sandbox. Other CI runners use only
            # the clients' local config/model-list commands and a non-secret fixture.
            denied = (["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)"]
                      if sys.platform == "darwin" else [])
            if name == "opencode":
                target = root / "config" / "opencode" / "tokenlab.jsonc"
                original = b'\xef\xbb\xbf{\r\n // existing account stays selected\r\n "model":"existing/fixture-model",\r\n "permission":{"*":"ask","bash":"deny"},\r\n "provider":{"existing":{"npm":"@ai-sdk/openai-compatible","options":{"baseURL":"https://example.invalid/v1","apiKey":"fixture-existing"},"models":{"fixture-model":{"name":"Existing"}}},},\r\n}\r\n'
                auth = root / "data" / "opencode" / "auth.json"
                args = ["--config", str(target), "--opencode-bin", executable]
                list_args = ["models", "tokenlab"]
            else:
                target = root / "pi" / "models.json"
                original = b'\xef\xbb\xbf{\r\n // existing account stays selected\r\n "providers":{"existing":{"baseUrl":"https://example.invalid/v1","api":"openai-completions","apiKey":"fixture-existing","models":[{"id":"fixture-model"},]},},\r\n}\r\n'
                auth = root / "pi" / "auth.json"
                args = ["--agent-dir", str(target.parent), "--pi-bin", executable]
                list_args = ["--list-models", "tokenlab"]
            target.parent.mkdir(parents=True)
            target.write_bytes(original)
            auth.parent.mkdir(parents=True, exist_ok=True)
            account = b'{"existing":{"type":"api_key","key":"fixture-account"}}'
            auth.write_bytes(account)
            settings = target.parent / "settings.json"
            selection = b'{"defaultProvider":"existing","defaultModel":"fixture-model"}'
            if name == "pi":
                settings.write_bytes(selection)
            else:
                global_config = target.parent / "opencode.jsonc"
                baseline = b'{"$schema":"https://opencode.ai/config.json","model":"existing/fixture-model","permission":{"*":"ask","bash":"deny"},"provider":{"existing":{"npm":"@ai-sdk/openai-compatible","options":{"baseURL":"https://example.invalid/v1","apiKey":"fixture-existing"},"models":{"fixture-model":{"name":"Existing"}}}}}'
                global_config.write_bytes(baseline)
            helper = [sys.executable, str(SCRIPTS / f"configure_{name}.py"), *args]

            def run(command, input=None):
                return subprocess.run([*denied, *command], cwd=workspace, env=environment,
                                      capture_output=True, text=True, input=input, timeout=45)

            for applying in (False, True, True):
                before = target.stat().st_mtime_ns
                result = run([*helper, "--model", "gpt-5.6-luna", *(["--apply"] if applying else [])])
                self.assertEqual(result.returncode, 0, result.stderr)
                if not applying:
                    self.assertEqual(target.read_bytes(), original)
                elif "unchanged" in result.stdout:
                    self.assertEqual(target.stat().st_mtime_ns, before)
            configured = target.read_bytes()
            if name == "opencode":
                # A normal invocation must not discover the opt-in TokenLab layer.
                ordinary = run([executable, "debug", "config"])
                self.assertEqual(ordinary.returncode, 0, ordinary.stderr)
                self.assertNotIn("tokenlab", json.loads(ordinary.stdout).get("provider", {}))
                environment["OPENCODE_CONFIG"] = str(target)
            fixture = "sk-tokenlab-local-client-fixture-not-a-real-key"
            environment["TOKENLAB_API_KEY"] = fixture
            loaded = run([executable, *list_args])
            self.assertEqual(loaded.returncode, 0, loaded.stderr)
            self.assertIn("gpt-5.6-luna", loaded.stdout)
            self.assertIn("tokenlab", loaded.stdout)
            if name == "opencode":
                resolved = run([executable, "debug", "config"])
                self.assertEqual(resolved.returncode, 0, resolved.stderr)
                config = json.loads(resolved.stdout)
                self.assertEqual(config["model"], "existing/fixture-model")
                self.assertEqual(config["permission"]["*"], "ask")
                self.assertEqual(config["permission"]["bash"], "deny")
                self.assertEqual(config["provider"]["tokenlab"]["options"]["baseURL"], "https://api.tokenlab.sh/v1")
                self.assertEqual(config["provider"]["tokenlab"]["options"]["apiKey"], fixture)
            else:
                # Also exercise fallback selection with no saved default: the
                # appended provider must not move ahead of the existing one.
                for explicit, saved_default in ((False, True), (False, False), (True, True)):
                    if saved_default:
                        settings.write_bytes(selection)
                    else:
                        settings.unlink()
                    command = [executable, "--mode", "rpc", "--offline", "--no-session", "--no-tools",
                               "--no-extensions", "--no-skills", "--no-prompt-templates", "--no-themes", "--no-context-files"]
                    if explicit:
                        command += ["--provider", "tokenlab", "--model", "gpt-5.6-luna"]
                    state = run(command, input='{"type":"get_state"}\n')
                    self.assertEqual(state.returncode, 0, state.stderr)
                    reply = next(json.loads(line) for line in state.stdout.splitlines()
                                 if json.loads(line).get("command") == "get_state")
                    self.assertTrue(reply["success"])
                    self.assertEqual(reply["data"]["model"]["provider"], "tokenlab" if explicit else "existing")
                    self.assertEqual(reply["data"]["model"]["id"], "gpt-5.6-luna" if explicit else "fixture-model")
                    self.assertEqual(reply["data"]["messageCount"], 0)
            self.assertEqual(target.read_bytes(), configured)
            self.assertEqual(auth.read_bytes(), account)
            if name == "pi":
                self.assertEqual(settings.read_bytes(), selection)
            else:
                self.assertEqual(global_config.read_bytes(), baseline)
            for file in root.rglob("*"):
                if file.is_file():
                    self.assertNotIn(fixture.encode(), file.read_bytes(), file.name)
            restored = run([*helper, "--restore", "--apply"])
            self.assertEqual(restored.returncode, 0, restored.stderr)
            self.assertEqual(target.read_bytes(), original)
            self.assertEqual(auth.read_bytes(), account)


if __name__ == "__main__":
    unittest.main()

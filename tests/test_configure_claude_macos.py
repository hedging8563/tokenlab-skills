"""Opt-in real Claude Code check: temporary home, dummy token, OS-denied networking."""

import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest

from test_configure_claude import setup


@unittest.skipUnless(sys.platform == "darwin" and os.environ.get("TOKENLAB_CLAUDE_OFFLINE_TEST") == "1",
                     "Set TOKENLAB_CLAUDE_OFFLINE_TEST=1 on macOS for the installed-client check")
class InstalledClaudeTests(unittest.TestCase):
    def test_real_helper_and_launcher_preserve_user_settings_and_load_selected_session(self):
        executable = shutil.which("claude")
        self.assertIsNotNone(executable)
        self.assertEqual(setup.detect_claude(executable)[1], "2.1.263",
                         "Refresh this versioned check before claiming a newer installed client")
        with tempfile.TemporaryDirectory(prefix="tokenlab-claude-offline-") as directory:
            task_root = Path(directory)
            config = task_root / "claude"
            config.mkdir()
            workspace = task_root / "workspace"
            workspace.mkdir()
            key_helper_marker = task_root / "old-key-helper-ran"
            old_helper = shlex.join([sys.executable, "-c", f"from pathlib import Path; Path({str(key_helper_marker)!r}).touch()"])
            original = json.dumps({"model": "claude-haiku-4-5", "permissions": {"defaultMode": "plan"},
                                   "env": {"ANTHROPIC_API_KEY": "sk-existing-offline-not-a-real-key",
                                           "ANTHROPIC_CUSTOM_HEADERS": "X-Fixture: old"},
                                   "apiKeyHelper": old_helper, "fallbackModel": ["claude-haiku-4-5"]}).encode()
            (config / "settings.json").write_bytes(original)
            account = b'{"fixtureExistingAccount":"not-an-authentication-token"}'
            (config / ".credentials.json").write_bytes(account)
            protected = {name: (path.read_bytes(), path.stat().st_mtime_ns, path.stat().st_mode)
                         for name in ("settings.json", ".credentials.json") for path in (config / name,)}
            environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": directory,
                           "USERPROFILE": directory, "CLAUDE_CONFIG_DIR": str(config), "TMPDIR": directory,
                           "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"}
            deny_network = ["/usr/bin/sandbox-exec", "-p",
                            '(version 1)(allow default)(deny network*)(deny mach-lookup (global-name "com.apple.securityd"))']
            helper = [*deny_network, sys.executable, setup.__file__, "--claude-bin", executable,
                      "--claude-config-dir", str(config)]
            model = "claude-sonnet-4-6"
            launcher = config / "tokenlab-claude.py"
            for applying in [False, True, True]:
                before = launcher.stat().st_mtime_ns if launcher.exists() else None
                result = subprocess.run([*helper, "--model", model, *(["--apply"] if applying else [])],
                                        env=environment, cwd=workspace, capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr)
                if not applying:
                    self.assertIn("Preview: create", result.stdout)
                    self.assertFalse(launcher.exists())
                elif before is not None:
                    self.assertIn("Apply: unchanged", result.stdout)
                    self.assertEqual(launcher.stat().st_mtime_ns, before)
                else:
                    self.assertTrue(launcher.exists())
            launch = [*deny_network, sys.executable, str(launcher)]
            missing = subprocess.run([*launch, "--auth-status"], env=environment, cwd=workspace,
                                     capture_output=True, text=True, timeout=15)
            self.assertEqual(missing.returncode, 1)
            self.assertIn("Set a complete TOKENLAB_API_KEY", missing.stderr)
            fixture_token = "sk-tokenlab-offline-fixture-not-a-real-key"
            environment["TOKENLAB_API_KEY"] = fixture_token
            auth = subprocess.run([*launch, "--auth-status"], env=environment, cwd=workspace,
                                  capture_output=True, text=True, timeout=15)
            self.assertEqual(auth.returncode, 0, auth.stderr)
            self.assertIn("session Bearer credential", auth.stdout)
            self.assertNotIn(fixture_token, auth.stdout + auth.stderr)
            command = [*launch, "--print", "Offline configuration check", "--output-format", "stream-json",
                       "--no-session-persistence"]
            process = subprocess.Popen(command, cwd=workspace, env=environment, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True, start_new_session=True)
            try:
                output, errors = process.communicate(timeout=6)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                output, errors = process.communicate(timeout=5)
            events = []
            for line in output.splitlines():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
            init = next(event for event in events if event.get("type") == "system" and event.get("subtype") == "init")
            self.assertEqual(init["model"], model)
            self.assertEqual(init["permissionMode"], "plan")
            self.assertEqual(init["apiKeySource"], "none")
            self.assertNotIn(fixture_token, output + errors)
            self.assertNotEqual(process.returncode, 0)
            self.assertFalse(key_helper_marker.exists())
            for name, expected in protected.items():
                path = config / name
                self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns, path.stat().st_mode), expected)
            for path in task_root.rglob("*"):
                if path.is_file():
                    self.assertNotIn(fixture_token.encode(), path.read_bytes(), f"Token persisted in {path.name}")
            # Detect later settings edits on every launch, before an auth/model command.
            (config / "settings.json").write_text(json.dumps({"env": {"ANTHROPIC_AUTH_TOKEN": "old-fixture"}}))
            conflict = subprocess.run([*launch, "--auth-status"], env=environment, cwd=workspace,
                                      capture_output=True, text=True, timeout=15)
            self.assertEqual(conflict.returncode, 1)
            self.assertIn("conflicts with session credentials", conflict.stderr)
            (config / "settings.json").write_bytes(original)
            restored = subprocess.run([*helper, "--restore", "--apply"], env=environment, cwd=workspace,
                                      capture_output=True, text=True, timeout=15)
            self.assertEqual(restored.returncode, 0, restored.stderr)
            self.assertFalse(launcher.exists())
            self.assertEqual((config / "settings.json").read_bytes(), original)
            # The test itself rewrote settings for its conflict case; credential bytes,
            # permissions and timestamp must still be exactly unchanged by the client.
            path = config / ".credentials.json"
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns, path.stat().st_mode), protected[path.name])


if __name__ == "__main__":
    unittest.main()

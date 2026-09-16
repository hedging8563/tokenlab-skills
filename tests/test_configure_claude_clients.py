"""Actual Claude CLI authentication/configuration loading, never a model request."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()

"""Opt-in actual Codex loading test. No credentials; macOS denies all network access."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from test_configure_codex import setup


@unittest.skipUnless(sys.platform == "darwin" and os.environ.get("TOKENLAB_CODEX_OFFLINE_TEST") == "1",
                     "Set TOKENLAB_CODEX_OFFLINE_TEST=1 on macOS for the installed-CLI offline check")
class InstalledCodexTests(unittest.TestCase):
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
            environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                           "HOME": directory, "USERPROFILE": directory,
                           "CODEX_HOME": str(config_root), "TMPDIR": directory}
            deny_network = ["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)"]
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

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "skills/tokenlab-api-integration/scripts/configure_claude.py"
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location("configure_claude", SCRIPT)
setup = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = setup
spec.loader.exec_module(setup)


class ManagedSetupTests(unittest.TestCase):
    def test_host_managed_setup_is_not_overridden(self):
        with patch.dict(os.environ, {"CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST": "1"}, clear=True), self.assertRaises(setup.SetupError):
            setup.reject_managed_setup(Path("/unused"))

    def test_remote_policy_cache_is_detected_without_printing_contents(self):
        with tempfile.TemporaryDirectory(prefix="tokenlab-policy-test-") as directory:
            root = Path(directory)
            (root / "remote-settings.json").write_text('{"env":{"ANTHROPIC_AUTH_TOKEN":"secret-policy"}}')
            with patch.dict(os.environ, {}, clear=True), self.assertRaises(setup.SetupError) as error:
                setup.reject_managed_setup(root)
            self.assertNotIn("secret-policy", str(error.exception))

    def test_macos_policy_check_only_accepts_a_known_absent_domain(self):
        with patch.object(setup.sys, "platform", "darwin"), patch.dict(os.environ, {}, clear=True), patch.object(setup.Path, "exists", return_value=False), patch.object(setup.Path, "is_symlink", return_value=False):
            for code, stderr, accepted in [(0, b"", False), (1, b"Domain com.anthropic.claudecode does not exist", True),
                                           (1, b"access denied", False)]:
                result = subprocess.CompletedProcess([], code, b"secret-policy-output", stderr)
                with patch.object(setup.subprocess, "run", return_value=result):
                    if accepted:
                        setup.reject_managed_setup(Path("/unused"))
                    else:
                        with self.assertRaises(setup.SetupError) as error:
                            setup.reject_managed_setup(Path("/unused"))
                        self.assertNotIn("secret-policy", str(error.exception))


class ConfigureClaudeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tokenlab-claude-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "claude"
        self.root.mkdir()
        self.workspace = Path(self.temp.name) / "workspace"
        self.workspace.mkdir()
        self.base = json.dumps({"model": "existing-model", "permissions": {"defaultMode": "plan"},
                                "env": {"ANTHROPIC_API_KEY": "secret-existing-key"},
                                "apiKeyHelper": "existing-helper"}).encode()
        (self.root / "settings.json").write_bytes(self.base)
        (self.root / ".credentials.json").write_text('{"fixture":"secret-existing-account"}')
        self.content = setup.render_launcher(self.root, "tokenlab-claude", "claude-test-model", "claude")
        policy = patch.object(setup, "reject_managed_setup")
        policy.start()
        self.addCleanup(policy.stop)
        cwd = patch.object(setup.Path, "cwd", return_value=self.workspace)
        cwd.start()
        self.addCleanup(cwd.stop)

    def plan(self, content=None, restore=False):
        return setup.prepare(self.root, "tokenlab-claude", self.content if content is None else content, restore)

    def snapshot(self):
        return {p.name: (p.read_bytes(), p.stat().st_mtime_ns, p.stat().st_mode) for p in self.root.iterdir()}

    def run_main(self, *args):
        output = io.StringIO()
        with patch.object(setup, "detect_claude", return_value=("claude", "2.1.263")), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = setup.main(["--claude-config-dir", str(self.root), *args])
        return code, output.getvalue()

    def test_preview_does_not_write_or_read_key(self):
        before = self.snapshot()
        with patch.dict(os.environ, {"TOKENLAB_API_KEY": "secret-launch-key"}):
            code, output = self.run_main("--model", "claude-test-model")
        self.assertEqual(code, 0)
        self.assertIn("Preview: create", output)
        self.assertNotIn("secret-", output)
        self.assertEqual(self.snapshot(), before)
        self.root = self.root / "absent"
        self.assertEqual(self.run_main("--model", "claude-test-model")[0], 0)
        self.assertFalse(self.root.exists())

    def test_create_repeat_update_and_restore_preserve_user_files(self):
        before = self.snapshot()
        setup.apply(self.plan())
        target = self.root / "tokenlab-claude.py"
        self.assertNotIn(b"secret-", target.read_bytes())
        initial = self.snapshot()
        setup.apply(self.plan())
        self.assertEqual(self.snapshot(), initial)
        changed = setup.render_launcher(self.root, "tokenlab-claude", "other-model", "claude")
        update = self.plan(changed)
        setup.apply(update)
        self.assertEqual(update.backup_path.read_bytes(), self.content)
        setup.apply(self.plan(restore=True))
        self.assertEqual(target.read_bytes(), self.content)
        self.assertFalse(update.backup_path.exists())
        setup.apply(self.plan(restore=True))
        self.assertFalse(target.exists())
        self.assertEqual(self.snapshot(), before)

    def test_unmanaged_or_edited_launcher_and_backup_are_not_overwritten(self):
        target = self.root / "tokenlab-claude.py"
        for content in [b"print('my launcher')\n", self.content + b"# my edit\n"]:
            target.write_bytes(content)
            with self.assertRaises(setup.SetupError):
                self.plan()
            with self.assertRaises(setup.SetupError):
                self.plan(restore=True)
            self.assertEqual(target.read_bytes(), content)
        target.write_bytes(self.content)
        update = self.plan(setup.render_launcher(self.root, "tokenlab-claude", "other-model", "claude"))
        setup.apply(update)
        update.backup_path.write_bytes(self.content + b"# edited backup\n")
        with self.assertRaises(setup.SetupError):
            self.plan(restore=True)

    def test_settings_conflicts_are_detected_in_user_and_workspace_ancestry(self):
        local = self.workspace / ".claude" / "settings.local.json"
        local.parent.mkdir()
        cases = [{"env": {"ANTHROPIC_AUTH_TOKEN": "secret-token"}},
                 {"env": {"ANTHROPIC_AUTH_TOKEN": ""}},
                 {"env": {"CLAUDE_CONFIG_DIR": "/different"}},
                 {"modelOverrides": {"claude-test-model": "other-model"}},
                 {"forceLoginMethod": "gateway"}]
        for settings in cases:
            for path in [self.root / "settings.json", local]:
                path.write_text(json.dumps(settings))
                code, output = self.run_main("--model", "claude-test-model", "--apply")
                self.assertEqual(code, 1)
                self.assertNotIn("secret-token", output)
                self.assertFalse((self.root / "tokenlab-claude.py").exists())
                path.write_text("{}")

    def test_invalid_json_and_unknown_arguments_never_echo_secrets(self):
        (self.root / "settings.json").write_text('{"secret-invalid')
        code, output = self.run_main("--model", "claude-test-model")
        self.assertEqual(code, 1)
        self.assertNotIn("secret-invalid", output)
        output = io.StringIO()
        with contextlib.redirect_stderr(output), self.assertRaises(SystemExit):
            setup.main(["--api-key", "sk-secret-argument"])
        self.assertNotIn("sk-secret-argument", output.getvalue())

    def test_restore_remains_possible_after_unrelated_settings_edit(self):
        setup.apply(self.plan())
        (self.root / "settings.json").write_text('{"malformed')
        setup.apply(self.plan(restore=True))
        self.assertEqual((self.root / "settings.json").read_text(), '{"malformed')

    def test_changes_after_preview_are_preserved(self):
        plan = self.plan()
        (self.root / "settings.json").write_bytes(self.base + b"\n")
        with self.assertRaises(setup.SetupError):
            setup.apply(plan)
        self.assertFalse(plan.target.exists())
        plan = self.plan()
        plan.target.write_text("# concurrent launcher\n")
        with self.assertRaises(setup.SetupError):
            setup.apply(plan)
        self.assertEqual(plan.target.read_text(), "# concurrent launcher\n")

    def test_read_only_settings_can_use_a_dotfiles_symlink(self):
        outside = Path(self.temp.name) / "dotfiles-settings.json"
        outside.write_bytes(self.base)
        settings = self.root / "settings.json"
        settings.unlink()
        try:
            settings.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink creation is not available to this test user")
        setup.apply(self.plan())
        self.assertTrue(settings.is_symlink())
        self.assertEqual(outside.read_bytes(), self.base)

    def test_failed_atomic_update_keeps_previous_launcher_recoverable(self):
        setup.apply(self.plan())
        plan = self.plan(setup.render_launcher(self.root, "tokenlab-claude", "other-model", "claude"))
        original_replace = os.replace
        def fail_target(source, target):
            if Path(target) == plan.target:
                raise OSError("simulated interruption")
            return original_replace(source, target)
        with patch.object(setup.os, "replace", side_effect=fail_target), self.assertRaises(OSError):
            setup.apply(plan)
        self.assertEqual(plan.target.read_bytes(), self.content)
        self.assertEqual(plan.backup_path.read_bytes(), self.content)
        setup.apply(self.plan(restore=True))
        self.assertFalse(plan.backup_path.exists())

    def test_only_explicit_model_and_safe_launcher_names_are_accepted(self):
        for model in ["default", "sonnet", "opusplan", "sk-secret", 'x"\npermissions={}', "bad model"]:
            with self.assertRaises(setup.SetupError):
                setup.render_launcher(self.root, "tokenlab-claude", model, "claude")
        for name in ["../tokenlab", "claude", "tokenlab-claude/other"]:
            with self.assertRaises(setup.SetupError):
                setup.render_launcher(self.root, name, "claude-test-model", "claude")

    def test_launch_environment_maps_only_the_explicit_key_without_mutating_parent(self):
        original = {"TOKENLAB_API_KEY": "secret-tokenlab", "ANTHROPIC_AUTH_TOKEN": "secret-old-bearer",
                    "ANTHROPIC_API_KEY": "secret-old-key", "ANTHROPIC_CUSTOM_HEADERS": "X-Key: old",
                    "CLAUDE_CODE_USE_BEDROCK": "1", "UNRELATED_SETTING": "keep"}
        with patch.dict(os.environ, original, clear=True):
            environment = setup.launch_environment(self.root)
            self.assertEqual(dict(os.environ), original)
        self.assertEqual(environment["ANTHROPIC_AUTH_TOKEN"], "secret-tokenlab")
        self.assertEqual(environment["ANTHROPIC_API_KEY"], "")
        self.assertEqual(environment["ANTHROPIC_CUSTOM_HEADERS"], "")
        self.assertEqual(environment["CLAUDE_CODE_USE_BEDROCK"], "0")
        self.assertEqual(environment["UNRELATED_SETTING"], "keep")
        overlay = setup.session_settings()
        self.assertNotIn("ANTHROPIC_AUTH_TOKEN", overlay["env"])
        self.assertNotIn("secret", json.dumps(overlay))
        self.assertNotIn("permissions", overlay)
        self.assertEqual(overlay["fallbackModel"], [])
        for key in [None, "", "key\nother"]:
            with patch.dict(os.environ, {} if key is None else {"TOKENLAB_API_KEY": key}, clear=True), self.assertRaises(setup.SetupError):
                setup.launch_environment(self.root)

    def test_native_auth_check_rejects_other_credentials_and_never_prints_account_data(self):
        valid = {"loggedIn": True, "authMethod": "oauth_token", "apiProvider": "firstParty"}
        for status, expected in [(valid, True), ({**valid, "apiProvider": "bedrock"}, False),
                                 ({**valid, "loggedIn": False}, False),
                                 ({**valid, "authMethod": "claude_ai"}, False),
                                 ({**valid, "apiKeySource": "apiKeyHelper"}, False)]:
            result = subprocess.CompletedProcess([], 0, json.dumps(status), "secret-account-error")
            with patch.object(setup.subprocess, "run", return_value=result):
                if expected:
                    setup.check_auth(["claude"], {})
                else:
                    with self.assertRaises(setup.SetupError):
                        setup.check_auth(["claude"], {})

    def test_detection_is_credential_free_and_checks_actual_client_interface(self):
        outputs = [subprocess.CompletedProcess([], 0, "2.1.263 (Claude Code)\n", ""),
                   subprocess.CompletedProcess([], 0, "--settings --model --print", "")]
        with patch.dict(os.environ, {"TOKENLAB_API_KEY": "secret-token"}), patch.object(setup.shutil, "which", return_value="claude"), patch.object(setup.subprocess, "run", side_effect=outputs) as run:
            self.assertEqual(setup.detect_claude()[1], "2.1.263")
            for call in run.call_args_list:
                self.assertNotIn("TOKENLAB_API_KEY", call.kwargs["env"])
                self.assertNotEqual(call.kwargs["env"]["CLAUDE_CONFIG_DIR"], str(self.root))
        outputs[0] = subprocess.CompletedProcess([], 0, "2.1.262 (Claude Code)", "")
        with patch.object(setup.shutil, "which", return_value="claude"), patch.object(setup.subprocess, "run", side_effect=outputs), self.assertRaises(setup.SetupError):
            setup.detect_claude()


if __name__ == "__main__":
    unittest.main()

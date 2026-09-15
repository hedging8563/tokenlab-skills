import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "skills/tokenlab-api-integration/scripts/configure_codex.py"
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location("configure_codex", SCRIPT)
setup = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = setup
spec.loader.exec_module(setup)


class ConfigureCodexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tokenlab-setup-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "codex"
        self.root.mkdir()
        self.base = b'''# Keep my existing setup\nmodel = "existing-model"\nmodel_provider = "existing"\napproval_policy = "on-request"\nsandbox_mode = "read-only"\n[model_providers.existing]\nname = "Existing"\nbase_url = "https://example.invalid/v1"\nwire_api = "responses"\nhttp_headers = { Authorization = "secret-existing-header" }\n'''
        (self.root / "config.toml").write_bytes(self.base)
        (self.root / "auth.json").write_text('{"token":"secret-existing-account"}')
        self.content = setup.render_profile("tokenlab", "gpt-test", "xhigh")

    def plan(self, content=None, restore=False):
        return setup.prepare(self.root, "tokenlab", self.content if content is None else content, restore)

    def snapshot(self):
        return {p.name: (p.read_bytes(), p.stat().st_mtime_ns, p.stat().st_mode) for p in self.root.iterdir()}

    def run_main(self, *args):
        output = io.StringIO()
        with patch.object(setup, "detect_codex", return_value=("codex", "0.149.0")), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = setup.main(["--codex-home", str(self.root), *args])
        return code, output.getvalue()

    def test_preview_does_not_write_or_disclose_existing_configuration(self):
        before = self.snapshot()
        code, output = self.run_main("--model", "gpt-test")
        self.assertEqual(code, 0)
        self.assertIn("Preview: create", output)
        self.assertNotIn("secret-", output)
        self.assertEqual(self.snapshot(), before)
        self.root = self.root / "not-created"
        self.assertEqual(self.run_main("--model", "gpt-test")[0], 0)
        self.assertFalse(self.root.exists())

    def test_create_is_an_independent_profile_and_preserves_accounts_and_permissions(self):
        before = self.snapshot()
        setup.apply(self.plan())
        config = tomllib.loads((self.root / "tokenlab.config.toml").read_text())
        self.assertEqual(config["model"], "gpt-test")
        self.assertEqual(config["model_provider"], "tokenlab")
        self.assertEqual(config["model_reasoning_effort"], "xhigh")
        self.assertEqual(config["model_providers"]["tokenlab"], {
            "name": "TokenLab", "base_url": "https://api.tokenlab.sh/v1",
            "wire_api": "responses", "env_key": "TOKENLAB_API_KEY",
        })
        self.assertNotIn("approval_policy", config)
        self.assertNotIn("sandbox_mode", config)
        for name, value in before.items():
            self.assertEqual(self.snapshot()[name], value)

    def test_repeat_is_noop_including_backup_and_timestamps(self):
        setup.apply(self.plan())
        before = self.snapshot()
        self.assertEqual(self.plan().action, "unchanged")
        setup.apply(self.plan())
        self.assertEqual(self.snapshot(), before)

    def test_backup_update_restore_and_remove_initial_profile(self):
        setup.apply(self.plan())
        initial = (self.root / "tokenlab.config.toml").read_bytes()
        newer = setup.render_profile("tokenlab", "other-model", "high")
        update = self.plan(newer)
        setup.apply(update)
        self.assertEqual(update.backup_path.read_bytes(), initial)
        setup.apply(self.plan(restore=True))
        self.assertEqual(update.target.read_bytes(), initial)
        self.assertFalse(update.backup_path.exists())
        setup.apply(self.plan(restore=True))
        self.assertFalse(update.target.exists())
        self.assertEqual(self.plan(restore=True).action, "unchanged")
        self.assertEqual((self.root / "config.toml").read_bytes(), self.base)

    def test_same_name_and_edited_files_are_not_taken_over(self):
        target = self.root / "tokenlab.config.toml"
        for content in [b'model = "mine"\n', self.content + b"# my edit\n"]:
            target.write_bytes(content)
            with self.assertRaises(setup.SetupError):
                self.plan()
            with self.assertRaises(setup.SetupError):
                self.plan(restore=True)
            self.assertEqual(target.read_bytes(), content)

    def test_existing_provider_or_legacy_profile_requires_another_name(self):
        for table in ["model_providers", "profiles"]:
            (self.root / "config.toml").write_bytes(self.base + f'\n[{table}.tokenlab]\nname="mine"\n'.encode())
            with self.assertRaises(setup.SetupError):
                self.plan()
        (self.root / "config.toml").write_text('model_providers = "secret-invalid-table"')
        self.assertEqual(self.run_main("--model", "gpt-test")[0], 1)

    def test_invalid_toml_and_unknown_cli_arguments_do_not_echo_secrets(self):
        (self.root / "config.toml").write_text('model = "secret-malformed')
        code, output = self.run_main("--model", "gpt-test")
        self.assertEqual(code, 1)
        self.assertNotIn("secret-malformed", output)
        output = io.StringIO()
        with contextlib.redirect_stderr(output), self.assertRaises(SystemExit):
            setup.main(["--api-key", "sk-secret-in-argument"])
        self.assertNotIn("sk-secret-in-argument", output.getvalue())

    def test_name_and_model_validation_prevents_paths_and_config_injection(self):
        for name in ["../tokenlab", "openai", "tokenlab/other", "tokenlab\nsecret"]:
            with self.assertRaises(setup.SetupError):
                setup.render_profile(name, "gpt-test", None)
        for model in ['x"\nsandbox_mode="danger-full-access"', "sk-secret", "bad model"]:
            with self.assertRaises(setup.SetupError):
                setup.render_profile("tokenlab", model, None)

    def test_modified_backup_and_missing_profile_are_conflicts(self):
        setup.apply(self.plan())
        update = self.plan(setup.render_profile("tokenlab", "other-model", None))
        setup.apply(update)
        backup = update.backup_path.read_bytes()
        update.backup_path.write_bytes(backup + b"# edited\n")
        with self.assertRaises(setup.SetupError):
            self.plan(restore=True)
        update.backup_path.write_bytes(backup)
        update.target.unlink()
        with self.assertRaises(setup.SetupError):
            self.plan()

    def test_changes_after_preview_are_preserved(self):
        create = self.plan()
        create.target.write_text('model = "concurrent-user"\n')
        with self.assertRaises(setup.SetupError):
            setup.apply(create)
        self.assertIn("concurrent-user", create.target.read_text())
        create.target.unlink()
        create = self.plan()
        (self.root / "config.toml").write_bytes(self.base + b"\n# user edit\n")
        with self.assertRaises(setup.SetupError):
            setup.apply(create)
        self.assertFalse(create.target.exists())

    def test_failed_replace_keeps_previous_profile_and_recoverable_backup(self):
        setup.apply(self.plan())
        update = self.plan(setup.render_profile("tokenlab", "other-model", None))
        original_replace = os.replace
        def fail_profile(source, target):
            if Path(target) == update.target:
                raise OSError("simulated interruption")
            return original_replace(source, target)
        with patch.object(setup.os, "replace", side_effect=fail_profile), self.assertRaises(OSError):
            setup.apply(update)
        self.assertEqual(update.target.read_bytes(), self.content)
        self.assertEqual(update.backup_path.read_bytes(), self.content)
        setup.apply(self.plan(restore=True))
        self.assertEqual(update.target.read_bytes(), self.content)
        self.assertFalse(update.backup_path.exists())

    def test_lock_is_not_removed_when_owned_by_another_run(self):
        lock = self.root / ".tokenlab.tokenlab-setup.lock"
        lock.write_text("other run")
        with self.assertRaises(setup.SetupError):
            setup.apply(self.plan())
        self.assertEqual(lock.read_text(), "other run")

    def test_linked_profile_does_not_modify_an_external_file(self):
        outside = Path(self.temp.name) / "outside.toml"
        outside.write_bytes(self.content)
        target = self.root / "tokenlab.config.toml"
        try:
            target.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink creation is not available to this test user")
        with self.assertRaises(setup.SetupError):
            self.plan(restore=True)
        target.unlink()
        os.link(outside, target)
        with self.assertRaises(setup.SetupError):
            self.plan()
        self.assertEqual(outside.read_bytes(), self.content)

    def test_read_only_base_config_can_use_a_dotfiles_symlink(self):
        outside = Path(self.temp.name) / "dotfiles-config.toml"
        outside.write_bytes(self.base)
        base = self.root / "config.toml"
        base.unlink()
        try:
            base.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink creation is not available to this test user")
        setup.apply(self.plan())
        self.assertTrue(base.is_symlink())
        self.assertEqual(outside.read_bytes(), self.base)

    def test_codex_detection_is_isolated_and_requires_profile_file_support(self):
        outputs = [subprocess.CompletedProcess([], 0, "codex-cli 0.149.0\n", ""),
                   subprocess.CompletedProcess([], 0, "--profile Layer $CODEX_HOME/<name>.config.toml", "")]
        with patch.dict(os.environ, {"TOKENLAB_API_KEY": "secret-key"}), patch.object(setup.shutil, "which", return_value="codex"), patch.object(setup.subprocess, "run", side_effect=outputs) as run:
            self.assertEqual(setup.detect_codex()[1], "0.149.0")
            for call in run.call_args_list:
                self.assertNotIn("TOKENLAB_API_KEY", call.kwargs["env"])
                self.assertNotEqual(call.kwargs["env"]["CODEX_HOME"], str(self.root))
        outputs[0] = subprocess.CompletedProcess([], 0, "codex-cli 0.133.0\n", "")
        with patch.object(setup.shutil, "which", return_value="codex"), patch.object(setup.subprocess, "run", side_effect=outputs), self.assertRaises(setup.SetupError):
            setup.detect_codex()


if __name__ == "__main__":
    unittest.main()

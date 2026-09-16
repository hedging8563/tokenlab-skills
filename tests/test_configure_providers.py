"""Provider insertion preserves existing data, selection, and recoverable originals."""

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/tokenlab-api-integration/scripts"
sys.path.insert(0, str(SCRIPTS))
import configure_opencode
import configure_pi
import provider_config as shared


class ConfigureProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tokenlab-provider-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.target = self.root / "models.json"
        self.original = b'\xef\xbb\xbf{\r\n  // Keep my account and selection\r\n  "model": "existing/model",\r\n  "permission": {"*":"ask"},\r\n  "providers": { "existing": {"apiKey":"secret-existing"}}\r\n}\r\n'
        self.target.write_bytes(self.original)

    def plan(self, *, model="gpt-test", restore=False, guards=None):
        return shared.prepare(self.target, "Pi", "providers", "tokenlab", configure_pi.provider(model),
                              restore=restore, trailing_commas=True, block_comments=False, guards=guards)

    def snapshot(self):
        return {p.name: (p.read_bytes(), p.stat().st_mtime_ns, p.stat().st_mode)
                for p in self.root.iterdir() if p.is_file()}

    def test_preview_insertion_preserves_every_original_byte_and_existing_values(self):
        before = self.snapshot()
        plan = self.plan()
        self.assertEqual(self.snapshot(), before)
        _, _, original = shared.parse(self.original)
        _, _, actual = shared.parse(plan.after)
        expected = json.loads(json.dumps(original))
        expected["providers"]["tokenlab"] = {
            "baseUrl": "https://api.tokenlab.sh/v1", "api": "openai-completions",
            "apiKey": "$TOKENLAB_API_KEY", "models": [{"id": "gpt-test"}],
        }
        self.assertEqual(actual, expected)
        body = plan.after[3:].split(b"\n", 1)[1]
        remaining = iter(body)
        self.assertTrue(all(byte in remaining for byte in self.original[3:]))
        self.assertEqual(list(actual["providers"]), ["existing", "tokenlab"])
        self.assertEqual(plan.action, "configure")

    def test_apply_repeat_update_and_restore_original_bytes(self):
        shared.apply(self.plan())
        before = self.snapshot()
        repeat = self.plan()
        self.assertEqual(repeat.action, "unchanged")
        shared.apply(repeat)
        self.assertEqual(self.snapshot(), before)
        shared.apply(self.plan(model="gpt-new"))
        self.assertEqual(shared.parse(self.target.read_bytes())[2]["providers"]["tokenlab"]["models"],
                         [{"id": "gpt-new"}])
        shared.apply(self.plan(restore=True))
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assertEqual(set(self.snapshot()), {"models.json"})
        self.assertEqual(self.plan(restore=True).action, "unchanged")

    def test_new_file_is_removed_on_restore_without_creating_preview_directories(self):
        self.target = self.root / "new" / "models.json"
        plan = self.plan()
        self.assertFalse(self.target.parent.exists())
        shared.apply(plan)
        self.assertTrue(self.target.exists())
        shared.apply(self.plan(restore=True))
        self.assertFalse(self.target.exists())
        self.assertFalse(plan.backup_path.exists())

    def test_duplicate_provider_or_unrelated_managed_file_is_not_taken_over(self):
        for value in (b'{"providers":{"tokenlab":{"apiKey":"secret-user"}}}',
                      b'// TokenLab other setup\n{}', b'{"providers":null}'):
            self.target.write_bytes(value)
            with self.assertRaises(shared.SetupError):
                self.plan()
            self.assertEqual(self.target.read_bytes(), value)

    def test_modified_configuration_backup_and_missing_original_are_conflicts(self):
        for kind in ("config", "backup", "missing"):
            with self.subTest(kind=kind):
                self.target.write_bytes(self.original)
                backup = self.target.with_name(".models.json.tokenlab.tokenlab-backup")
                backup.unlink(missing_ok=True)
                shared.apply(self.plan())
                if kind == "missing":
                    self.target.unlink()
                else:
                    path = self.target if kind == "config" else backup
                    path.write_bytes(path.read_bytes() + b"\n// user edit")
                before = self.snapshot()
                for restoring in (False, True):
                    with self.assertRaises(shared.SetupError):
                        self.plan(restore=restoring)
                self.assertEqual(self.snapshot(), before)

    def test_interrupted_write_retains_original_and_can_resume_or_restore(self):
        real_write = shared.atomic_write

        def interrupt_target(path, content, expected):
            if path == self.target:
                raise OSError("simulated interrupted write")
            real_write(path, content, expected)

        with patch.object(shared, "atomic_write", side_effect=interrupt_target), self.assertRaises(OSError):
            shared.apply(self.plan())
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assertTrue(self.plan().backup_path.exists())
        shared.apply(self.plan())
        with patch.object(Path, "unlink", side_effect=OSError("simulated backup cleanup interruption")), self.assertRaises(OSError):
            shared.apply(self.plan(restore=True))
        # Atomic restoration may complete before its backup/lock cleanup. Simulate
        # manual lock removal only after that interrupted process has exited.
        (self.root / ".models.json.tokenlab-setup.lock").unlink(missing_ok=True)
        shared.apply(self.plan(restore=True))
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assertFalse(self.plan().backup_path.exists())

    def test_target_backup_and_auth_changes_after_preview_stop_the_write(self):
        auth = self.root / "auth.json"
        auth.write_bytes(b'{"existing":{"key":"secret-user"}}')
        plan = self.plan(guards={auth: auth.read_bytes()})
        auth.write_bytes(b'{"tokenlab":{"key":"secret-concurrent"}}')
        with self.assertRaises(shared.SetupError):
            shared.apply(plan)
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assertFalse(plan.backup_path.exists())
        plan = self.plan()
        self.target.write_bytes(self.original + b"\r\n")
        with self.assertRaises(shared.SetupError):
            shared.apply(plan)
        self.target.write_bytes(self.original)
        plan.backup_path.write_bytes(b"user-owned-file")
        with self.assertRaises(shared.SetupError):
            shared.apply(plan)
        self.assertEqual(plan.backup_path.read_bytes(), b"user-owned-file")

    def test_saved_auth_conflict_does_not_echo_values_or_change_files(self):
        auth = self.root / "auth.json"
        content = b'{"tokenlab":{"key":"secret-account"}}'
        auth.write_bytes(content)
        with self.assertRaises(shared.SetupError) as error:
            shared.reject_saved_credential(auth, "tokenlab")
        self.assertNotIn("secret-account", str(error.exception))
        self.assertEqual(shared.reject_saved_credential(auth, "tokenlab-personal"), content)

    def test_existing_lock_is_retained(self):
        lock = self.root / ".models.json.tokenlab-setup.lock"
        lock.write_bytes(b"another process")
        with self.assertRaises(shared.SetupError):
            shared.apply(self.plan())
        self.assertEqual(lock.read_bytes(), b"another process")
        self.assertEqual(self.target.read_bytes(), self.original)

    def test_links_are_not_overwritten(self):
        outside = self.root / "outside.json"
        outside.write_bytes(self.original)
        self.target.unlink()
        try:
            self.target.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink creation unavailable to this user")
        with self.assertRaises(shared.SetupError):
            self.plan()
        self.target.unlink()
        os.link(outside, self.target)
        with self.assertRaises(shared.SetupError):
            self.plan()
        self.assertEqual(outside.read_bytes(), self.original)

    def test_no_secrets_or_unsafe_names_are_accepted_as_arguments(self):
        for module in (configure_opencode, configure_pi):
            for model in ('sk-secret-key', 'model\nsecret', 'model"escape', 'bad model'):
                with self.assertRaises(shared.SetupError):
                    module.provider(model)
            output = io.StringIO()
            with contextlib.redirect_stderr(output), self.assertRaises(SystemExit):
                module.main(["--api-key", "sk-secret-key"])
            self.assertNotIn("sk-secret-key", output.getvalue())
        for name in ("openai", "../tokenlab", "tokenlab/other", "tokenlab\n"):
            with self.assertRaises(shared.SetupError):
                shared.check_provider(name)


class JsoncInsertionTests(unittest.TestCase):
    def test_comments_strings_unicode_and_trailing_commas_are_preserved(self):
        examples = [b'{}', b'{/* retain */}', b'{"keep":"https://example.test/*x*/,]"}',
                    '{"注释":"保留 \\\" //", "provider":{ //next\r\n"existing":{},},}'.encode(),
                    b'{"provider":{},"array":[{"nested":[1,2,],},],}']
        for original in examples:
            with self.subTest(original=original):
                desired = configure_opencode.provider("gpt-test")
                actual = shared.insert_provider(original, "provider", "tokenlab", desired, trailing_commas=True)
                before = shared.parse(original, trailing_commas=True)[2]
                before.setdefault("provider", {})["tokenlab"] = desired
                self.assertEqual(shared.parse(actual, trailing_commas=True)[2], before)

    def test_invalid_json_and_duplicate_keys_fail_safely(self):
        for value in (b'[]', b'{"secret":NaN}', b'{"a":1,"a":2}',
                      b'{"provider":{"a":1,"a":2}}', b'{"a":1,,}',
                      b'{,}', b'{"a":[,]}', b'{"a":1} trailing-secret',
                      b'{/* unterminated-secret', b'\xff'):
            with self.subTest(value=value), self.assertRaises(shared.SetupError) as error:
                shared.parse(value, trailing_commas=True)
            self.assertNotIn("secret", str(error.exception))

    def test_pi_accepts_line_comments_and_trailing_commas_but_not_block_comments(self):
        actual = shared.insert_provider(b'{"providers":{}, // keep\n}', "providers", "tokenlab",
                                        configure_pi.provider("gpt-test"), trailing_commas=True, block_comments=False)
        self.assertIn("tokenlab", shared.parse(actual, trailing_commas=True, block_comments=False)[2]["providers"])
        with self.assertRaises(shared.SetupError):
            shared.insert_provider(b'{/* unsupported by Pi */ "providers":{}}', "providers", "tokenlab",
                                   configure_pi.provider("gpt-test"), trailing_commas=True, block_comments=False)


class ProviderCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tokenlab-provider-cli-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_helper(self, module, *args, environment=None):
        output = io.StringIO()
        env = {"HOME": str(self.root), "USERPROFILE": str(self.root), **(environment or {})}
        with patch.dict(os.environ, env, clear=True), patch.object(module, "inspect_client", return_value="1.18.31"), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = module.main(list(args))
        return code, output.getvalue()

    def test_cli_preview_apply_and_restore_without_client(self):
        for module, option, target in ((configure_opencode, "--config", self.root / "tokenlab-personal.jsonc"),
                                       (configure_pi, "--agent-dir", self.root / "pi")):
            args = [option, str(target), "--provider", "tokenlab-personal", "--model", "gpt-test"]
            env = {"HOME": str(self.root), "USERPROFILE": str(self.root), "TOKENLAB_API_KEY": "sk-environment-fixture"}
            code, output = self.run_helper(module, *args, environment=env)
            self.assertEqual(code, 0, output)
            self.assertIn("Preview: configure", output)
            self.assertIn("tokenlab-personal", output)
            self.assertNotIn("sk-environment-fixture", output)
            self.assertFalse(target.exists())
            code, output = self.run_helper(module, *args, "--apply", environment=env)
            self.assertEqual(code, 0, output)
            for file in self.root.rglob("*"):
                if file.is_file():
                    self.assertNotIn(b"sk-environment-fixture", file.read_bytes())
            with patch.object(module, "inspect_client", side_effect=AssertionError("restore must not require client")):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(module.main([option, str(target), "--provider", "tokenlab-personal", "--restore", "--apply"]), 0)

    def test_opencode_uses_opt_in_layer_and_rejects_automatic_config_filenames(self):
        config = self.root / "opencode"
        config.mkdir()
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.root)}, clear=True):
            self.assertEqual(configure_opencode.config_path(None), config / "tokenlab.jsonc")
            (config / "opencode.json").write_bytes(b"{}")
            self.assertEqual(configure_opencode.config_path(None), config / "tokenlab.jsonc")
            (config / "opencode.jsonc").write_bytes(b"{}")
            for name in ("config.json", "opencode.json", "opencode.jsonc", "OPENCODE.JSON"):
                with self.assertRaises(shared.SetupError):
                    configure_opencode.config_path(config / name)

    def test_legacy_and_custom_directory_providers_are_conflict_guarded(self):
        for filename in ("config.json", "opencode.json", "opencode.jsonc"):
            config_root = self.root / filename / "opencode"
            config_root.mkdir(parents=True)
            (config_root / filename).write_bytes(b'{"provider":{"tokenlab":{"name":"secret-old"}}}')
            code, output = self.run_helper(configure_opencode, "--model", "gpt-test", "--apply",
                                           environment={"XDG_CONFIG_HOME": str(config_root.parent)})
            self.assertEqual(code, 1, output)
            self.assertNotIn("secret-old", output)
            self.assertFalse((config_root / "tokenlab.jsonc").exists())
        extra = self.root / "custom"
        extra.mkdir()
        (extra / "opencode.jsonc").write_bytes(b'{"provider":{"tokenlab":{}}}')
        code, output = self.run_helper(configure_opencode, "--model", "gpt-test", "--apply",
                                       environment={"OPENCODE_CONFIG_DIR": str(extra)})
        self.assertEqual(code, 1, output)
        code, output = self.run_helper(configure_opencode, "--model", "gpt-test", "--apply",
                                       environment={"OPENCODE_CONFIG": str(self.root / "existing-custom.jsonc")})
        self.assertEqual(code, 1, output)

    def test_empty_environment_paths_fall_back_to_home(self):
        env = {"HOME": str(self.root), "USERPROFILE": str(self.root), "XDG_CONFIG_HOME": "",
               "XDG_DATA_HOME": "", "PI_CODING_AGENT_DIR": ""}
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(configure_opencode.config_path(None), self.root / ".config" / "opencode" / "tokenlab.jsonc")
        auth = self.root / ".local" / "share" / "opencode" / "auth.json"
        auth.parent.mkdir(parents=True)
        auth.write_bytes(b'{"tokenlab":{}}')
        self.assertEqual(self.run_helper(configure_opencode, "--model", "gpt-test", "--apply", environment=env)[0], 1)
        code, output = self.run_helper(configure_pi, "--model", "gpt-test", "--apply", environment=env)
        self.assertEqual(code, 0, output)
        self.assertTrue((self.root / ".pi" / "agent" / "models.json").exists())

    def test_provider_allowlists_and_inline_config_are_not_overridden(self):
        config = self.root / "tokenlab.jsonc"
        for content in ({"disabled_providers": ["tokenlab"]}, {"enabled_providers": ["other"]},
                        {"enabled_providers": None}, {"disabled_providers": "secret-invalid"}):
            config.write_text(json.dumps(content))
            original = config.read_bytes()
            code, output = self.run_helper(configure_opencode, "--config", str(config), "--model", "gpt-test", "--apply")
            self.assertEqual(code, 1, output)
            self.assertNotIn("secret-invalid", output)
            self.assertEqual(config.read_bytes(), original)
        config.write_bytes(b"{}")
        code, output = self.run_helper(configure_opencode, "--config", str(config), "--model", "gpt-test", "--apply",
                                       environment={"OPENCODE_CONFIG_CONTENT": "secret-inline"})
        self.assertEqual(code, 1)
        self.assertNotIn("secret-inline", output)
        self.assertEqual(config.read_bytes(), b"{}")

    def test_client_detection_strips_credentials_and_rejects_unsupported_version(self):
        result = subprocess.CompletedProcess([], 0, stdout="1.18.31\n", stderr="")
        def inspect(command, **kwargs):
            self.assertEqual(command[-1], "--version")
            self.assertNotIn("TOKENLAB_API_KEY", kwargs["env"])
            self.assertNotIn("OPENCODE_CONFIG", kwargs["env"])
            self.assertNotIn("NODE_OPTIONS", kwargs["env"])
            self.assertTrue(Path(kwargs["env"]["HOME"]).is_dir())
            self.assertEqual(kwargs["env"]["HOME"], kwargs["cwd"])
            return result
        with patch.dict(os.environ, {"TOKENLAB_API_KEY": "secret-env", "OPENCODE_CONFIG": "/private/config", "NODE_OPTIONS": "secret-option"}), patch.object(shared.shutil, "which", return_value=sys.executable), patch.object(shared.subprocess, "run", side_effect=inspect):
            self.assertEqual(shared.inspect_client("opencode", None, (1, 18, 31)), "1.18.31")
            result.stdout = "1.18.30"
            with self.assertRaises(shared.SetupError):
                shared.inspect_client("opencode", None, (1, 18, 31))


if __name__ == "__main__":
    unittest.main()

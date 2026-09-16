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
import configure_hermes as setup
import provider_config as files
from hermes_yaml import insert_provider
from setup_files import SetupError


class HermesYamlTests(unittest.TestCase):
    def insert(self, source):
        return insert_provider(source, "providers", "tokenlab", setup.provider("gpt-5.6-luna"))

    def test_lossless_insertion_and_original_default_permissions(self):
        import yaml
        for newline in ("\n", "\r\n"):
            source = ("# untouched comment\nmodel:\n  provider: openrouter\n  default: 'original' # choice\n"
                      "providers:\n  existing:\n    api: 'https://example.invalid' # URL\n"
                      "# next section comment\napprovals:\n  mode: manual\nterminal:\n  backend: docker\n").replace("\n", newline).encode()
            result = self.insert(source)
            added = ('  "tokenlab":' + newline + '    "api": "https://api.tokenlab.sh/v1"' + newline
                     + '    "key_env": "TOKENLAB_API_KEY"' + newline + '    "transport": "chat_completions"' + newline
                     + '    "default_model": "gpt-5.6-luna"' + newline).encode()
            self.assertEqual(result.replace(added, b""), source)
            before, after = yaml.safe_load(source), yaml.safe_load(result)
            del after["providers"]["tokenlab"]
            self.assertEqual(before, after)

    def test_empty_flow_bom_unicode_document_end_and_no_final_newline(self):
        import yaml
        for source in (None, b"", b"# comment\n", b"{}", b"providers: {} # empty\n",
                       b'providers: {old: {api: "http://localhost"}}\n',
                       b"---\nmodel: {provider: openrouter}\n...\n",
                       b"model:\n  provider: openrouter", "\ufeff# 原注释\nmodel: old\n".encode()):
            with self.subTest(source=source):
                self.assertEqual(yaml.safe_load(self.insert(source))["providers"]["tokenlab"], setup.provider("gpt-5.6-luna"))

    def test_rejects_ambiguous_yaml_and_collision_without_echoing_values(self):
        for source in (b"providers: []\n", b"providers: null\n", b"providers:\n  tokenlab: {}\n",
                       b"model: one\nmodel: two\n", b"providers: {}\nproviders: {}\n", b"[one, two]\n",
                       b"a: &a {x: 1}\nproviders:\n  <<: *a\n", b"---\na: 1\n---\nb: 2\n",
                       b"model: {provider: 'custom:tokenlab'}\n", b"providers: &p {}\nother: *p\n",
                       b"bad: !!python/object:secret {}\n", b"x: \xff\n"):
            with self.subTest(source=source), self.assertRaises(SetupError) as caught:
                self.insert(source)
            self.assertNotIn("secret", str(caught.exception))


class HermesLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.target = self.root / "config.yaml"
        self.original = b"# preserve me\nmodel: {provider: openrouter, default: old}\n"
        self.target.write_bytes(self.original)

    def tearDown(self):
        self.temp.cleanup()

    def plan(self, model="gpt-5.6-luna", restore=False, guards=None):
        return files.prepare(self.target, "Hermes", "providers", "tokenlab", None if restore else setup.provider(model),
                             restore=restore, guards=guards, insert=insert_provider, comment="#")

    def test_preview_apply_repeat_update_exact_restore(self):
        initial = self.plan()
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assertFalse(initial.backup_path.exists())
        files.apply(initial)
        installed = self.target.read_bytes()
        self.assertTrue(installed.startswith(b"# TokenLab Hermes setup"))
        self.assertEqual(self.plan().action, "unchanged")
        files.apply(self.plan("gpt-5.6-terra"))
        self.assertNotEqual(self.target.read_bytes(), installed)
        files.apply(self.plan(restore=True))
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assertFalse(initial.backup_path.exists())

    def test_missing_file_restores_to_missing(self):
        self.target.unlink()
        files.apply(self.plan())
        files.apply(self.plan(restore=True))
        self.assertFalse(self.target.exists())

    def test_refuses_later_edits_and_invalid_backup(self):
        plan = self.plan()
        files.apply(plan)
        self.target.write_bytes(self.target.read_bytes() + b"# user edit\n")
        for restoring in (True, False):
            with self.assertRaises(SetupError):
                self.plan(restore=restoring)
        self.target.write_bytes(plan.after)
        plan.backup_path.write_bytes(b"bad backup\n")
        with self.assertRaises(SetupError):
            self.plan(restore=True)

    def test_rejects_concurrent_config_and_account_changes(self):
        plan = self.plan()
        self.target.write_bytes(self.original + b"# edited\n")
        with self.assertRaises(SetupError):
            files.apply(plan)
        self.target.write_bytes(self.original)
        auth = self.root / "auth.json"
        auth.write_bytes(b"{}")
        plan = self.plan(guards={auth: b"{}"})
        auth.write_bytes(b'{"changed":true}')
        with self.assertRaises(SetupError):
            files.apply(plan)
        self.assertFalse(plan.backup_path.exists())

    def test_interrupted_after_backup_can_finish_or_restore(self):
        plan = self.plan()
        plan.backup_path.write_bytes(plan.backup_after)
        files.apply(self.plan())
        self.assertEqual(self.target.read_bytes(), plan.after)
        self.target.write_bytes(self.original)
        files.apply(self.plan(restore=True))
        self.assertFalse(plan.backup_path.exists())

    def test_linked_config_is_refused(self):
        original = self.root / "original.yaml"
        self.target.rename(original)
        try:
            self.target.symlink_to(original)
        except OSError:
            self.skipTest("Symlink creation unavailable on this host")
        with self.assertRaises(SetupError):
            self.plan()

    def test_restore_works_without_yaml_or_client(self):
        files.apply(self.plan())
        with patch.dict(sys.modules, {"yaml": None}), patch.object(setup, "inspect_client", side_effect=AssertionError("must not inspect")):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(setup.main(["--hermes-home", str(self.root), "--restore", "--apply"]), 0)
        self.assertEqual(self.target.read_bytes(), self.original)


class HermesDetectionTests(unittest.TestCase):
    def test_version_uses_client_version_not_release_date(self):
        result = subprocess.CompletedProcess([], 0, "Hermes Agent v0.21.3 (2026.9.14) · upstream 547c3d49\n")
        with patch.object(files.shutil, "which", return_value=sys.executable), patch.object(files.subprocess, "run", return_value=result):
            self.assertEqual(files.inspect_client("hermes", None, (0, 21, 3)), "0.21.3")

    def test_windows_default_and_sticky_profile_resolution(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"LOCALAPPDATA": directory}, clear=True), patch.object(setup.sys, "platform", "win32"):
            native = Path(directory) / "hermes"
            native.mkdir()
            (native / "profiles" / "work").mkdir(parents=True)
            (native / "active_profile").write_text("work\n")
            selected, guards = setup.resolve_home(None)
            self.assertEqual(selected, native / "profiles" / "work")
            self.assertIn(native / "active_profile", guards)
            self.assertEqual(setup.resolve_home(native)[0], native)

    def test_managed_overrides_wsl_and_saved_account_collisions(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            root = Path(directory)
            for env in ({"WSL_DISTRO_NAME": "Ubuntu"}, {"HERMES_MANAGED": "nix"},
                        {"HERMES_IGNORE_USER_CONFIG": "1"}, {"HERMES_MANAGED_DIR": directory}):
                with patch.dict(os.environ, env, clear=True), self.assertRaises(SetupError):
                    setup.inspect_settings(root, "tokenlab")
            for doc in ({"providers": {"custom:tokenlab": {}}}, {"credential_pool": {"tokenlab": []}},
                        {"active_provider": "custom:tokenlab"}, {"providers": []}):
                (root / "auth.json").write_text(json.dumps(doc))
                with self.assertRaises(SetupError):
                    setup.inspect_settings(root, "tokenlab")

    def test_cli_rejects_unverified_version_and_secret_arguments(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(setup, "inspect_client", return_value="0.21.4"), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(setup.main(["--hermes-home", directory, "--model", "gpt-5.6-luna"]), 1)
            self.assertEqual(list(Path(directory).iterdir()), [])
        result = subprocess.run([sys.executable, str(SCRIPTS / "configure_hermes.py"), "--key", "sk-never-print-this"], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("sk-never-print-this", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()

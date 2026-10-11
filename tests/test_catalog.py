"""Check that the skill folders, catalog.json, generated files, and manifests agree."""

import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GROUPS = ['foundation', 'image', 'video', 'audio', '3d', 'decision', 'integration']


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sync_catalog = load_module('sync_catalog', ROOT / 'scripts/sync_catalog.py')
sync_models = load_module('sync_models', ROOT / 'scripts/sync_models.py')
CATALOG = json.loads((ROOT / 'catalog.json').read_text())
FOLDERS = sorted(p.name for p in (ROOT / 'skills').iterdir() if p.is_dir())


def frontmatter(path):
    text = path.read_text()
    match = re.match(r'---\n(.*?)\n---\n', text, re.S)
    if not match:
        raise AssertionError(f'{path} has no frontmatter')
    fields = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(':')
        if sep and not line.startswith(' '):
            value = value.strip()
            fields[key.strip()] = json.loads(value) if value.startswith('"') else value
    return fields, text[match.end():]


class SkillFolderTests(unittest.TestCase):
    def test_every_folder_has_a_skill_named_like_the_folder(self):
        for folder in FOLDERS:
            with self.subTest(folder=folder):
                fields, body = frontmatter(ROOT / 'skills' / folder / 'SKILL.md')
                self.assertEqual(fields.get('name'), folder)
                self.assertEqual(fields.get('license'), 'MIT')
                self.assertTrue(body.strip())

    def test_descriptions_are_within_the_specification_bounds(self):
        for folder in FOLDERS:
            with self.subTest(folder=folder):
                description = frontmatter(ROOT / 'skills' / folder / 'SKILL.md')[0].get('description', '')
                self.assertGreaterEqual(len(description), 80)
                self.assertLessEqual(len(description), 1024)

    def test_outcome_skills_name_a_sibling_and_the_run_skill(self):
        for skill in CATALOG['skills']:
            if skill['group'] not in ('image', 'video', 'audio', '3d', 'decision'):
                continue
            with self.subTest(skill=skill['id']):
                body = (ROOT / skill['path'] / 'SKILL.md').read_text()
                self.assertIn('tokenlab-run', body)
                self.assertTrue((ROOT / skill['path'] / 'README.md').is_file())
                self.assertTrue((ROOT / skill['path'] / 'agents/openai.yaml').is_file())


class CatalogTests(unittest.TestCase):
    def test_catalog_ids_match_the_skill_folders_exactly(self):
        ids = [s['id'] for s in CATALOG['skills']]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(sorted(ids), FOLDERS)
        for skill in CATALOG['skills']:
            self.assertEqual(skill['path'], f"skills/{skill['id']}")

    def test_groups_use_the_fixed_order_and_hold_each_skill_once(self):
        self.assertEqual([g['id'] for g in CATALOG['groups']], GROUPS)
        listed = [s for g in CATALOG['groups'] for s in g['skills']]
        self.assertEqual(sorted(listed), FOLDERS)
        self.assertEqual(len(listed), len(set(listed)))
        group_of = {s: g['id'] for g in CATALOG['groups'] for s in g['skills']}
        for skill in CATALOG['skills']:
            self.assertEqual(group_of[skill['id']], skill['group'], skill['id'])

    def test_entries_are_complete_and_summaries_are_short(self):
        for skill in CATALOG['skills']:
            with self.subTest(skill=skill['id']):
                self.assertTrue(skill['summary'])
                self.assertLessEqual(len(skill['summary']), 90)
                for key in ('operations', 'endpoints', 'mcpTools'):
                    self.assertIsInstance(skill[key], list)
                for endpoint in skill['endpoints']:
                    self.assertTrue(endpoint.startswith(('/v1/', '/v1beta/')), endpoint)
        for group in CATALOG['groups']:
            self.assertTrue(group['title'] and group['description'])

    def test_generated_files_match_the_catalog(self):
        self.assertEqual(json.loads((ROOT / 'skills.sh.json').read_text()), sync_catalog.skills_sh(CATALOG))
        self.assertIn(sync_catalog.readme_section(CATALOG), (ROOT / 'README.md').read_text())
        self.assertEqual(sync_catalog.main(['--check']), 0)

    def test_readme_section_lists_every_skill_under_its_group(self):
        section = sync_catalog.readme_section(CATALOG)
        for group in CATALOG['groups']:
            start = section.index(f"**{group['title']}**")
            for skill_id in group['skills']:
                self.assertGreater(section.index(f'[`{skill_id}`]'), start)

    def test_skills_with_operations_have_one_generated_model_block(self):
        for skill in CATALOG['skills']:
            with self.subTest(skill=skill['id']):
                text = (ROOT / skill['path'] / 'SKILL.md').read_text()
                expected = 1 if skill['operations'] else 0
                self.assertEqual(len(sync_models.BLOCK.findall(text)), expected)

    def test_preferred_model_ids_appear_only_inside_the_generated_block(self):
        ids = {e if isinstance(e, str) else e['id'] for s in CATALOG['skills'] for e in s.get('preferredModels', [])}
        token = re.compile(r'[a-z0-9][a-z0-9.\-]*[a-z0-9]')
        for skill in CATALOG['skills']:
            for path in sorted((ROOT / skill['path']).rglob('*.md')):
                with self.subTest(path=str(path.relative_to(ROOT))):
                    prose = sync_models.BLOCK.sub('', path.read_text())
                    self.assertEqual(sorted(set(token.findall(prose)) & ids), [])

    def test_preferred_models_name_operations_of_their_skill(self):
        for skill in CATALOG['skills']:
            for entry in skill.get('preferredModels', []):
                if isinstance(entry, dict) and 'operation' in entry:
                    self.assertIn(entry['operation'], skill['operations'], (skill['id'], entry['id']))

    def test_availability_lists_every_skill(self):
        availability = json.loads((ROOT / 'generated/availability.json').read_text())
        self.assertEqual(sorted(availability), FOLDERS)
        for entry in availability.values():
            self.assertIn(entry['status'], ('available', 'unavailable'))

    def test_patch_bump_changes_every_manifest_together(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copy(ROOT / 'catalog.json', root / 'catalog.json')
            shutil.copytree(ROOT / '.claude-plugin', root / '.claude-plugin')
            version = sync_catalog.bump_patch(root)
            major, minor, patch = CATALOG['version'].split('.')
            self.assertEqual(version, f'{major}.{minor}.{int(patch) + 1}')
            self.assertEqual(json.loads((root / 'catalog.json').read_text())['version'], version)
            self.assertEqual(json.loads((root / '.claude-plugin/plugin.json').read_text())['version'], version)
            self.assertEqual(json.loads((root / '.claude-plugin/marketplace.json').read_text())['metadata']['version'],
                             version)

    def test_versions_agree(self):
        plugin = json.loads((ROOT / '.claude-plugin/plugin.json').read_text())
        marketplace = json.loads((ROOT / '.claude-plugin/marketplace.json').read_text())
        self.assertEqual(plugin['version'], CATALOG['version'])
        self.assertEqual(marketplace['metadata']['version'], CATALOG['version'])


if __name__ == '__main__':
    unittest.main()

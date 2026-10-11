"""Check scripts/sync_models.py against a fixture catalog, without network calls."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sync_models', ROOT / 'scripts/sync_models.py')
sync_models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync_models)

NOW = '2026-10-12T00:00:00Z'
LATER = '2026-10-13T00:00:00Z'


def model(model_id, operations, price='1', unit='per_second', stage='active', supply=None):
    return {'id': model_id, 'tokenlab': {
        'category': 'video', 'pricing_unit': unit, 'lifecycle': {'stage': stage},
        'pricing_summary': {'official_min_price': price, 'platform_min_price': None},
        'public_contract_summary': {'public_operations': operations},
        'deliveryAvailability': {'operations': supply or {}}}}


def live(*models, ranked=None):
    return {'models': list(models), 'recommended': {'video': ranked or [m['id'] for m in models]}}


SKILL_TEXT = """---
name: fixture-skill
---

# Fixture

## Models

Intro line that must stay.

{start}
old generated text
{end}

## Workflow

Steps that must stay.
""".format(start=sync_models.START, end=sync_models.END)


class FixtureRepo:
    def __init__(self, case, skills):
        tmp = tempfile.TemporaryDirectory()
        case.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for skill in skills:
            folder = self.root / skill['path']
            folder.mkdir(parents=True)
            (folder / 'SKILL.md').write_text(SKILL_TEXT)
        self.catalog = {'skills': skills}

    def build(self, snapshot, previous=None, now=NOW):
        outputs = sync_models.build(self.catalog, snapshot, root=self.root, previous=previous, now=now)
        for path, content in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        return outputs

    def skill_text(self, skill_id='skills/fixture'):
        return (self.root / skill_id / 'SKILL.md').read_text()

    def availability(self):
        return json.loads((self.root / 'generated' / 'availability.json').read_text())


def skill(operations, preferred=None, skill_id='fixture'):
    entry = {'id': skill_id, 'path': f'skills/{skill_id}', 'operations': operations}
    if preferred is not None:
        entry['preferredModels'] = preferred
    return entry


class PickTests(unittest.TestCase):
    def test_live_preferred_models_come_first_in_their_order(self):
        snapshot = live(model('a', ['image-to-video']), model('b', ['image-to-video']), model('c', ['image-to-video']))
        picked = sync_models.pick(skill(['image-to-video'], [{'id': 'b', 'use': 'Main'}, 'a']), snapshot)
        self.assertEqual([(r['id'], r['pick'], r['use']) for r in picked['image-to-video']],
                         [('b', 'default', 'Main'), ('a', 'alternative', '')])

    def test_removed_preferred_model_falls_back_to_the_ranked_list_plus_a_low_cost_option(self):
        snapshot = live(model('r1', ['image-to-video'], '5'), model('r2', ['image-to-video'], '4'),
                        model('r3', ['image-to-video'], '3'), model('r4', ['image-to-video'], '0.5'),
                        model('other', ['text-to-video'], '0.1'),
                        ranked=['r1', 'other', 'r2', 'r3', 'r4'])
        picked = sync_models.pick(skill(['image-to-video'], [{'id': 'gone-model'}]), snapshot)
        self.assertEqual([(r['id'], r['pick']) for r in picked['image-to-video']],
                         [('r1', 'default'), ('r2', 'alternative'), ('r3', 'alternative'), ('r4', 'low-cost')])

    def test_preferred_model_for_another_operation_or_without_supply_is_skipped(self):
        snapshot = live(model('a', ['image-to-video', 'text-to-video']),
                        model('b', ['image-to-video'], supply={'image-to-video': {'verified': False, 'official': False}}),
                        model('c', ['image-to-video'], stage='retired'))
        picked = sync_models.pick(skill(['image-to-video'], [{'id': 'a', 'operation': 'text-to-video'}, 'b', 'c']),
                                  snapshot)
        self.assertEqual([r['id'] for r in picked['image-to-video']], ['a'])
        self.assertEqual(picked['image-to-video'][0]['pick'], 'default')


class BuildTests(unittest.TestCase):
    def test_operation_with_no_supply_marks_the_skill_unavailable(self):
        repo = FixtureRepo(self, [skill(['motion-control'], ['gone-model'])])
        repo.build(live(model('a', ['image-to-video'])))
        self.assertEqual(repo.availability()['fixture'], {'status': 'unavailable', 'models': [], 'checkedAt': NOW})
        self.assertIn('| `motion-control` | none live | unavailable |', repo.skill_text('skills/fixture'))

    def test_one_live_operation_keeps_the_skill_available(self):
        repo = FixtureRepo(self, [skill(['motion-control', 'image-to-video'])])
        repo.build(live(model('a', ['image-to-video'])))
        self.assertEqual(repo.availability()['fixture']['status'], 'available')
        self.assertEqual(repo.availability()['fixture']['models'], ['a'])

    def test_skill_without_operations_needs_no_block(self):
        repo = FixtureRepo(self, [skill([], skill_id='guide')])
        outputs = repo.build(live(model('a', ['image-to-video'])))
        self.assertEqual(repo.availability()['guide'], {'status': 'available', 'models': [], 'checkedAt': NOW})
        self.assertNotIn(repo.root / 'skills/guide/SKILL.md', outputs)

    def test_block_is_replaced_in_place_and_a_second_run_changes_nothing(self):
        repo = FixtureRepo(self, [skill(['image-to-video'], ['a'])])
        snapshot = live(model('a', ['image-to-video']))
        repo.build(snapshot)
        first = repo.skill_text('skills/fixture')
        self.assertNotIn('old generated text', first)
        self.assertIn('Intro line that must stay.\n\n' + sync_models.START, first)
        self.assertIn(sync_models.END + '\n\n## Workflow\n\nSteps that must stay.\n', first)
        self.assertEqual(first.count(sync_models.START), 1)
        self.assertIn('| `image-to-video` | `a` | default |', first)
        first_availability = repo.availability()

        outputs = repo.build(snapshot, previous=first_availability, now=LATER)
        for path, content in outputs.items():
            self.assertEqual(path.read_text(), content)
        self.assertEqual(repo.skill_text('skills/fixture'), first)
        self.assertEqual(repo.availability(), first_availability)

    def test_changed_models_update_checked_at(self):
        repo = FixtureRepo(self, [skill(['image-to-video'], ['a', 'b'])])
        repo.build(live(model('a', ['image-to-video']), model('b', ['image-to-video'])))
        previous = repo.availability()
        repo.build(live(model('b', ['image-to-video'])), previous=previous, now=LATER)
        self.assertEqual(repo.availability()['fixture'], {'status': 'available', 'models': ['b'], 'checkedAt': LATER})

    def test_missing_or_duplicate_block_is_an_error(self):
        repo = FixtureRepo(self, [skill(['image-to-video'], ['a'])])
        path = repo.root / 'skills/fixture/SKILL.md'
        path.write_text('# No block\n')
        with self.assertRaises(ValueError):
            repo.build(live(model('a', ['image-to-video'])))
        path.write_text(SKILL_TEXT + SKILL_TEXT)
        with self.assertRaises(ValueError):
            repo.build(live(model('a', ['image-to-video'])))


if __name__ == '__main__':
    unittest.main()

"""Check scripts/sync_models.py against a fixture catalog, without network calls."""

import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

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


# Unrelated chat models keep the fixture above the catalog size floor.
FILLER = [{'id': f'filler-{i}', 'tokenlab': {'category': 'chat', 'lifecycle': {'stage': 'active'}}}
          for i in range(sync_models.MIN_MODELS)]


def live(*models, ranked=None):
    return {'models': list(models) + FILLER, 'recommended': {'video': ranked or [m['id'] for m in models]}}


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


def skill(operations, preferred=None, skill_id='fixture', **extra):
    entry = {'id': skill_id, 'path': f'skills/{skill_id}', 'operations': operations, **extra}
    if preferred is not None:
        entry['preferredModels'] = preferred
    return entry


class FixtureRepo:
    def __init__(self, case, skills):
        tmp = tempfile.TemporaryDirectory()
        case.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for entry in skills:
            folder = self.root / entry['path']
            folder.mkdir(parents=True)
            (folder / 'SKILL.md').write_text(SKILL_TEXT)
        self.catalog = {'skills': skills}

    def sync(self, snapshot, now=NOW, **options):
        return sync_models.sync(self.catalog, snapshot, root=self.root, now=now, **options)

    def files(self):
        return {p: p.read_text() for p in sorted(self.root.rglob('*')) if p.is_file()}

    def skill_text(self, skill_id='fixture'):
        return (self.root / 'skills' / skill_id / 'SKILL.md').read_text()

    def availability(self):
        return json.loads((self.root / 'generated' / 'availability.json').read_text())


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
        self.assertEqual(picked['image-to-video'][-1]['use'], sync_models.LOW_COST_USE)

    def test_specialised_operation_without_preferred_supply_is_not_filled_with_general_models(self):
        snapshot = live(model('general', ['image-edit', 'image-to-video']))
        entry = skill(['image-edit', 'image-to-video'], ['gone-model'], rankedFallback={'image-edit': False})
        picked = sync_models.pick(entry, snapshot)
        self.assertEqual(picked['image-edit'], [])
        self.assertEqual([r['id'] for r in picked['image-to-video']], ['general'])
        self.assertEqual(sync_models.pick(skill(['image-edit'], ['gone'], rankedFallback=False), snapshot),
                         {'image-edit': []})

    def test_models_for_other_operations_without_supply_or_not_active_are_skipped(self):
        snapshot = live(model('a', ['image-to-video', 'text-to-video']),
                        model('b', ['image-to-video'], supply={'image-to-video': {'verified': False, 'official': False}}),
                        model('c', ['image-to-video'], stage='retired'),
                        model('d', ['image-to-video'], stage='deprecated'),
                        model('e', ['image-to-video'], stage='preview'))
        picked = sync_models.pick(skill(['image-to-video'], [{'id': 'a', 'operation': 'text-to-video'},
                                                             'b', 'c', 'd', 'e'], rankedFallback=False),
                                  snapshot)
        self.assertEqual(picked['image-to-video'], [])
        ranked = sync_models.pick(skill(['image-to-video']), snapshot)
        self.assertEqual([r['id'] for r in ranked['image-to-video']], ['a'])

    def test_unsafe_model_id_is_never_rendered(self):
        for bad in ('bad id', 'x|y', '-leading', 'a' * 129, 'name`code`'):
            with self.subTest(bad=bad), self.assertRaises(sync_models.SyncError):
                sync_models.render_block({'image-to-video': [{'id': bad, 'pick': 'default', 'use': ''}]})


class SyncTests(unittest.TestCase):
    def test_empty_or_short_catalog_stops_without_writing(self):
        repo = FixtureRepo(self, [skill(['image-to-video'], ['a'])])
        before = repo.files()
        for snapshot in ({'models': [], 'recommended': {}},
                         {'models': [model('a', ['image-to-video'])], 'recommended': {}}):
            with self.subTest(models=len(snapshot['models'])), self.assertRaises(sync_models.SyncError):
                repo.sync(snapshot)
        self.assertEqual(repo.files(), before)

    def test_operation_with_no_supply_marks_the_skill_unavailable(self):
        repo = FixtureRepo(self, [skill(['motion-control'], ['gone-model'])])
        code, summary, _ = repo.sync(live(model('a', ['image-to-video'])))
        self.assertEqual(code, 0)
        self.assertEqual(repo.availability()['fixture'], {'status': 'unavailable', 'models': [], 'checkedAt': NOW})
        self.assertIn('| `motion-control` | none live | unavailable |', repo.skill_text())

    def test_one_live_operation_keeps_the_skill_available(self):
        repo = FixtureRepo(self, [skill(['motion-control', 'image-to-video'])])
        repo.sync(live(model('a', ['image-to-video'])))
        self.assertEqual(repo.availability()['fixture']['status'], 'available')
        self.assertEqual(repo.availability()['fixture']['models'], ['a'])

    def test_skill_without_operations_needs_no_block(self):
        repo = FixtureRepo(self, [skill([], skill_id='guide')])
        repo.sync(live(model('a', ['image-to-video'])))
        self.assertEqual(repo.availability()['guide'], {'status': 'available', 'models': [], 'checkedAt': NOW})
        self.assertEqual(repo.skill_text('guide'), SKILL_TEXT)

    def test_block_is_replaced_in_place_and_a_second_run_changes_nothing(self):
        repo = FixtureRepo(self, [skill(['image-to-video'], ['a'])])
        snapshot = live(model('a', ['image-to-video']))
        repo.sync(snapshot)
        first = repo.skill_text()
        self.assertNotIn('old generated text', first)
        self.assertIn('Intro line that must stay.\n\n' + sync_models.START, first)
        self.assertIn(sync_models.END + '\n\n## Workflow\n\nSteps that must stay.\n', first)
        self.assertEqual(first.count(sync_models.START), 1)
        self.assertIn('| `image-to-video` | `a` | default |', first)
        files = repo.files()
        code, summary, stale = repo.sync(snapshot, now=LATER)
        self.assertEqual((code, summary['route'], stale), (0, 'none', []))
        self.assertEqual(repo.files(), files)
        self.assertEqual(repo.sync(snapshot, now=LATER, check=True)[0], 0)

    def test_small_change_is_written_and_routed_to_push(self):
        repo = FixtureRepo(self, [skill(['image-to-video'], ['a', 'b'], skill_id=f's{i}') for i in range(5)])
        repo.sync(live(model('a', ['image-to-video']), model('b', ['image-to-video'])), allow_large=True)
        for i in range(3):
            repo.catalog['skills'][i]['preferredModels'] = ['b']
        code, summary, _ = repo.sync(live(model('a', ['image-to-video']), model('b', ['image-to-video'])), now=LATER)
        self.assertEqual((code, summary['route'], summary['changed_skills'], summary['flips']),
                         (0, 'push', ['s0', 's1', 's2'], []))
        self.assertEqual(repo.availability()['s0'], {'status': 'available', 'models': ['b'], 'checkedAt': LATER})
        self.assertEqual(repo.availability()['s4']['checkedAt'], NOW)

    def test_large_flip_is_refused_without_writing_unless_allowed(self):
        skills = [skill(['motion-control'], ['m'], skill_id=f's{i}', rankedFallback=False) for i in range(3)]
        repo = FixtureRepo(self, skills)
        repo.sync(live(model('m', ['motion-control'])), allow_large=True)
        before = repo.files()
        gone = live(model('other', ['image-to-video']))
        code, summary, _ = repo.sync(gone, now=LATER)
        self.assertEqual((code, summary['route'], summary['flips']), (3, 'pr', ['s0', 's1', 's2']))
        self.assertEqual(repo.files(), before)
        code, summary, _ = repo.sync(gone, now=LATER, allow_large=True)
        self.assertEqual((code, summary['route']), (0, 'pr'))
        self.assertEqual(repo.availability()['s0']['status'], 'unavailable')

    def test_check_reports_stale_files_without_writing(self):
        repo = FixtureRepo(self, [skill(['image-to-video'], ['a'])])
        before = repo.files()
        code, _, stale = repo.sync(live(model('a', ['image-to-video'])), check=True)
        self.assertEqual(code, 1)
        self.assertTrue(stale)
        self.assertEqual(repo.files(), before)

    def test_missing_or_duplicate_block_is_an_error(self):
        repo = FixtureRepo(self, [skill(['image-to-video'], ['a'])])
        path = repo.root / 'skills/fixture/SKILL.md'
        for text in ('# No block\n', SKILL_TEXT + SKILL_TEXT):
            path.write_text(text)
            with self.subTest(text=text[:10]), self.assertRaises(ValueError):
                repo.sync(live(model('a', ['image-to-video'])))


def http_error(path, status, code=None):
    body = json.dumps({'error': {'code': code}}).encode() if code else b'{}'
    return urllib.error.HTTPError(path, status, 'error', {}, io.BytesIO(body))


class FetchTests(unittest.TestCase):
    def test_scene_that_the_api_rejects_falls_back_to_the_category_list(self):
        calls = []
        responses = {
            '/v1/models': {'data': [model('d', ['systemone'])]},
            '/v1/models?recommended_for=decision': sync_models.SceneNotOffered('decision'),
            '/v1/models?category=decision': {'data': [{'id': 'd'}]},
            '/v1/models?recommended_for=video': {'data': [{'id': 'v2'}, {'id': 'v1'}]},
        }

        def fake_fetch(path):
            calls.append(path)
            if isinstance(responses[path], Exception):
                raise responses[path]
            return responses[path]

        with patch.object(sync_models, 'fetch', fake_fetch):
            snapshot = sync_models.load_live({'decision', 'video'})
        self.assertEqual(snapshot['recommended'], {'decision': ['d'], 'video': ['v2', 'v1']})
        self.assertIn('/v1/models?category=decision', calls)
        self.assertNotIn('/v1/models?category=video', calls)

    def test_only_invalid_recommended_for_counts_as_a_missing_scene(self):
        cases = [
            ('/v1/models?recommended_for=decision', http_error('u', 400, 'invalid_recommended_for'),
             sync_models.SceneNotOffered),
            ('/v1/models?recommended_for=video', http_error('u', 400, 'invalid_request'), sync_models.SyncError),
            ('/v1/models', http_error('u', 404), sync_models.SyncError),
            ('/v1/models', http_error('u', 503), sync_models.SyncError),
            ('/v1/models', urllib.error.URLError('down'), sync_models.SyncError),
        ]
        for path, error, expected in cases:
            with self.subTest(path=path, error=str(error)):
                with patch.object(sync_models.urllib.request, 'urlopen', side_effect=error), \
                        self.assertRaises(expected):
                    sync_models.fetch(path)


if __name__ == '__main__':
    unittest.main()

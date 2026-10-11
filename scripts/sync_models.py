#!/usr/bin/env python3
"""Refresh each skill's model list from the live TokenLab catalog.

catalog.json owns each skill's `operations`, an optional ordered `preferredModels`
list, and an optional `rankedFallback` (default true). For every operation this
script picks:

1. the preferred models that are live and support the operation, or else
2. if ranked fallback is allowed for that operation, the top three
   `recommended_for` models that support it, plus one low-cost option.

It rewrites only the block between the model markers in each SKILL.md and writes
generated/availability.json. A skill is "unavailable" when no live model supports
any of its operations.

Safety limits, checked before any file is written:
- any failed catalog read, or fewer than MIN_MODELS models, stops with exit 1;
- a large change (more than MAX_CHANGED_SKILLS skills, or more than MAX_FLIPS
  skills turning unavailable) stops with exit 3 unless --allow-large is given.
--summary FILE writes {"route": "none" | "push" | "pr", ...} for the workflow.
--check exits 1 when a file is out of date.

Standard library only. The public catalog needs no API key.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'catalog.json'
AVAILABILITY = ROOT / 'generated' / 'availability.json'
API_BASE = os.environ.get('TOKENLAB_API_BASE', 'https://api.tokenlab.sh').rstrip('/')
START, END = '<!-- tokenlab:models:start -->', '<!-- tokenlab:models:end -->'
BLOCK = re.compile(re.escape(START) + r'.*?' + re.escape(END), re.S)
MODEL_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$')
RANKED_LIMIT = 3
MIN_MODELS = 200
MAX_CHANGED_SKILLS = 3
MAX_FLIPS = 2
LOW_COST_USE = 'Lowest starting price among models with the same pricing unit'

# The recommended_for scene that ranks models for each public operation.
SCENE = {
    'text-to-image': 'image', 'image-to-image': 'image', 'image-edit': 'image',
    'text-to-video': 'video', 'image-to-video': 'video', 'reference-to-video': 'video',
    'start-end-to-video': 'video', 'video-to-video': 'video', 'video-extension': 'video',
    'motion-control': 'video', 'music': 'music', 'text-to-3d': '3d', 'image-to-3d': '3d',
    'world-generation': '3d', 'tts': 'tts', 'stt': 'stt', 'translation': 'translation',
    'systemone': 'decision', 'embedding': 'embedding', 'rerank': 'rerank',
}


class SyncError(Exception):
    """The live catalog cannot be trusted for this run; nothing is written."""


class SceneNotOffered(Exception):
    """The API rejected a recommended_for scene with invalid_recommended_for."""


def fetch(path):
    request = urllib.request.Request(API_BASE + path, headers={'User-Agent': 'tokenlab-skills/sync-models'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 400 and 'recommended_for=' in path:
                try:
                    code = json.loads(error.read()).get('error', {}).get('code')
                except ValueError:
                    code = None
                if code == 'invalid_recommended_for':
                    raise SceneNotOffered(path) from error
            if error.code < 500 or attempt == 2:
                raise SyncError(f'GET {path} failed with HTTP {error.code}') from error
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            if attempt == 2:
                raise SyncError(f'GET {path} failed: {error}') from error


def load_live(scenes):
    """Read the model list and the ranked list for each scene."""
    models = fetch('/v1/models')['data']
    ranked = {}
    for scene in sorted(scenes):
        try:
            body = fetch(f'/v1/models?recommended_for={scene}')
        except SceneNotOffered:
            # The scene is not released yet (for example decision): use the category
            # list, which has the same models but no ranking.
            body = fetch(f'/v1/models?category={scene}')
        ranked[scene] = [m['id'] for m in body['data']]
    return {'models': models, 'recommended': ranked}


def supports(model, operation):
    """True when an active model publishes the operation and has supply for it."""
    t = model.get('tokenlab') or {}
    if (t.get('lifecycle') or {}).get('stage', 'active') != 'active':
        return False  # retired, deprecated, and preview models are not defaults
    if operation == 'chat':
        return t.get('category') == 'chat'
    contract = t.get('public_contract_summary') or t.get('public_contract') or {}
    if operation not in (contract.get('public_operations') or []):
        return False
    supply = ((t.get('deliveryAvailability') or {}).get('operations') or {}).get(operation)
    return supply is None or bool(supply.get('verified') or supply.get('official'))


def low_price(model):
    summary = (model.get('tokenlab') or {}).get('pricing_summary') or {}
    prices = []
    for key in ('platform_min_price', 'official_min_price'):
        try:
            prices.append(float(summary[key]))
        except (KeyError, TypeError, ValueError):
            pass
    return min(prices) if prices else None


def ranked_fallback(skill, operation):
    setting = skill.get('rankedFallback', True)
    return setting.get(operation, True) if isinstance(setting, dict) else bool(setting)


def pick(skill, live):
    """Return {operation: [rows]} for one skill. Each row is {id, pick, use}."""
    by_id = {m['id']: m for m in live['models']}
    preferred = skill.get('preferredModels') or []
    result = {}
    for operation in skill['operations']:
        rows = []
        for entry in preferred:
            entry = {'id': entry} if isinstance(entry, str) else entry
            if entry.get('operation') not in (None, operation):
                continue
            model = by_id.get(entry['id'])
            if model and supports(model, operation):
                rows.append({'id': entry['id'], 'pick': 'preferred', 'use': entry.get('use', '')})
        if not rows and ranked_fallback(skill, operation):
            rows = ranked_rows(operation, live, by_id)
        for index, row in enumerate(rows):
            row['pick'] = 'default' if index == 0 else ('low-cost' if row['pick'] == 'low-cost' else 'alternative')
        result[operation] = rows
    return result


def ranked_rows(operation, live, by_id):
    scene = SCENE.get(operation)
    order = live['recommended'].get(scene) or [m['id'] for m in live['models']]
    candidates = [i for i in order if i in by_id and supports(by_id[i], operation)]
    rows = [{'id': i, 'pick': 'ranked', 'use': ''} for i in candidates[:RANKED_LIMIT]]
    if rows:
        unit = (by_id[rows[0]['id']].get('tokenlab') or {}).get('pricing_unit')
        priced = [(low_price(by_id[i]), i) for i in candidates
                  if (by_id[i].get('tokenlab') or {}).get('pricing_unit') == unit and low_price(by_id[i]) is not None]
        if priced:
            cheapest = min(priced)[1]
            if cheapest not in {r['id'] for r in rows}:
                rows.append({'id': cheapest, 'pick': 'low-cost', 'use': LOW_COST_USE})
    return rows


def render_block(picked):
    lines = [START,
             '<!-- Generated from the live catalog by scripts/sync_models.py. Do not edit; '
             'change preferredModels in catalog.json. -->', '',
             '| Operation | Model | Pick | Use |', '| --- | --- | --- | --- |']
    for operation, rows in picked.items():
        if not rows:
            lines.append(f'| `{operation}` | none live | unavailable | No live model supports this operation now. |')
        for row in rows:
            if not MODEL_ID.match(row['id']):
                raise SyncError(f'refusing to render model id {row["id"]!r}')
            use = row['use'].replace('|', '/').replace('\n', ' ')
            lines.append(f"| `{operation}` | `{row['id']}` | {row['pick']} | {use} |")
    lines += ['',
              'This list refreshes daily from the live catalog. Preferred models come first; otherwise models '
              'are ranked by their 24-hour success rate. Before a call, confirm the model with '
              '`GET /v1/models/{model}` and read its price from `GET /v1/models/{model}/pricing`.',
              END]
    return '\n'.join(lines)


def replace_block(text, block, path='SKILL.md'):
    if len(BLOCK.findall(text)) != 1:
        raise ValueError(f'{path} needs exactly one {START} ... {END} block')
    return BLOCK.sub(lambda _: block, text)


def availability(picked, previous, now):
    ids = list(dict.fromkeys(r['id'] for rows in picked.values() for r in rows))
    status = 'available' if ids or not picked else 'unavailable'
    entry = {'status': status, 'models': ids}
    if previous and {k: previous.get(k) for k in entry} == entry:
        entry['checkedAt'] = previous.get('checkedAt', now)
    else:
        entry['checkedAt'] = now
    return entry


def build(catalog, live, root=ROOT, previous=None, now=None):
    """Return ({path: new text}, {skill_id: availability entry})."""
    if len(live['models']) < MIN_MODELS:
        raise SyncError(f"the catalog lists {len(live['models'])} models; expected at least {MIN_MODELS}")
    now = now or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    previous = previous or {}
    outputs, report = {}, {}
    for skill in catalog['skills']:
        picked = pick(skill, live) if skill['operations'] else {}
        report[skill['id']] = availability(picked, previous.get(skill['id']), now)
        if not picked:
            continue
        path = root / skill['path'] / 'SKILL.md'
        outputs[path] = replace_block(path.read_text(), render_block(picked), path)
    outputs[root / 'generated' / 'availability.json'] = json.dumps(report, indent=2) + '\n'
    return outputs, report


def summarize(previous, report):
    """Count changed skills and available -> unavailable flips, and choose the route."""
    changed = sorted(k for k, v in report.items()
                     if {f: (previous.get(k) or {}).get(f) for f in ('status', 'models')}
                     != {'status': v['status'], 'models': v['models']})
    flips = sorted(k for k in changed
                   if (previous.get(k) or {}).get('status') == 'available' and report[k]['status'] == 'unavailable')
    large = len(changed) > MAX_CHANGED_SKILLS or len(flips) > MAX_FLIPS
    return {'changed_skills': changed, 'flips': flips, 'large': large}


def sync(catalog, live, root=ROOT, check=False, allow_large=False, now=None):
    """Plan, check the safety limits, then write. Return (exit code, summary, stale paths)."""
    availability_path = root / 'generated' / 'availability.json'
    previous = json.loads(availability_path.read_text()) if availability_path.exists() else {}
    outputs, report = build(catalog, live, root=root, previous=previous, now=now)
    stale = [p for p, content in outputs.items() if not p.exists() or p.read_text() != content]
    summary = summarize(previous, report)
    summary['route'] = 'none' if not stale else ('pr' if summary['large'] else 'push')
    if check:
        return (1 if stale else 0), summary, stale
    if summary['large'] and not allow_large:
        return 3, summary, stale
    for path in stale:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(outputs[path])
    return 0, summary, stale


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true', help='fail if a generated file is out of date')
    parser.add_argument('--allow-large', action='store_true', help='write a change above the safety limits')
    parser.add_argument('--summary', help='write the change summary and route to this JSON file')
    parser.add_argument('--catalog-file', help='read a saved {"models", "recommended"} snapshot instead of the API')
    args = parser.parse_args(argv)
    catalog = json.loads(CATALOG.read_text())
    try:
        if args.catalog_file:
            live = json.loads(Path(args.catalog_file).read_text())
        else:
            live = load_live({SCENE[o] for s in catalog['skills'] for o in s['operations'] if o in SCENE})
        code, summary, stale = sync(catalog, live, check=args.check, allow_large=args.allow_large)
    except SyncError as error:
        print(f'sync stopped, no files written: {error}', file=sys.stderr)
        return 1
    if args.summary:
        Path(args.summary).write_text(json.dumps(summary, indent=2) + '\n')
    names = ', '.join(str(p.relative_to(ROOT)) for p in stale)
    if code == 1:
        print(f'out of date: {names}; run python3 scripts/sync_models.py', file=sys.stderr)
    elif code == 3:
        print(f"large change refused, no files written: {len(summary['changed_skills'])} skills changed, "
              f"{len(summary['flips'])} became unavailable; rerun with --allow-large to write it",
              file=sys.stderr)
    elif stale:
        print(f'wrote {names}', file=sys.stderr)
    return code


if __name__ == '__main__':
    sys.exit(main())

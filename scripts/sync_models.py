#!/usr/bin/env python3
"""Refresh each skill's model list from the live TokenLab catalog.

catalog.json owns each skill's `operations` and an optional, ordered
`preferredModels` list. For every operation this script picks:

1. the preferred models that are live and support the operation, or else
2. the top three `recommended_for` models that support it, plus one low-cost option.

It rewrites only the block between the model markers in each SKILL.md and writes
generated/availability.json. A skill is "unavailable" when no live model supports
any of its operations. `--check` exits non-zero when a file is out of date.

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
RANKED_LIMIT = 3

# The recommended_for scene that ranks models for each public operation.
SCENE = {
    'text-to-image': 'image', 'image-to-image': 'image', 'image-edit': 'image',
    'text-to-video': 'video', 'image-to-video': 'video', 'reference-to-video': 'video',
    'start-end-to-video': 'video', 'video-to-video': 'video', 'video-extension': 'video',
    'motion-control': 'video', 'music': 'music', 'text-to-3d': '3d', 'image-to-3d': '3d',
    'world-generation': '3d', 'tts': 'tts', 'stt': 'stt', 'translation': 'translation',
    'systemone': 'decision', 'embedding': 'embedding', 'rerank': 'rerank',
}


def fetch(path):
    request = urllib.request.Request(API_BASE + path, headers={'User-Agent': 'tokenlab-skills/sync-models'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code < 500:
                return None  # for example invalid_recommended_for: the scene is not offered yet
            if attempt == 2:
                raise
        except urllib.error.URLError:
            if attempt == 2:
                raise


def load_live(scenes):
    """Read the model list and the ranked list for each scene."""
    models = fetch('/v1/models')['data']
    ranked = {}
    for scene in sorted(scenes):
        body = fetch(f'/v1/models?recommended_for={scene}')
        ranked[scene] = [m['id'] for m in body['data']] if body else []
    return {'models': models, 'recommended': ranked}


def supports(model, operation):
    """True when a live model publishes the operation and has supply for it."""
    t = model.get('tokenlab') or {}
    if (t.get('lifecycle') or {}).get('stage') == 'retired':
        return False
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
        if not rows:
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
                rows.append({'id': cheapest, 'pick': 'low-cost', 'use': 'Lowest listed price for this operation'})
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
            lines.append(f"| `{operation}` | `{row['id']}` | {row['pick']} | {row['use']} |")
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
    """Return {path: new text} for every generated file."""
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
    return outputs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true', help='fail if a generated file is out of date')
    parser.add_argument('--catalog-file', help='read a saved {"models", "recommended"} snapshot instead of the API')
    args = parser.parse_args(argv)
    catalog = json.loads(CATALOG.read_text())
    if args.catalog_file:
        live = json.loads(Path(args.catalog_file).read_text())
    else:
        live = load_live({SCENE[o] for s in catalog['skills'] for o in s['operations'] if o in SCENE})
    previous = json.loads(AVAILABILITY.read_text()) if AVAILABILITY.exists() else {}
    stale = []
    for path, content in build(catalog, live, previous=previous).items():
        if path.exists() and path.read_text() == content:
            continue
        if args.check:
            stale.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            print(f'wrote {path.relative_to(ROOT)}')
    if stale:
        print('out of date: ' + ', '.join(stale) + '; run python3 scripts/sync_models.py', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

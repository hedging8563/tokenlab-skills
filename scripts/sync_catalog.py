#!/usr/bin/env python3
"""Generate skills.sh.json and the README catalog section from catalog.json.

catalog.json owns skill ids, groups, order, and summaries. Run this script after
you change it. `--check` exits non-zero when a generated file is out of date.
"""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'catalog.json'
SKILLS_SH = ROOT / 'skills.sh.json'
README = ROOT / 'README.md'
START, END = '<!-- catalog:start -->', '<!-- catalog:end -->'
SCHEMA = 'https://skills.sh/schemas/skills.sh.schema.json'


def load_catalog(path=CATALOG):
    return json.loads(path.read_text())


def skills_sh(catalog):
    return {
        '$schema': SCHEMA,
        'notGrouped': 'bottom',
        'groupings': [
            {'title': g['title'], 'description': g['description'], 'skills': list(g['skills'])}
            for g in catalog['groups']
        ],
    }


def readme_section(catalog):
    by_id = {s['id']: s for s in catalog['skills']}
    lines = [START, '']
    for group in catalog['groups']:
        lines.append(f"**{group['title']}** - {group['description']}")
        lines.append('')
        for skill_id in group['skills']:
            lines.append(f"- [`{skill_id}`]({by_id[skill_id]['path']}/) - {by_id[skill_id]['summary']}")
        lines.append('')
    lines.append(END)
    return '\n'.join(lines)


def render_readme(text, catalog):
    head, sep, rest = text.partition(START)
    _, sep2, tail = rest.partition(END)
    if not sep or not sep2:
        raise SystemExit(f'README.md needs {START} and {END} markers')
    return head + readme_section(catalog) + tail


def outputs(catalog):
    return {
        SKILLS_SH: json.dumps(skills_sh(catalog), indent=2) + '\n',
        README: render_readme(README.read_text(), catalog),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='fail if a generated file is out of date')
    args = parser.parse_args(argv)
    stale = []
    for path, content in outputs(load_catalog()).items():
        current = path.read_text() if path.exists() else None
        if current == content:
            continue
        if args.check:
            stale.append(path.name)
        else:
            path.write_text(content)
            print(f'wrote {path.name}')
    if stale:
        print(f"out of date: {', '.join(stale)}; run python3 scripts/sync_catalog.py", file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

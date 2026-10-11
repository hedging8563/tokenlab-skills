#!/usr/bin/env python3
"""Write SRT or VTT subtitles from a verbose_json transcription response.

Standard library only.

  subtitles.py transcript.json --format srt > clip.srt
  subtitles.py transcript.json --format vtt --max-chars 42 > clip.vtt
  subtitles.py transcript.json --max-chars 42 --text-only > cues.txt
  subtitles.py transcript.json --max-chars 42 --texts cues.es.txt > clip.es.srt

The input is the JSON body from /v1/audio/transcriptions with
response_format=verbose_json, or the tokenlab_run.py output that wraps it in
"response" or "task". Cues come from `segments`. With --max-chars, long segments are split
on word timestamps (`words`) when the response has them. A response with only
`words` is split into cues of --max-chars (default 42).

To translate, print the cue texts one per line with --text-only, translate that
text, then pass the translated lines back with --texts and the same --max-chars.
The line count must match the cue count, so the original timings are kept.
"""

import argparse
import json
from pathlib import Path
import sys


def stamp(seconds, sep):
    ms = max(0, int(round(float(seconds) * 1000)))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}'


def split_on_words(segment, words, max_chars):
    """Split one segment into cues of at most max_chars, using word timings inside it."""
    inside = [w for w in words if w['start'] >= segment['start'] - 0.01 and w['end'] <= segment['end'] + 0.01]
    if not inside:
        return [segment]
    cues, current = [], []
    for word in inside:
        text = ' '.join(w['word'].strip() for w in current + [word])
        if current and len(text) > max_chars:
            cues.append({'start': current[0]['start'], 'end': current[-1]['end'],
                         'text': ' '.join(w['word'].strip() for w in current)})
            current = []
        current.append(word)
    if current:
        cues.append({'start': current[0]['start'], 'end': current[-1]['end'],
                     'text': ' '.join(w['word'].strip() for w in current)})
    return cues


def cues_from(body, max_chars=None):
    segments = body.get('segments') or []
    words = body.get('words') or []
    if not segments and words:
        # Word-only responses: one span, split into cues by length.
        segments = [{'start': words[0]['start'], 'end': words[-1]['end'],
                     'text': ' '.join(w['word'].strip() for w in words)}]
        max_chars = max_chars or 42
    if not segments:
        raise SystemExit('no segments or words in the response; request response_format=verbose_json '
                         'from a model that returns timestamps')
    cues = []
    for seg in segments:
        seg = {'start': seg['start'], 'end': seg['end'], 'text': seg['text'].strip()}
        if max_chars and len(seg['text']) > max_chars and words:
            cues += split_on_words(seg, words, max_chars)
        else:
            cues.append(seg)
    return [c for c in cues if c['text']]


def render(cues, fmt):
    if fmt == 'vtt':
        blocks = ['WEBVTT']
        blocks += [f"{stamp(c['start'], '.')} --> {stamp(c['end'], '.')}\n{c['text']}" for c in cues]
    else:
        blocks = [f"{i}\n{stamp(c['start'], ',')} --> {stamp(c['end'], ',')}\n{c['text']}" for i, c in enumerate(cues, 1)]
    return '\n\n'.join(blocks) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('path', help='verbose_json response file, or - for stdin')
    parser.add_argument('--format', choices=('srt', 'vtt'), default='srt')
    parser.add_argument('--max-chars', type=int, help='split long cues on word timestamps')
    parser.add_argument('--text-only', action='store_true', help='print cue texts, one per line')
    parser.add_argument('--texts', help='file of replacement cue texts, one per line (for example a translation)')
    args = parser.parse_args(argv)
    raw = sys.stdin.read() if args.path == '-' else Path(args.path).read_text(encoding='utf-8')
    body = json.loads(raw)
    # tokenlab_run.py wraps the body in "response" (sync) or "task" (after polling).
    for key in ('task', 'response'):
        if isinstance(body.get(key), dict):
            body = body[key]
            break
    cues = cues_from(body, args.max_chars)
    if args.text_only:
        sys.stdout.write(''.join(c['text'] + '\n' for c in cues))
        return 0
    if args.texts:
        lines = [line.strip() for line in Path(args.texts).read_text(encoding='utf-8').strip('\n').split('\n')]
        if len(lines) != len(cues):
            raise SystemExit(f'{len(lines)} text lines for {len(cues)} cues; translate cue by cue instead')
        cues = [dict(c, text=t) for c, t in zip(cues, lines)]
    sys.stdout.write(render(cues, args.format))
    return 0


if __name__ == '__main__':
    sys.exit(main())

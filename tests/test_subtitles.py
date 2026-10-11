"""Exercise the subtitle helper of tokenlab-transcribe-and-subtitle without network calls."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'subtitles', ROOT / 'skills/tokenlab-transcribe-and-subtitle/scripts/subtitles.py')
subtitles = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subtitles)


class SubtitleTests(unittest.TestCase):
    BODY = {'segments': [{'start': 0.0, 'end': 2.5, 'text': ' Hello there, welcome to the long demo clip.'}],
            'words': [{'word': w, 'start': s, 'end': e} for w, s, e in
                      [('Hello', 0.0, 0.4), ('there,', 0.4, 0.8), ('welcome', 0.9, 1.3), ('to', 1.3, 1.4),
                       ('the', 1.4, 1.5), ('long', 1.5, 1.8), ('demo', 1.8, 2.1), ('clip.', 2.1, 2.5)]]}

    def test_long_segments_split_on_word_timings(self):
        cues = subtitles.cues_from(self.BODY, max_chars=20)
        self.assertEqual([c['text'] for c in cues], ['Hello there, welcome', 'to the long demo', 'clip.'])
        self.assertEqual((cues[1]['start'], cues[1]['end']), (1.3, 2.1))

    def test_srt_and_vtt_timestamps(self):
        cues = [{'start': 3661.25, 'end': 3662.5, 'text': 'Hi'}]
        self.assertEqual(subtitles.render(cues, 'srt'), '1\n01:01:01,250 --> 01:01:02,500\nHi\n')
        self.assertEqual(subtitles.render(cues, 'vtt'), 'WEBVTT\n\n01:01:01.250 --> 01:01:02.500\nHi\n')

    def test_translated_lines_keep_the_original_timings(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, texts = Path(tmp) / 'body.json', Path(tmp) / 'es.txt'
            source.write_text(json.dumps({'response': self.BODY}))
            texts.write_text('Hola, bienvenidos\na la larga demo\nclip.\n')
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                subtitles.main([str(source), '--max-chars', '20', '--texts', str(texts)])
        self.assertIn('00:00:01,300 --> 00:00:02,100\na la larga demo', out.getvalue())

    def test_mismatched_translation_line_count_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, texts = Path(tmp) / 'body.json', Path(tmp) / 'es.txt'
            source.write_text(json.dumps(self.BODY))
            texts.write_text('only one line\n')
            with self.assertRaises(SystemExit):
                subtitles.main([str(source), '--max-chars', '20', '--texts', str(texts)])


if __name__ == '__main__':
    unittest.main()

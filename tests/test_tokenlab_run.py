"""Exercise the tokenlab-run helper without network calls."""

import argparse
import base64
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run_helper = load_module('tokenlab_run', ROOT / 'skills/tokenlab-run/scripts/tokenlab_run.py')


class Responses:
    """Return queued (status, request_id, body) tuples, or raise queued errors, and record calls."""

    def __init__(self, *items):
        self.items, self.calls = list(items), []

    def __call__(self, method, path, body=None, form=None, timeout=300, auth=True, headers=None, attempts=3):
        self.calls.append({'method': method, 'path': path, 'body': body, 'headers': headers})
        item = self.items.pop(0)
        if isinstance(item, Exception):
            raise item
        return 200, 'req_fixture', item


def run_args(**overrides):
    values = dict(endpoint='/v1/videos/generations', json=None, form=None, file=None, wait=True, interval=0,
                  timeout=60, http_timeout=30, out=None, delivery=None)
    values.update(overrides)
    return argparse.Namespace(**values)


class ResultUrlTests(unittest.TestCase):
    def test_collects_results_and_skips_status_and_stream_links(self):
        task = {
            'status': 'completed', 'poll_url': 'https://api.example.test/v1/tasks/t',
            'data': [{'url': 'https://cdn.example.test/a.png'}], 'outputs': ['https://cdn.example.test/a.png'],
            'video_url': 'https://cdn.example.test/b.mp4', 'stream_audio_url': 'https://stream.example.test/s.mp3',
            'media_retention': {'items': [{'url': 'https://cdn.example.test/a.png'}]},
            'prompt': 'https://not-a-result.example.test',
        }
        self.assertEqual(run_helper.result_urls(task),
                         ['https://cdn.example.test/a.png', 'https://cdn.example.test/b.mp4'])


class WaitTests(unittest.TestCase):
    def test_polls_until_terminal_and_retries_transient_status_errors(self):
        fake = Responses({'status': 'pending'}, run_helper.ApiError(503, {}, 'r'), {'status': 'processing'},
                         {'status': 'completed', 'video_url': 'https://cdn.example.test/v.mp4'})
        with patch.object(run_helper, 'request', fake):
            task = run_helper.wait('/v1/tasks/t', interval=0, sleep=lambda _: None)
        self.assertEqual(task['status'], 'completed')
        self.assertEqual([c['method'] for c in fake.calls], ['GET'] * 4)

    def test_stops_on_a_non_transient_status_error(self):
        fake = Responses(run_helper.ApiError(404, {'error': {'code': 'async_task_not_found'}}, 'r'))
        with patch.object(run_helper, 'request', fake), self.assertRaises(run_helper.ApiError):
            run_helper.wait('/v1/tasks/t', interval=0, sleep=lambda _: None)

    def test_timeout_returns_the_latest_status_instead_of_failing(self):
        clock = iter([0, 100])
        fake = Responses({'status': 'processing', 'id': 't'})
        with patch.object(run_helper, 'request', fake):
            task = run_helper.wait('/v1/tasks/t', interval=0, timeout=10, sleep=lambda _: None,
                                   clock=lambda: next(clock))
        self.assertEqual(task['status'], 'processing')


class RunTests(unittest.TestCase):
    def test_async_task_is_created_once_and_followed_by_its_poll_url(self):
        fake = Responses({'id': 't', 'status': 'pending', 'poll_url': '/v1/custom-poll/t'},
                         {'status': 'completed', 'video_url': 'https://cdn.example.test/v.mp4'})
        with patch.object(run_helper, 'request', fake), contextlib.redirect_stderr(io.StringIO()):
            result = run_helper.run(run_args(json='{"model": "m", "operation": "text-to-video"}', delivery='verified'))
        self.assertEqual([(c['method'], c['path']) for c in fake.calls],
                         [('POST', '/v1/videos/generations'), ('GET', '/v1/custom-poll/t')])
        self.assertEqual(fake.calls[0]['headers'], {'X-TokenLab-Delivery-Policy': 'verified'})
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['result_urls'], ['https://cdn.example.test/v.mp4'])

    def test_failed_create_is_not_sent_again(self):
        fake = Responses(run_helper.ApiError(400, {'error': {'code': 'unsupported_parameter', 'param': 'size'}}, 'r'))
        with patch.object(run_helper, 'request', fake), self.assertRaises(run_helper.ApiError):
            run_helper.run(run_args(json='{"model": "m"}'))
        self.assertEqual(len(fake.calls), 1)

    def test_inline_image_is_saved_and_not_printed(self):
        payload = base64.b64encode(b'png-bytes').decode()
        fake = Responses({'created': 1, 'data': [{'b64_json': payload}]})
        with tempfile.TemporaryDirectory() as tmp, patch.object(run_helper, 'request', fake):
            out = Path(tmp) / 'image.png'
            result = run_helper.run(run_args(endpoint='/v1/images/generations', json='{"model": "m"}', out=str(out)))
            self.assertEqual(out.read_bytes(), b'png-bytes')
        self.assertEqual(len(fake.calls), 1)
        self.assertNotIn(payload, json.dumps(result))

    def test_binary_speech_is_written_to_the_output_file(self):
        fake = Responses(b'ID3audio')
        with tempfile.TemporaryDirectory() as tmp, patch.object(run_helper, 'request', fake):
            out = Path(tmp) / 'speech.mp3'
            result = run_helper.run(run_args(endpoint='/v1/audio/speech', json='{"model": "m"}', out=str(out)))
            self.assertEqual(out.read_bytes(), b'ID3audio')
        self.assertEqual(result['bytes'], 8)


class LostTaskTests(unittest.TestCase):
    """A paid task must never lose its identity, and a create request is never sent twice."""

    def test_task_identity_is_written_to_stderr_right_after_the_create_call(self):
        fake = Responses({'id': 't1', 'status': 'pending', 'poll_url': '/v1/tasks/t1'},
                         {'status': 'completed', 'video_url': 'https://cdn.example.test/v.mp4'})
        err = io.StringIO()
        with patch.object(run_helper, 'request', fake), contextlib.redirect_stderr(err):
            run_helper.run(run_args(json='{"model": "m"}'))
        self.assertEqual(json.loads(err.getvalue().splitlines()[0]),
                         {'request_id': 'req_fixture', 'task_id': 't1', 'poll_url': '/v1/tasks/t1'})

    def test_any_error_while_waiting_returns_unknown_with_the_task_and_a_failing_exit_code(self):
        for error in (RuntimeError('parser broke'), run_helper.ApiError(401, {'error': {}}, 'r')):
            with self.subTest(error=error):
                fake = Responses({'task_id': 't2', 'status': 'pending', 'poll_url': '/v1/tasks/t2'}, error)
                out = io.StringIO()
                env = {'TOKENLAB_API_KEY': 'sk-fixture-only'}
                with patch.dict(run_helper.os.environ, env), patch.object(run_helper, 'request', fake), \
                        contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                    code = run_helper.main(['run', '/v1/videos/generations', '--json', '{}', '--wait'])
                result = json.loads(out.getvalue())
                self.assertEqual(code, 1)
                self.assertEqual(result['status'], 'unknown')
                self.assertEqual((result['task']['task_id'], result['task']['poll_url']), ('t2', '/v1/tasks/t2'))
                self.assertEqual(result['resume'], 'tokenlab_run.py poll /v1/tasks/t2')
                self.assertEqual([c['method'] for c in fake.calls], ['POST', 'GET'])

    def test_broken_create_connection_is_reported_as_maybe_accepted_and_not_resent(self):
        for error in (urllib.error.URLError('timed out'), TimeoutError('read timed out'), ConnectionResetError()):
            with self.subTest(error=type(error).__name__):
                fake = Responses(error)
                out = io.StringIO()
                with patch.dict(run_helper.os.environ, {'TOKENLAB_API_KEY': 'sk-fixture-only'}), \
                        patch.object(run_helper, 'request', fake), contextlib.redirect_stdout(out):
                    code = run_helper.main(['run', '/v1/videos/generations', '--json', '{}', '--wait'])
                result = json.loads(out.getvalue())
                self.assertEqual(code, 1)
                self.assertEqual((result['status'], result['accepted']), ('unknown', 'unknown'))
                self.assertIn('Do not send it again', result['warning'])
                self.assertEqual(len(fake.calls), 1)

    def test_wait_timeout_returns_the_running_task_with_a_resume_command(self):
        clock = iter([0, 200])
        fake = Responses({'id': 't3', 'status': 'pending', 'poll_url': '/v1/tasks/t3'},
                         {'id': 't3', 'status': 'processing', 'poll_url': '/v1/tasks/t3'})
        original = run_helper.wait
        timed = lambda path, interval, timeout: original(path, interval, timeout, sleep=lambda _: None,
                                                          clock=lambda: next(clock))
        out = io.StringIO()
        with patch.dict(run_helper.os.environ, {'TOKENLAB_API_KEY': 'sk-fixture-only'}), \
                patch.object(run_helper, 'request', fake), patch.object(run_helper, 'wait', timed), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = run_helper.main(['run', '/v1/videos/generations', '--json', '{}', '--wait'])
        result = json.loads(out.getvalue())
        self.assertEqual((code, result['status'], result['resume']), (2, 'processing', 'tokenlab_run.py poll /v1/tasks/t3'))

    def test_default_wait_is_short_enough_for_an_agent_turn(self):
        parsed = []
        with patch.object(run_helper, 'run', lambda args: parsed.append(args) or {'status': 'completed'}), \
                patch.dict(run_helper.os.environ, {'TOKENLAB_API_KEY': 'sk-fixture-only'}), \
                contextlib.redirect_stdout(io.StringIO()):
            run_helper.main(['run', '/v1/videos/generations', '--json', '{}', '--wait'])
        self.assertLessEqual(parsed[0].timeout, 120)


class AuthOriginTests(unittest.TestCase):
    def capture(self, path):
        seen = []

        class Reply(io.BytesIO):
            status, headers = 200, {'Content-Type': 'application/json'}

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        def urlopen(req, timeout):
            seen.append((req.full_url, req.get_header('Authorization')))
            return Reply(b'{"status": "completed"}')

        with patch.dict(run_helper.os.environ, {'TOKENLAB_API_KEY': 'sk-fixture-only'}), \
                patch.object(run_helper, 'API_BASE', 'https://api.example.test'), \
                patch.object(run_helper.urllib.request, 'urlopen', urlopen):
            run_helper.request('GET', path)
        return seen[0]

    def test_key_goes_only_to_the_api_origin_over_https(self):
        self.assertEqual(self.capture('/v1/tasks/t')[1], 'Bearer sk-fixture-only')
        self.assertEqual(self.capture('https://api.example.test/v1/tasks/t')[1], 'Bearer sk-fixture-only')
        for other in ('https://cdn.example.test/v1/tasks/t', 'http://api.example.test/v1/tasks/t',
                      'https://api.example.test.evil.test/v1/tasks/t'):
            with self.subTest(url=other):
                self.assertIsNone(self.capture(other)[1])

    def test_poll_accepts_an_absolute_poll_url(self):
        fake = Responses({'status': 'completed', 'data': [{'url': 'https://cdn.example.test/a.png'}]})
        with patch.dict(run_helper.os.environ, {'TOKENLAB_API_KEY': 'sk-fixture-only'}), \
                patch.object(run_helper, 'request', fake), contextlib.redirect_stdout(io.StringIO()):
            code = run_helper.main(['poll', 'https://api.tokenlab.sh/v1/tasks/t4'])
        self.assertEqual((code, fake.calls[0]['path']), (0, 'https://api.tokenlab.sh/v1/tasks/t4'))


class RequestRetryTests(unittest.TestCase):
    def test_get_retries_a_dropped_connection_but_post_does_not(self):
        attempts = []

        def flaky(method, *args):
            attempts.append(method)
            raise urllib.error.URLError('EOF occurred in violation of protocol')

        with patch.object(run_helper, '_request', flaky), patch.object(run_helper.time, 'sleep'):
            with self.assertRaises(urllib.error.URLError):
                run_helper.request('GET', '/v1/models/m')
            with self.assertRaises(urllib.error.URLError):
                run_helper.request('POST', '/v1/videos/generations', body={})
        self.assertEqual(attempts, ['GET', 'GET', 'GET', 'POST'])

    def test_run_without_a_key_stops_before_any_request(self):
        fake = Responses()
        with patch.dict(run_helper.os.environ, {}, clear=True), patch.object(run_helper, 'request', fake), \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            run_helper.main(['run', '/v1/videos/generations', '--json', '{}'])
        self.assertEqual(fake.calls, [])


class ContractTests(unittest.TestCase):
    DETAIL = {'id': 'm', 'tokenlab': {
        'category': 'video', 'lifecycle': {'stage': 'active'},
        'public_contract': {
            'public_operations': ['image-to-video', 'text-to-video'],
            'request_endpoint_by_operation': {'image-to-video': '/v1/videos/generations'},
            'supported_parameters': ['prompt', 'image_url'],
            'durations_label': 'Source clip 3-30 s.',
            'operation_constraints': [{'operation': 'image-to-video', 'allowed_durations': ['2']},
                                      {'operation': 'text-to-video', 'allowed_durations': ['5']}]},
        'deliveryAvailability': {'operations': {'image-to-video': {'verified': True, 'official': False}}}}}

    def test_contract_keeps_only_the_requested_operation(self):
        with patch.object(run_helper, 'request', Responses(self.DETAIL)):
            out = run_helper.contract('m', 'image-to-video')
        self.assertEqual(out['operation_constraints'], [{'operation': 'image-to-video', 'allowed_durations': ['2']}])
        self.assertEqual(out['delivery'], {'image-to-video': {'verified': True, 'official': False}})
        self.assertEqual(out['labels'], {'durations_label': 'Source clip 3-30 s.'})

    def test_contract_rejects_an_operation_the_model_does_not_publish(self):
        with patch.object(run_helper, 'request', Responses(self.DETAIL)), self.assertRaises(SystemExit):
            run_helper.contract('m', 'motion-control')

    def test_price_keeps_price_structures_and_drops_source_notes(self):
        body = {'model': 'm', 'pricing_unit': 'per_second', 'pricing_details': {
            'unitPriceVariants': [{'officialLockPrice': 0.1}], 'minimumUnitCount': 10, 'provenance': {'notes': 'x'}}}
        with patch.object(run_helper, 'request', Responses(body)):
            out = run_helper.price('m')
        self.assertEqual(out['pricing_details'], {'unitPriceVariants': [{'officialLockPrice': 0.1}], 'minimumUnitCount': 10})


if __name__ == '__main__':
    unittest.main()

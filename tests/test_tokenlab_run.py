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
        with patch.object(run_helper, 'request', fake):
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

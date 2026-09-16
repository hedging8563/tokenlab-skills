"""Exercise the shipped helper and exact documentation code without paid requests."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/tokenlab-api-integration/scripts/search_api.py'
EXAMPLES = (ROOT / 'skills/tokenlab-api-integration/references/integration_examples.md').read_text()
spec = importlib.util.spec_from_file_location('search_api', SCRIPT)
search_api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(search_api)


def javascript(heading):
    section = EXAMPLES.split(f'## {heading}\n', 1)[1].split('\n## ', 1)[0]
    return re.search(r'```javascript\n(.*?)\n```', section, re.S).group(1)


CLIENT = javascript('Shared JavaScript client')
WAITER = javascript('Poll raw HTTP tasks')
IMAGE = javascript('Multimedia: handle sync and async image delivery')


def run_js(prefix, suffix, example=''):
    source = "import assert from 'node:assert/strict';\n" + prefix + '\n' + CLIENT + '\n' + WAITER + '\n' + example + '\n' + suffix
    env = {**os.environ, 'TOKENLAB_API_BASE': 'https://api.example.test', 'TOKENLAB_API_KEY': 'sk-fixture-only'}
    result = subprocess.run(['node', '--input-type=module', '-'], input=source, text=True,
                            capture_output=True, env=env, timeout=10)
    if result.returncode:
        raise AssertionError(result.stderr or result.stdout)


class DiscoveryContractTests(unittest.TestCase):
    def test_media_detail_keeps_operation_contract_without_chat_inference(self):
        contract = {
            'request_endpoint': '/v1/images/generations',
            'request_endpoint_by_operation': {'image-edit': '/v1/images/edits'},
            'status_mode': 'inline_or_task',
            'request_shape_mode': 'json_or_multipart',
            'operation_constraints': [{'operation': 'image-edit', 'supported_parameters': ['images']}],
            'recommended_request': {'operation': 'text-to-image'},
        }
        for key in ('request_format_details', 'public_contract'):
            with self.subTest(key=key):
                model = {'id': 'arbitrary-id', 'owned_by': 'openai', 'tokenlab': {
                    'accepted_request_formats': [], key: contract,
                    'request_format_summary': {'request_endpoint': '/summary-only'},
                }}
                value = search_api.summarize(model, 'harness', include_contract=True)
                self.assertEqual(value['preferred_endpoint'], '/v1/images/generations')
                self.assertEqual(value['request_contract'], contract)
                self.assertIn('API/MCP', value['endpoint_reason'])
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    search_api.print_human([model], 'general', include_contract=True)
                self.assertIn('/v1/images/edits', out.getvalue())
                self.assertIn('inline_or_task', out.getvalue())

    def test_unknown_list_detail_is_not_declared_unsupported(self):
        model = {'id': 'gpt-image-named-but-unknown', 'owned_by': 'openai', 'tokenlab': {}}
        value = search_api.summarize(model, 'general')
        self.assertIsNone(value['preferred_endpoint'])
        self.assertIn('inspect --detail', value['endpoint_reason'])
        self.assertNotIn('request_contract', value)

    def test_chat_protocol_selection_still_follows_declared_formats(self):
        model = {'id': 'fixture', 'owned_by': 'openai', 'tokenlab': {
            'accepted_request_formats': ['openai_chat_completions', 'openai_responses']}}
        self.assertEqual(search_api.preferred_endpoint(model, 'general')[0], '/v1/responses')
        self.assertEqual(search_api.preferred_endpoint(model, 'chat')[0], '/v1/chat/completions')
        model['tokenlab']['accepted_request_formats'] = ['gemini_generate_content']
        self.assertIsNone(search_api.preferred_endpoint(model, 'harness')[0])


class JavaScriptExampleTests(unittest.TestCase):
    def test_exact_raw_image_example_polls_returned_url(self):
        run_js('''
let calls = [];
const logs = [];
globalThis.console = {log: (...values) => logs.push(values)};
globalThis.fetch = async (url, init) => {
  calls.push({url: String(url), method: init.method});
  return Response.json(init.method === 'POST'
    ? {task_id: 'ldtask_fixture', status: 'pending', poll_url: '/v1/custom-poll/fixture', data: []}
    : {id: 'ldtask_fixture', status: 'completed', data: [{url: 'https://example.test/image.png'}]});
};
''', '''
assert.equal(calls.length, 2);
assert.equal(calls[1].url, 'https://api.example.test/v1/custom-poll/fixture');
assert.equal(calls[1].method, 'GET');
assert.equal(logs[0][0].status, 'completed');
assert.equal(logs[0][0].data.length, 1);
''', IMAGE)

    def test_exact_inline_image_example_never_polls(self):
        run_js('''
let calls = 0;
const logs = [];
globalThis.console = {log: (...values) => logs.push(values)};
globalThis.fetch = async () => {calls++; return Response.json({created: 1, data: [{b64_json: 'fixture'}]});};
''', "assert.equal(calls, 1); assert.equal(logs[0][0].data[0].b64_json, 'fixture');", IMAGE)

    def test_terminal_image_response_is_delivered_without_requiring_a_poll_url(self):
        run_js('''
let calls = 0;
const logs = [];
globalThis.console = {log: (...values) => logs.push(values)};
globalThis.fetch = async () => {calls++; return Response.json({status: 'failed', error: {code: 'fixture_failure'}});};
''', "assert.equal(calls, 1); assert.equal(logs[0][0].status, 'failed');", IMAGE)

    def test_waiter_failure_timeout_and_cancellation_remain_distinct(self):
        run_js('''
let calls = 0;
globalThis.fetch = async () => {calls++; return Response.json({id: 'fixture', status: 'processing'});};
''', '''
const failed = await waitForTokenLabTask({id: 'fixture', status: 'failed', error: {code: 'fixture_failure'}});
assert.equal(failed.status, 'failed'); assert.equal(calls, 0);
const waiting = await waitForTokenLabTask({task_id: 'fixture', status: 'pending'}, {timeoutMs: 15, pollIntervalMs: 1});
assert.equal(waiting.timed_out, true); assert.equal(waiting.terminal, false);
assert.equal(waiting.latest.status, 'processing');
const before = calls;
const caller = new AbortController(); caller.abort(new Error('caller stopped'));
await assert.rejects(waitForTokenLabTask('fixture', {signal: caller.signal}), /caller stopped/);
assert.equal(calls, before);
''')

    def test_poll_url_cannot_send_credentials_to_another_origin(self):
        run_js('let calls = 0; globalThis.fetch = async () => {calls++; throw Error("unexpected network");};', '''
await assert.rejects(waitForTokenLabTask({id: 'fixture', poll_url: 'https://other.example.test/task'}), /configured API origin/);
assert.equal(calls, 0);
''')

    def test_http_error_preserves_retry_headers_without_create_retry(self):
        run_js('''
let calls = 0;
globalThis.fetch = async () => {
  calls++;
  return Response.json({error: {code: 'rate_limited', message: 'Wait', retry_after: 1}},
    {status: 429, headers: {'Retry-After': '37', 'X-Request-ID': 'req_fixture'}});
};
''', '''
await assert.rejects(tokenlabRequest('/v1/images/generations', {method: 'POST', body: '{}'}), error => {
  assert.equal(error.status, 429); assert.equal(error.code, 'rate_limited');
  assert.equal(error.retryAfter, 37); assert.equal(error.retryAfterHeader, '37');
  assert.equal(error.requestId, 'req_fixture'); assert.equal(error.retryable, true); return true;
});
assert.equal(calls, 1);
const date = new Date(Date.now() + 60_000).toUTCString();
assert.ok(retryAfterSeconds(date) > 30 && retryAfterSeconds(date) <= 60);
assert.equal(retryAfterSeconds(-1), undefined);
assert.equal(retryAfterSeconds(true), undefined);
globalThis.fetch = async () => Response.json({error: {retry_after: 9, retryable: false, request_id: 'req_body'}},
  {status: 503, headers: {'Retry-After': 'invalid'}});
await assert.rejects(tokenlabRequest('/v1/tasks/fixture'), error => {
  assert.equal(error.retryAfter, 9); assert.equal(error.requestId, 'req_body');
  assert.equal(error.retryable, false); return true;
});
''')


class PythonExampleTests(unittest.TestCase):
    def test_python_waiter_preserves_raw_response_poll_url(self):
        section = EXAMPLES.split('Python polling with an overall deadline:', 1)[1]
        source = re.search(r'```python\n(.*?)\n```', section, re.S).group(1)
        calls = []
        def get(url, **kwargs):
            calls.append(url)
            return types.SimpleNamespace(raise_for_status=lambda: None,
                json=lambda: {'id': 'fixture', 'status': 'completed', 'data': [{'url': 'https://example.test/image.png'}]})
        namespace = {}
        with patch.dict(sys.modules, {'requests': types.SimpleNamespace(get=get)}), patch.dict(os.environ, {
            'TOKENLAB_API_BASE': 'https://api.example.test', 'TOKENLAB_API_KEY': 'sk-fixture-only'}):
            exec(source, namespace)
            result = namespace['wait_for_task']({'task_id': 'fixture', 'status': 'pending', 'poll_url': '/v1/custom-poll/fixture'})
            self.assertEqual(result['status'], 'completed')
            self.assertEqual(calls, ['https://api.example.test/v1/custom-poll/fixture'])
            with self.assertRaisesRegex(ValueError, 'configured API origin'):
                namespace['wait_for_task']({'id': 'fixture', 'poll_url': 'https://other.example.test/task'})
            self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""Run one TokenLab request from the command line: read the contract, check the price, call, wait.

Standard library only. The API key comes from TOKENLAB_API_KEY, is never printed, and is sent
only to https URLs on the API host.

`run` prints {request_id, task_id, poll_url} to stderr right after a task is created. A create
request is never sent twice; if its connection breaks, the output says the task may exist.
`--wait` waits up to 100 s. Exit codes: 0 done, 1 failed or unknown, 2 still running (use `poll`).

  tokenlab_run.py contract MODEL [--operation OP]
  tokenlab_run.py price MODEL
  tokenlab_run.py run ENDPOINT --json '{"model": ...}' [--wait] [--out FILE] [--delivery auto|verified|official]
  tokenlab_run.py run ENDPOINT --form model=M --file file=@clip.mp3
  tokenlab_run.py poll TASK_ID_OR_POLL_URL
  tokenlab_run.py cancel TASK_ID
  tokenlab_run.py upload PATH [--purpose user_data] [--model MODEL]
"""

import argparse
import base64
import json
import mimetypes
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

API_BASE = os.environ.get('TOKENLAB_API_BASE', 'https://api.tokenlab.sh').rstrip('/')
TERMINAL = {'completed', 'failed', 'succeeded', 'cancelled', 'expired'}
RETRY_STATUS = {429, 500, 502, 503, 504}
URL_KEYS = ('url', 'urls', 'outputs')
# Links that are not deliverable results: status links and short-lived listening streams.
SKIP_KEYS = ('poll_url', 'media_retention', 'stream_audio_url')


class ApiError(Exception):
    def __init__(self, status, body, request_id):
        super().__init__(f'HTTP {status}')
        self.status, self.body, self.request_id = status, body, request_id


def encode_multipart(fields, files):
    boundary = uuid.uuid4().hex
    chunks = []
    for name, value in fields:
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    for name, path in files:
        ctype = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
        head = (f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n'
                f'Content-Type: {ctype}\r\n\r\n')
        chunks.append(head.encode() + path.read_bytes() + b'\r\n')
    chunks.append(f'--{boundary}--\r\n'.encode())
    return b''.join(chunks), f'multipart/form-data; boundary={boundary}'


def request(method, path, body=None, form=None, timeout=300, auth=True, headers=None, attempts=3):
    """Send one request. Return (status, request_id, parsed JSON or raw bytes).

    Only GET retries a dropped connection. A POST is never sent twice, so a lost
    create response cannot start a second paid task.
    """
    for attempt in range(attempts if method == 'GET' else 1):
        try:
            return _request(method, path, body, form, timeout, auth, headers)
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if method != 'GET' or attempt == attempts - 1:
                raise
            time.sleep(2 * (attempt + 1))


def same_api_origin(url):
    """True for an https URL on the API host. The key is never sent anywhere else."""
    target, base = urllib.parse.urlsplit(url), urllib.parse.urlsplit(API_BASE)
    return target.scheme == 'https' and (target.scheme, target.netloc) == (base.scheme, base.netloc)


def _request(method, path, body, form, timeout, auth, extra_headers):
    absolute = path.startswith(('http://', 'https://'))
    url = path if absolute else API_BASE + path
    headers = {'User-Agent': 'tokenlab-skills/tokenlab-run', **(extra_headers or {})}
    key = os.environ.get('TOKENLAB_API_KEY', '')
    if auth and key and (not absolute or same_api_origin(url)):
        headers['Authorization'] = f'Bearer {key}'
    data = None
    if form is not None:
        data, headers['Content-Type'] = encode_multipart(*form)
    elif body is not None:
        data, headers['Content-Type'] = json.dumps(body).encode(), 'application/json'
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status, response_headers, content = response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        status, response_headers, content = error.code, error.headers, error.read()
    request_id = response_headers.get('x-request-id') if response_headers else None
    ctype = (response_headers.get('Content-Type') or '') if response_headers else ''
    if 'json' in ctype or content[:1] in (b'{', b'['):
        try:
            parsed = json.loads(content)
        except ValueError:
            parsed = content
    else:
        parsed = content
    if status >= 400:
        raise ApiError(status, parsed if not isinstance(parsed, bytes) else parsed[:500].decode('utf-8', 'replace'), request_id)
    return status, request_id, parsed


def result_urls(value, key=''):
    """Collect result URLs from a task or response, skipping poll and status links."""
    found = []
    if isinstance(value, dict):
        for k, v in value.items():
            if k in SKIP_KEYS:
                continue
            found += result_urls(v, k)
    elif isinstance(value, list):
        for item in value:
            found += result_urls(item, key)
    elif isinstance(value, str) and value.startswith(('http://', 'https://')) and key.endswith(URL_KEYS):
        found.append(value)
    return list(dict.fromkeys(found))


def is_task(response):
    return isinstance(response, dict) and response.get('status') not in (None, *TERMINAL) and bool(
        response.get('poll_url') or response.get('task_id') or response.get('id'))


def poll_path(response):
    return response.get('poll_url') or f"/v1/tasks/{response.get('task_id') or response.get('id')}"


def wait(path, interval=5.0, timeout=900.0, sleep=time.sleep, clock=time.monotonic):
    """Poll until a terminal status. Retry only transient status-read errors."""
    deadline, transient = clock() + timeout, 0
    while True:
        try:
            _, request_id, task = request('GET', path)
            transient = 0
        except ApiError as error:
            if error.status not in RETRY_STATUS or transient >= 5:
                raise
            transient += 1
            task = None
        if isinstance(task, dict) and task.get('status') in TERMINAL:
            return task
        if clock() >= deadline:
            return task if isinstance(task, dict) else {'status': 'unknown', 'poll_url': path}
        sleep(interval)


def contract(model, operation=None):
    _, _, detail = request('GET', f'/v1/models/{model}', auth=False)
    t = detail.get('tokenlab') or {}
    pc = t.get('public_contract') or t.get('request_format_details') or {}
    ops = pc.get('public_operations') or []
    rows = [c for c in pc.get('operation_constraints') or [] if not operation or c.get('operation') == operation]
    if operation and operation not in ops:
        raise SystemExit(f'{model} does not publish operation {operation!r}; published: {ops}')
    delivery = (t.get('deliveryAvailability') or {}).get('operations') or {}
    return {
        'model': detail.get('id'),
        'category': t.get('category'),
        'lifecycle': (t.get('lifecycle') or {}).get('stage'),
        'public_operations': ops,
        'accepted_request_formats': t.get('accepted_request_formats') or [],
        'request_endpoint_by_operation': pc.get('request_endpoint_by_operation') or {},
        'status_mode': pc.get('status_mode'),
        'durations': pc.get('durations') or [],
        'resolutions': pc.get('resolutions') or [],
        'aspect_ratios': pc.get('aspect_ratios') or [],
        'output_formats': pc.get('output_formats') or [],
        'labels': {k: pc[k] for k in ('durations_label', 'resolutions_label', 'aspect_ratios_label') if pc.get(k)},
        'service_limits': pc.get('service_limits'),
        'notes': pc.get('notes') or [],
        # Some models publish only model-level parameters and no per-operation rows.
        'supported_parameters': pc.get('supported_parameters') or [],
        'operation_constraints': rows,
        'recommended_request': pc.get('recommended_request') or pc.get('recommended_request_summary'),
        'delivery': {op: delivery.get(op) for op in ([operation] if operation else ops)},
        'pricing_unit': t.get('pricing_unit'),
        'pricing_summary': t.get('pricing_summary'),
    }


def price(model):
    _, _, body = request('GET', f'/v1/models/{model}/pricing', auth=False)
    # Keep every price structure (entries, formulas, unit variants, credits); drop source notes.
    details = {k: v for k, v in (body.get('pricing_details') or {}).items() if k != 'provenance'}
    return {
        'model': body.get('model'),
        'pricing_unit': body.get('pricing_unit'),
        'pricing_summary': body.get('pricing_summary'),
        'scalar_pricing': body.get('scalar_pricing'),
        'official_scalar_pricing': body.get('official_scalar_pricing'),
        'pricing_details': details,
    }


def load_json(text):
    if text.startswith('@'):
        text = Path(text[1:]).read_text()
    return json.loads(text)


def parse_form(pairs, files):
    fields = [tuple(p.split('=', 1)) for p in pairs or []]
    paths = []
    for item in files or []:
        name, _, value = item.partition('=')
        paths.append((name, Path(value.lstrip('@')).expanduser()))
    return fields, paths


def save_inline_images(response, out):
    """Write sync b64_json images to files and keep the printed JSON short."""
    saved = []
    for index, item in enumerate(response.get('data') or [] if isinstance(response, dict) else []):
        data = item.get('b64_json') if isinstance(item, dict) else None
        if not data:
            continue
        if out:
            path = Path(out if index == 0 else f'{out}.{index}')
            path.write_bytes(base64.b64decode(data))
            saved.append(str(path))
        item['b64_json'] = f'<{len(data)} base64 chars{" saved to " + saved[-1] if out else "; use --out FILE to save"}>'
    return saved


def record_task(request_id, response):
    """Print the task identity at once, so a crash or timeout later cannot lose it."""
    print(json.dumps({'request_id': request_id, 'task_id': response.get('task_id') or response.get('id'),
                      'poll_url': poll_path(response)}), file=sys.stderr, flush=True)


def describe(error):
    if isinstance(error, ApiError):
        return {'http_status': error.status, 'request_id': error.request_id, 'error': error.body}
    return f'{type(error).__name__}: {error}'


def run(args):
    started = time.monotonic()
    form = parse_form(args.form, args.file) if (args.form or args.file) else None
    body = load_json(args.json) if args.json else None
    headers = {'X-TokenLab-Delivery-Policy': args.delivery} if args.delivery else None
    try:
        _, request_id, response = request('POST', args.endpoint, body=body, form=form, timeout=args.http_timeout,
                                          headers=headers)
    except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
        # The server may have accepted and charged the request before the connection broke.
        return {'status': 'unknown', 'accepted': 'unknown', 'error': str(error),
                'warning': 'The create request may have been accepted and charged. Do not send it again. '
                           'Check Runs or Usage in the TokenLab console, or ask the user before any retry.',
                'elapsed_s': round(time.monotonic() - started, 1)}
    if is_task(response):
        record_task(request_id, response)
    if isinstance(response, bytes):
        out = Path(args.out or 'tokenlab-output.bin')
        out.write_bytes(response)
        return {'request_id': request_id, 'saved_to': str(out), 'bytes': len(response),
                'elapsed_s': round(time.monotonic() - started, 1)}
    saved = save_inline_images(response, args.out)
    result = {'request_id': request_id, 'response': response}
    if saved:
        result['saved_to'] = saved
    if args.wait and is_task(response):
        try:
            result['task'] = wait(poll_path(response), args.interval, args.timeout)
        except Exception as error:  # the task exists and is billed; never lose its identity
            result['task'] = {'status': 'unknown', 'task_id': response.get('task_id') or response.get('id'),
                              'poll_url': poll_path(response), 'error': describe(error)}
    final = result.get('task', response)
    result['status'] = final.get('status') if isinstance(final, dict) else None
    result['result_urls'] = result_urls(final)
    if is_task(final) or result['status'] == 'unknown':
        result['resume'] = f'tokenlab_run.py poll {poll_path(final if final.get("poll_url") else response)}'
    result['elapsed_s'] = round(time.monotonic() - started, 1)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('contract'); p.add_argument('model'); p.add_argument('--operation')
    p = sub.add_parser('price'); p.add_argument('model')
    p = sub.add_parser('run'); p.add_argument('endpoint')
    p.add_argument('--json', help='JSON body, or @file.json')
    p.add_argument('--form', action='append', help='multipart field name=value')
    p.add_argument('--file', action='append', help='multipart file name=@path')
    p.add_argument('--wait', action='store_true', help='poll an async task until it finishes')
    p.add_argument('--interval', type=float, default=5.0)
    p.add_argument('--timeout', type=float, default=100.0,
                   help='seconds to wait for a task; then resume with the poll command')
    p.add_argument('--http-timeout', type=float, default=300.0)
    p.add_argument('--out', help='file for a binary response (TTS audio) or an inline b64_json image')
    p.add_argument('--delivery', choices=('auto', 'verified', 'official'),
                   help='X-TokenLab-Delivery-Policy for this request; default is the key setting')
    p = sub.add_parser('poll'); p.add_argument('task'); p.add_argument('--interval', type=float, default=5.0)
    p.add_argument('--timeout', type=float, default=900.0)
    p = sub.add_parser('cancel'); p.add_argument('task_id')
    p = sub.add_parser('upload'); p.add_argument('path'); p.add_argument('--purpose', default='user_data')
    p.add_argument('--model')
    args = parser.parse_args(argv)

    needs_key = args.command in ('run', 'poll', 'cancel', 'upload')
    if needs_key and not os.environ.get('TOKENLAB_API_KEY'):
        parser.error('set TOKENLAB_API_KEY')
    try:
        if args.command == 'contract':
            out = contract(args.model, args.operation)
        elif args.command == 'price':
            out = price(args.model)
        elif args.command == 'run':
            out = run(args)
        elif args.command == 'poll':
            path = args.task if args.task.startswith(('/', 'http://', 'https://')) else f'/v1/tasks/{args.task}'
            try:
                task = wait(path, args.interval, args.timeout)
            except Exception as error:
                task = {'status': 'unknown', 'poll_url': path, 'error': describe(error)}
            out = {'task': task, 'status': task.get('status'), 'result_urls': result_urls(task)}
            if out['status'] not in TERMINAL:
                out['resume'] = f'tokenlab_run.py poll {path}'
        elif args.command == 'cancel':
            out = request('DELETE', f'/v1/tasks/{args.task_id}')[2]
        else:
            fields = [('purpose', args.purpose)] + ([('model', args.model)] if args.model else [])
            out = request('POST', '/v1/files', form=(fields, [('file', Path(args.path).expanduser())]))[2]
    except ApiError as error:
        print(json.dumps({'http_status': error.status, 'request_id': error.request_id, 'error': error.body}, indent=2))
        return 1
    print(json.dumps(out, indent=2, ensure_ascii=False))
    status = out.get('status') if isinstance(out, dict) else None
    if status in ('failed', 'unknown'):
        return 1
    # 2: the task is still running after --timeout; resume with the poll command.
    return 2 if args.command in ('run', 'poll') and status in ('pending', 'processing') else 0


if __name__ == '__main__':
    sys.exit(main())

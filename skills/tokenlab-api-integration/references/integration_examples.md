# TokenLab integration examples

These are shape examples, not model-availability truth. Discover a live model and read its detail contract before every non-chat integration or before binding a long-lived agent route.

## Environment

```bash
export TOKENLAB_API_KEY='sk-...'
export TOKENLAB_API_BASE='https://api.tokenlab.sh'
```

Never paste the real key into source, browser code, logs, screenshots, or query strings unless an official SDK protocol specifically requires a query key and the request stays server-side.

## Discover and inspect a model

### JavaScript

```javascript
const apiBase = process.env.TOKENLAB_API_BASE ?? 'https://api.tokenlab.sh';
const apiKey = process.env.TOKENLAB_API_KEY;

async function tokenlabGet(path, signal) {
  const response = await fetch(`${apiBase}${path}`, {
    headers: {
      Accept: 'application/json',
      ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
    },
    signal,
  });
  const body = await response.json();
  if (!response.ok) {
    const error = new Error(body?.error?.message ?? `TokenLab HTTP ${response.status}`);
    error.status = response.status;
    error.code = body?.error?.code;
    error.requestId = response.headers.get('x-request-id');
    error.details = body;
    throw error;
  }
  return body;
}

const controller = new AbortController();
const listing = await tokenlabGet('/v1/models?category=video', controller.signal);
const selected = listing.data[0];
if (!selected) throw new Error('No public video model is currently available');
const detail = await tokenlabGet(`/v1/models/${encodeURIComponent(selected.id)}`, controller.signal);
console.log(detail.id, detail.tokenlab?.accepted_request_formats, detail.tokenlab?.capabilities);
```

### Python

```python
import os
import requests

API_BASE = os.getenv("TOKENLAB_API_BASE", "https://api.tokenlab.sh")
API_KEY = os.getenv("TOKENLAB_API_KEY")
HEADERS = {"Accept": "application/json"}
if API_KEY:
    HEADERS["Authorization"] = f"Bearer {API_KEY}"

listing = requests.get(
    f"{API_BASE}/v1/models",
    params={"category": "image"},
    headers=HEADERS,
    timeout=30,
)
listing.raise_for_status()
models = listing.json()["data"]
if not models:
    raise RuntimeError("No public image model is currently available")

model_id = models[0]["id"]
detail = requests.get(
    f"{API_BASE}/v1/models/{model_id}",
    headers=HEADERS,
    timeout=30,
)
detail.raise_for_status()
print(detail.json()["tokenlab"].get("accepted_request_formats", []))
```

## Native protocol examples

### OpenAI Responses

Use only when the detail contract contains `openai_responses`.

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["TOKENLAB_API_KEY"],
    base_url="https://api.tokenlab.sh/v1",
    timeout=120.0,
)

response = client.responses.create(
    model="<model-id-from-live-detail>",
    input="Explain this repository in three bullets.",
)
print(response.output_text)
```

```javascript
import OpenAI from 'openai';

const client = new OpenAI({
  apiKey: process.env.TOKENLAB_API_KEY,
  baseURL: 'https://api.tokenlab.sh/v1',
  timeout: 120_000,
});

const response = await client.responses.create({
  model: '<model-id-from-live-detail>',
  input: 'Explain this repository in three bullets.',
});
console.log(response.output_text);
```

### Anthropic Messages

Use only when the detail contract contains `anthropic_messages`. The SDK base URL has no `/v1` suffix.

```python
import os
from anthropic import Anthropic

client = Anthropic(
    api_key=os.environ["TOKENLAB_API_KEY"],
    base_url="https://api.tokenlab.sh",
    timeout=120.0,
)

message = client.messages.create(
    model="<model-id-from-live-detail>",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}],
)
print("".join(block.text for block in message.content if block.type == "text"))
```

### Gemini `generateContent`

Use only when the detail contract contains `gemini_generate_content`. Keep native `contents`, `parts`, tools, files, and cached-content fields on this route.

```bash
curl --fail-with-body \
  -X POST 'https://api.tokenlab.sh/v1beta/models/<model-id>:generateContent' \
  -H "Authorization: Bearer $TOKENLAB_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "contents": [{
      "role": "user",
      "parts": [{"text": "Explain this image"}]
    }]
  }'
```

### OpenAI Chat Completions compatibility

```javascript
const completion = await client.chat.completions.create({
  model: '<model-id-whose-detail-declares-openai_chat_completions>',
  messages: [{ role: 'user', content: 'Hello' }],
});
console.log(completion.choices[0]?.message?.content);
```

## Multimedia: handle sync and async image delivery

```javascript
async function tokenlabRequest(path, init, signal) {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
      ...init.headers,
    },
    signal,
  });
  const text = await response.text();
  let body;
  try {
    body = text ? JSON.parse(text) : null;
  } catch (cause) {
    throw new Error(`TokenLab returned non-JSON HTTP ${response.status}`, { cause });
  }
  if (!response.ok) {
    const error = new Error(body?.error?.message ?? `TokenLab HTTP ${response.status}`);
    error.status = response.status;
    error.code = body?.error?.code;
    error.retryable = body?.error?.retryable ?? body?.retryable ?? false;
    error.retryAfter = body?.error?.retry_after ?? body?.retry_after;
    error.requestId = response.headers.get('x-request-id');
    error.details = body;
    throw error;
  }
  return body;
}

const created = await tokenlabRequest('/v1/images/generations', {
  method: 'POST',
  body: JSON.stringify({
    model: '<live-image-model-id>',
    prompt: 'A paper-cut mountain landscape at dawn',
  }),
}, controller.signal);

const delivery = created.delivery;
if (delivery?.mode === 'async') {
  const terminal = await waitForTokenLabTask(delivery.task_id, {
    signal: controller.signal,
    timeoutMs: 15 * 60_000,
  });
  console.log(terminal);
} else {
  console.log(created);
}
```

## Async submit and wait

Video, music, and 3D create endpoints are asynchronous. Replace only the endpoint and request fields defined by the chosen model detail/OpenAPI.

```javascript
const TERMINAL = new Set(['completed', 'failed', 'succeeded', 'cancelled', 'expired']);

function abortableDelay(ms, signal) {
  return new Promise((resolve, reject) => {
    if (signal.aborted) return reject(signal.reason);
    const finish = () => {
      signal.removeEventListener('abort', abort);
      resolve();
    };
    const timer = setTimeout(finish, ms);
    const abort = () => {
      clearTimeout(timer);
      signal.removeEventListener('abort', abort);
      reject(signal.reason);
    };
    signal.addEventListener('abort', abort, { once: true });
  });
}

async function waitForTokenLabTask(id, {
  signal,
  timeoutMs = 15 * 60_000,
  pollIntervalMs = 5_000,
} = {}) {
  const timeout = AbortSignal.timeout(timeoutMs);
  const combined = signal ? AbortSignal.any([signal, timeout]) : timeout;
  let latest = null;
  try {
    while (true) {
      latest = await tokenlabRequest(`/v1/tasks/${encodeURIComponent(id)}`, {
        method: 'GET',
        headers: {},
      }, combined);
      const status = String(latest.status ?? '').toLowerCase();
      if (!status) throw new Error('Task response has no status');
      if (TERMINAL.has(status)) return latest;
      await abortableDelay(pollIntervalMs, combined);
    }
  } catch (error) {
    if (timeout.aborted && !signal?.aborted) {
      return { timed_out: true, terminal: false, latest };
    }
    throw error;
  }
}

const submitted = await tokenlabRequest('/v1/videos/generations', {
  method: 'POST',
  body: JSON.stringify({
    model: '<live-video-model-id>',
    prompt: 'A slow tracking shot through a glass greenhouse after rain',
  }),
}, controller.signal);

const taskId = submitted.delivery?.task_id ?? submitted.task_id ?? submitted.id;
if (!taskId) throw new Error('Async create response did not include a task id');
const result = await waitForTokenLabTask(taskId, { signal: controller.signal });
console.log(result);
```

Python polling with an overall deadline:

```python
import os
import time
import requests

API_BASE = os.getenv("TOKENLAB_API_BASE", "https://api.tokenlab.sh")
HEADERS = {
    "Authorization": f"Bearer {os.environ['TOKENLAB_API_KEY']}",
    "Content-Type": "application/json",
}
TERMINAL = {"completed", "failed", "succeeded", "cancelled", "expired"}

def wait_for_task(task_id: str, timeout_seconds: float = 900, interval_seconds: float = 5):
    deadline = time.monotonic() + timeout_seconds
    latest = None
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return {"timed_out": True, "terminal": False, "latest": latest}
        response = requests.get(
            f"{API_BASE}/v1/tasks/{task_id}",
            headers=HEADERS,
            timeout=min(30, remaining),
        )
        response.raise_for_status()
        latest = response.json()
        status = str(latest.get("status", "")).lower()
        if not status:
            raise RuntimeError("Task response has no status")
        if status in TERMINAL:
            return latest
        time.sleep(min(interval_seconds, max(0, deadline - time.monotonic())))
```

## Multipart audio and files

```python
with open("audio.wav", "rb") as audio:
    response = requests.post(
        f"{API_BASE}/v1/audio/transcriptions",
        headers={"Authorization": f"Bearer {os.environ['TOKENLAB_API_KEY']}"},
        data={"model": "<live-stt-model-id>"},
        files={"file": ("audio.wav", audio, "audio/wav")},
        timeout=120,
    )
response.raise_for_status()
print(response.json()["text"])
```

Validate the local path, MIME type, and byte size before opening a model-selected file. Do not let untrusted model output choose arbitrary host paths.

## Go base client

```go
client := &http.Client{Timeout: 120 * time.Second}
req, err := http.NewRequestWithContext(ctx, http.MethodGet,
    "https://api.tokenlab.sh/v1/models?category=embedding", nil)
if err != nil { return err }
req.Header.Set("Authorization", "Bearer "+os.Getenv("TOKENLAB_API_KEY"))
req.Header.Set("Accept", "application/json")
resp, err := client.Do(req)
if err != nil { return err }
defer resp.Body.Close()
```

Always use `NewRequestWithContext` so caller cancellation propagates.

## PHP base request

```php
<?php
$ch = curl_init('https://api.tokenlab.sh/v1/models?category=rerank');
curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_TIMEOUT => 30,
    CURLOPT_HTTPHEADER => [
        'Accept: application/json',
        'Authorization: Bearer ' . getenv('TOKENLAB_API_KEY'),
    ],
]);
$body = curl_exec($ch);
if ($body === false) {
    throw new RuntimeException(curl_error($ch));
}
$status = curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
curl_close($ch);
if ($status < 200 || $status >= 300) {
    throw new RuntimeException("TokenLab HTTP $status: $body");
}
$models = json_decode($body, true, flags: JSON_THROW_ON_ERROR);
```

## Structured error recovery

Do not implement an unbounded catch-and-retry loop. A safe policy is:

```text
401/403          -> stop; fix credential or permission
400 invalid      -> fix only fields named by the current public contract
404 model/task   -> rediscover or verify ownership; do not retry blindly
402 balance      -> stop or ask before selecting a cheaper model
429              -> bounded retry using Retry-After
5xx retryable    -> bounded same-request retry; preserve payload semantics
model_not_found  -> use explicit did_you_mean/suggestions or rediscover
```

Success means the requested semantic result was delivered: text/tool calls preserved for LLM endpoints, a valid media result or terminal task for generation, an embedding vector with the expected dimension, or a transcript for STT. HTTP 200 alone is not sufficient when the client silently changed the request or returned a nonterminal task.

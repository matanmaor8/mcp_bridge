import { spawn } from 'node:child_process';
import { once } from 'node:events';
import path from 'node:path';
import process from 'node:process';

const root = path.resolve(process.cwd());
const port = 18787;
const baseUrl = `http://127.0.0.1:${port}`;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForHealth(timeoutMs = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(`${baseUrl}/health`);
      if (res.ok) return;
    } catch {}
    await sleep(200);
  }
  throw new Error('server did not become healthy in time');
}

async function run() {
  const child = spawn(process.execPath, ['server.js'], {
    cwd: root,
    env: {
      ...process.env,
      PORT: String(port),
      DEFAULT_MODE: 'mock',
      DEFAULT_REPO: 'sample_repo_template',
      BRIDGE_TIMEOUT_MS: '30000',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  let stdout = '';
  let stderr = '';
  child.stdout.on('data', (chunk) => { stdout += chunk.toString(); });
  child.stderr.on('data', (chunk) => { stderr += chunk.toString(); });

  const results = [];
  const record = async (name, fn) => {
    const started = Date.now();
    await fn();
    results.push({ name, duration_ms: Date.now() - started, status: 'passed' });
  };

  try {
    await waitForHealth();

    await record('GET /health', async () => {
      const res = await fetch(`${baseUrl}/health`);
      if (!res.ok) throw new Error(`health status ${res.status}`);
      const data = await res.json();
      if (!data.ok) throw new Error('health response missing ok=true');
    });

    await record('GET /mcp returns SSE', async () => {
      const res = await fetch(`${baseUrl}/mcp`, { headers: { Accept: 'text/event-stream' } });
      const contentType = res.headers.get('content-type') || '';
      if (!contentType.includes('text/event-stream')) {
        throw new Error(`unexpected content-type: ${contentType}`);
      }
      const reader = res.body.getReader();
      const { value } = await reader.read();
      const text = new TextDecoder().decode(value || new Uint8Array());
      if (!text.includes('event: ready')) throw new Error(`missing ready event: ${text}`);
      await reader.cancel();
    });

    await record('POST /mcp initialize', async () => {
      const res = await fetch(`${baseUrl}/mcp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'initialize' }),
      });
      const data = await res.json();
      if (data?.result?.serverInfo?.name !== 'chatgpt-codex-bridge') {
        throw new Error(`bad initialize response: ${JSON.stringify(data)}`);
      }
    });

    await record('POST /mcp tools/list', async () => {
      const res = await fetch(`${baseUrl}/mcp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jsonrpc: '2.0', id: 2, method: 'tools/list' }),
      });
      const data = await res.json();
      const names = (data?.result?.tools || []).map((t) => t.name);
      for (const expected of ['start_orchestrator_task', 'get_orchestrator_task_status', 'get_orchestrator_task_result']) {
        if (!names.includes(expected)) throw new Error(`missing tool ${expected}`);
      }
    });

    let jobId = '';
    await record('POST /run_async mock', async () => {
      const res = await fetch(`${baseUrl}/run_async`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task: 'Improve logging in the sample repo and add tests', mode: 'mock' }),
      });
      const data = await res.json();
      jobId = data.jobId;
      if (!jobId) throw new Error(`missing jobId: ${JSON.stringify(data)}`);
    });

    await record('GET /jobs/:id completes', async () => {
      const deadline = Date.now() + 10000;
      while (Date.now() < deadline) {
        const res = await fetch(`${baseUrl}/jobs/${jobId}`);
        const data = await res.json();
        if (data.status === 'completed') return;
        await sleep(200);
      }
      throw new Error('job did not complete in time');
    });

    await record('GET /jobs/:id/result returns parsed text', async () => {
      const res = await fetch(`${baseUrl}/jobs/${jobId}/result`);
      const data = await res.json();
      if (!data?.result?.parsed?.finalStatus) {
        throw new Error(`missing parsed finalStatus: ${JSON.stringify(data)}`);
      }
    });

    await record('MCP tools/call start + status + result', async () => {
      const startRes = await fetch(`${baseUrl}/mcp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jsonrpc: '2.0',
          id: 10,
          method: 'tools/call',
          params: { name: 'start_orchestrator_task', arguments: { task: 'Improve logging in the sample repo and add tests', mode: 'mock' } },
        }),
      });
      const startData = await startRes.json();
      const mcpJobId = startData?.result?.structuredContent?.jobId;
      if (!mcpJobId) throw new Error(`missing MCP job id: ${JSON.stringify(startData)}`);

      const deadline = Date.now() + 10000;
      while (Date.now() < deadline) {
        const statusRes = await fetch(`${baseUrl}/mcp`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            jsonrpc: '2.0', id: 11, method: 'tools/call',
            params: { name: 'get_orchestrator_task_status', arguments: { jobId: mcpJobId } },
          }),
        });
        const statusData = await statusRes.json();
        if (statusData?.result?.structuredContent?.status === 'completed') break;
        await sleep(200);
      }

      const resultRes = await fetch(`${baseUrl}/mcp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jsonrpc: '2.0', id: 12, method: 'tools/call',
          params: { name: 'get_orchestrator_task_result', arguments: { jobId: mcpJobId } },
        }),
      });
      const resultData = await resultRes.json();
      if (!resultData?.result?.structuredContent?.result?.parsed?.finalStatus) {
        throw new Error(`missing MCP result payload: ${JSON.stringify(resultData)}`);
      }
    });

    console.log(JSON.stringify({ ok: true, results }, null, 2));
  } finally {
    child.kill('SIGTERM');
    try { await once(child, 'close'); } catch {}
    if (stderr.trim()) {
      console.error(stderr);
    }
  }
}

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

import express from "express";
import path from "path";
import { fileURLToPath } from "url";
import { spawn, spawnSync } from "child_process";
import fs from "fs";
import crypto from "crypto";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const envPath = path.join(__dirname, ".env");

if (fs.existsSync(envPath)) {
  for (const line of fs.readFileSync(envPath, "utf8").split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const idx = trimmed.indexOf("=");
    if (idx > 0) {
      const key = trimmed.slice(0, idx);
      const value = trimmed.slice(idx + 1);
      if (!(key in process.env)) process.env[key] = value;
    }
  }
}

const app = express();
app.use(express.json({ limit: "4mb" }));
app.use("/public", express.static(path.join(__dirname, "public")));
app.use(express.static(path.join(__dirname, "public")));

const PORT = Number(process.env.PORT || 8787);
const ORCHESTRATOR_ROOT = path.resolve(
  __dirname,
  process.env.ORCHESTRATOR_ROOT || "../python_orchestrator"
);
const PYTHON_COMMAND = process.env.PYTHON_COMMAND || "python";
const DEFAULT_MODE = process.env.DEFAULT_MODE || "codex";
const DEFAULT_REPO = process.env.DEFAULT_REPO || "sample_repo_template";
const MCP_BEARER_TOKEN = process.env.MCP_BEARER_TOKEN || "";
const BRIDGE_TIMEOUT_MS = Number(process.env.BRIDGE_TIMEOUT_MS || 300000);
const JOB_RETENTION_MS = Number(process.env.JOB_RETENTION_MS || 60 * 60 * 1000);
const SSE_HEARTBEAT_MS = Number(process.env.SSE_HEARTBEAT_MS || 15000);

const jobs = new Map();
const sseClients = new Set();

function getPublicBaseUrl(req) {
  return process.env.PUBLIC_BASE_URL || `${req.protocol}://${req.get("host")}`;
}

function authorize(req, res, next) {
  if (!MCP_BEARER_TOKEN) return next();
  const header = req.headers.authorization || "";
  if (header === `Bearer ${MCP_BEARER_TOKEN}`) return next();
  return res.status(401).json({ error: "unauthorized" });
}

function setCors(res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "content-type, authorization, mcp-session-id");
  res.setHeader("Access-Control-Expose-Headers", "Mcp-Session-Id");
}

app.options(["/mcp", "/mcp/*"], (_req, res) => {
  setCors(res);
  res.status(204).end();
});

function resolveRepo(repo) {
  const candidate = repo || DEFAULT_REPO;
  if (path.isAbsolute(candidate)) return candidate;
  return path.resolve(ORCHESTRATOR_ROOT, candidate);
}

function buildArgs({ task, mode, repo }) {
  const effectiveMode = mode || DEFAULT_MODE;
  const args = ["app.py", "--task", task, "--mode", effectiveMode];
  if (effectiveMode !== "mock") {
    args.push("--repo", resolveRepo(repo));
  }
  return {
    args,
    effectiveMode,
    effectiveRepo: effectiveMode === "mock" ? "" : resolveRepo(repo),
  };
}

function parseStdout(stdout) {
  const text = stdout || "";
  const finalStatusMatch = text.match(/Final status:\s*(.+)/i);
  const summaryMatch = text.match(/Summary:\s*(.+)/i);
  const testsPassedMatch = text.match(/Tests passed:\s*(.+)/i);
  const changedFiles = [];
  let inChangedFiles = false;

  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (/^Changed files:\s*$/i.test(trimmed)) {
      inChangedFiles = true;
      continue;
    }
    if (
      inChangedFiles &&
      (/^Tests passed:/i.test(trimmed) || /^Summary:/i.test(trimmed) || /^Final status:/i.test(trimmed))
    ) {
      inChangedFiles = false;
    }
    if (inChangedFiles && trimmed.startsWith("- ")) changedFiles.push(trimmed.slice(2).trim());
  }

  return {
    finalStatus: finalStatusMatch ? finalStatusMatch[1].trim() : "",
    summary: summaryMatch ? summaryMatch[1].trim() : "",
    testsPassed: testsPassedMatch ? testsPassedMatch[1].trim() : "",
    changedFiles,
  };
}

function buildHumanReadableResult(result) {
  const parsed = parseStdout(result.stdout || "");
  const parts = [];
  if (parsed.finalStatus) parts.push(`Final status: ${parsed.finalStatus}`);
  if (parsed.summary) parts.push(`Summary: ${parsed.summary}`);
  if (parsed.changedFiles.length) {
    parts.push("Changed files:");
    for (const f of parsed.changedFiles) parts.push(`- ${f}`);
  } else {
    parts.push("Changed files: none");
  }
  if (parsed.testsPassed) parts.push(`Tests passed: ${parsed.testsPassed}`);
  if (result.stdout?.trim()) parts.push("", result.stdout.trim());
  if (result.stderr?.trim()) parts.push("", `stderr:\n${result.stderr.trim()}`);
  return parts.join("\n");
}

function runOrchestratorSync({ task, mode, repo }) {
  const { args, effectiveMode, effectiveRepo } = buildArgs({ task, mode, repo });
  const proc = spawnSync(PYTHON_COMMAND, args, {
    cwd: ORCHESTRATOR_ROOT,
    encoding: "utf8",
    env: process.env,
    timeout: BRIDGE_TIMEOUT_MS,
    maxBuffer: 20 * 1024 * 1024,
  });
  return {
    ok: proc.status === 0,
    status: proc.status,
    timedOut: proc.error?.code === "ETIMEDOUT",
    stdout: proc.stdout || "",
    stderr: proc.stderr || (proc.error ? String(proc.error) : ""),
    command: [PYTHON_COMMAND, ...args].join(" "),
    effectiveMode,
    effectiveRepo,
  };
}

function broadcastMcpEvent(method, params) {
  const payload = `event: message\ndata: ${JSON.stringify({ jsonrpc: "2.0", method, params })}\n\n`;
  for (const client of sseClients) {
    try {
      client.write(payload);
    } catch {
      sseClients.delete(client);
    }
  }
}

function createJob({ task, mode, repo }) {
  const { args, effectiveMode, effectiveRepo } = buildArgs({ task, mode, repo });
  const jobId = crypto.randomUUID();
  const job = {
    id: jobId,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    task,
    mode: effectiveMode,
    repo: effectiveRepo,
    status: "running",
    command: [PYTHON_COMMAND, ...args].join(" "),
    stdout: "",
    stderr: "",
    exitCode: null,
    timedOut: false,
    ok: false,
  };
  jobs.set(jobId, job);

  const child = spawn(PYTHON_COMMAND, args, {
    cwd: ORCHESTRATOR_ROOT,
    env: process.env,
    shell: false,
  });

  const timeoutHandle = setTimeout(() => {
    if (job.status === "running") {
      job.timedOut = true;
      job.status = "timed_out";
      job.updatedAt = new Date().toISOString();
      try {
        child.kill();
      } catch {}
      broadcastMcpEvent("notifications/job_updated", { jobId: job.id, status: job.status });
    }
  }, BRIDGE_TIMEOUT_MS);

  child.stdout.on("data", (chunk) => {
    job.stdout += chunk.toString();
    job.updatedAt = new Date().toISOString();
  });

  child.stderr.on("data", (chunk) => {
    job.stderr += chunk.toString();
    job.updatedAt = new Date().toISOString();
  });

  child.on("close", (code) => {
    clearTimeout(timeoutHandle);
    if (job.status !== "timed_out") {
      job.exitCode = code;
      job.status = "completed";
      job.ok = code === 0;
      job.updatedAt = new Date().toISOString();
    }
    broadcastMcpEvent("notifications/job_updated", { jobId: job.id, status: job.status });
    setTimeout(() => jobs.delete(jobId), JOB_RETENTION_MS);
  });

  child.on("error", (err) => {
    clearTimeout(timeoutHandle);
    job.stderr += `\n${String(err)}`;
    job.status = "failed";
    job.updatedAt = new Date().toISOString();
    broadcastMcpEvent("notifications/job_updated", { jobId: job.id, status: job.status });
  });

  return job;
}

function getJobResult(job) {
  const result = {
    ok: job.ok,
    status: job.exitCode,
    timedOut: job.timedOut,
    stdout: job.stdout,
    stderr: job.stderr,
    command: job.command,
    effectiveMode: job.mode,
    effectiveRepo: job.repo,
  };

  return {
    ...result,
    parsed: parseStdout(job.stdout),
    text: buildHumanReadableResult(result),
  };
}

app.get("/", (_req, res) => {
  res.type("text/plain").send("ChatGPT Codex Bridge running");
});

app.get("/health", (_req, res) => {
  res.json({
    ok: true,
    port: PORT,
    orchestratorRoot: ORCHESTRATOR_ROOT,
    defaultMode: DEFAULT_MODE,
    defaultRepo: resolveRepo(DEFAULT_REPO),
    activeJobs: Array.from(jobs.values()).filter((j) => j.status === "running").length,
  });
});

app.post("/run", authorize, (req, res) => {
  const task = req.body?.task;
  if (!task) return res.status(400).json({ error: "task is required" });
  const result = runOrchestratorSync({
    task,
    mode: req.body?.mode || DEFAULT_MODE,
    repo: req.body?.repo || DEFAULT_REPO,
  });
  res.json({ ...result, parsed: parseStdout(result.stdout), text: buildHumanReadableResult(result) });
});

app.post("/run_async", authorize, (req, res) => {
  const task = req.body?.task;
  if (!task) return res.status(400).json({ error: "task is required" });
  const job = createJob({
    task,
    mode: req.body?.mode || DEFAULT_MODE,
    repo: req.body?.repo || DEFAULT_REPO,
  });
  res.json({ ok: true, jobId: job.id, status: job.status, mode: job.mode, repo: job.repo, command: job.command, createdAt: job.createdAt });
});

app.get("/jobs/:jobId", authorize, (req, res) => {
  const job = jobs.get(req.params.jobId);
  if (!job) return res.status(404).json({ error: "job not found" });
  res.json({ ok: true, jobId: job.id, status: job.status, mode: job.mode, repo: job.repo, command: job.command, exitCode: job.exitCode, timedOut: job.timedOut, createdAt: job.createdAt, updatedAt: job.updatedAt });
});

app.get("/jobs/:jobId/result", authorize, (req, res) => {
  const job = jobs.get(req.params.jobId);
  if (!job) return res.status(404).json({ error: "job not found" });
  if (job.status === "running") return res.json({ ok: true, jobId: job.id, status: job.status, message: "Job is still running." });
  res.json({ ok: true, jobId: job.id, status: job.status, result: getJobResult(job) });
});

app.get("/.well-known/mcp", authorize, (req, res) => {
  setCors(res);
  res.json({
    name: "chatgpt-codex-bridge",
    version: "2.0.0",
    mcp_url: `${getPublicBaseUrl(req)}/mcp`,
  });
});

app.get("/mcp", authorize, (req, res) => {
  setCors(res);
  res.status(200);
  res.setHeader("Content-Type", "text/event-stream; charset=utf-8");
  res.setHeader("Cache-Control", "no-cache, no-transform");
  res.setHeader("Connection", "keep-alive");
  res.flushHeaders?.();
  res.write(`event: ready\ndata: ${JSON.stringify({ ok: true, name: "chatgpt-codex-bridge", version: "2.0.0" })}\n\n`);
  const timer = setInterval(() => {
    try {
      res.write(`: heartbeat ${Date.now()}\n\n`);
    } catch {
      clearInterval(timer);
    }
  }, SSE_HEARTBEAT_MS);
  sseClients.add(res);
  req.on("close", () => {
    clearInterval(timer);
    sseClients.delete(res);
  });
});

app.post("/mcp", authorize, (req, res) => {
  setCors(res);
  const method = req.body?.method;
  const id = req.body?.id ?? null;

  if (method === "initialize") {
    return res.json({
      jsonrpc: "2.0",
      id,
      result: {
        protocolVersion: "2025-03-26",
        capabilities: { tools: {} },
        serverInfo: { name: "chatgpt-codex-bridge", version: "2.0.0" },
      },
    });
  }

  if (method === "tools/list") {
    return res.json({
      jsonrpc: "2.0",
      id,
      result: {
        tools: [
          {
            name: "start_orchestrator_task",
            description: "Start a local orchestrator task asynchronously and return a job ID.",
            inputSchema: {
              type: "object",
              properties: {
                task: { type: "string" },
                mode: { type: "string", enum: ["repo", "codex", "mock", "openai"] },
                repo: { type: "string" },
              },
              required: ["task"],
            },
          },
          {
            name: "get_orchestrator_task_status",
            description: "Get the current status of an asynchronous orchestrator job.",
            inputSchema: {
              type: "object",
              properties: { jobId: { type: "string" } },
              required: ["jobId"],
            },
          },
          {
            name: "get_orchestrator_task_result",
            description: "Get the final result of a completed asynchronous orchestrator job.",
            inputSchema: {
              type: "object",
              properties: { jobId: { type: "string" } },
              required: ["jobId"],
            },
          },
        ],
      },
    });
  }

  if (method === "tools/call") {
    const params = req.body?.params || {};
    const toolName = params.name;
    const args = params.arguments || {};

    if (toolName === "start_orchestrator_task") {
      if (!args.task) {
        return res.json({ jsonrpc: "2.0", id, error: { code: -32602, message: "task is required" } });
      }
      const job = createJob({ task: args.task, mode: args.mode || DEFAULT_MODE, repo: args.repo || DEFAULT_REPO });
      return res.json({
        jsonrpc: "2.0",
        id,
        result: {
          structuredContent: { jobId: job.id, status: job.status, mode: job.mode, repo: job.repo, command: job.command, createdAt: job.createdAt },
          content: [{ type: "text", text: `Started orchestrator job.\nJob ID: ${job.id}\nStatus: ${job.status}\nMode: ${job.mode}\nRepo: ${job.repo}` }],
        },
      });
    }

    if (toolName === "get_orchestrator_task_status") {
      const job = jobs.get(args.jobId);
      if (!job) {
        return res.json({ jsonrpc: "2.0", id, error: { code: -32004, message: "job not found" } });
      }
      return res.json({
        jsonrpc: "2.0",
        id,
        result: {
          structuredContent: { jobId: job.id, status: job.status, mode: job.mode, repo: job.repo, command: job.command, exitCode: job.exitCode, timedOut: job.timedOut, createdAt: job.createdAt, updatedAt: job.updatedAt },
          content: [{ type: "text", text: `Job ID: ${job.id}\nStatus: ${job.status}\nExit code: ${String(job.exitCode)}\nTimed out: ${String(job.timedOut)}` }],
        },
      });
    }

    if (toolName === "get_orchestrator_task_result") {
      const job = jobs.get(args.jobId);
      if (!job) {
        return res.json({ jsonrpc: "2.0", id, error: { code: -32004, message: "job not found" } });
      }
      if (job.status === "running") {
        return res.json({
          jsonrpc: "2.0",
          id,
          result: {
            structuredContent: { jobId: job.id, status: job.status },
            content: [{ type: "text", text: `Job ${job.id} is still running.` }],
          },
        });
      }
      const result = getJobResult(job);
      return res.json({
        jsonrpc: "2.0",
        id,
        result: {
          structuredContent: { jobId: job.id, status: job.status, result },
          content: [{ type: "text", text: result.text }],
        },
      });
    }

    return res.json({ jsonrpc: "2.0", id, error: { code: -32601, message: "unknown tool" } });
  }

  return res.json({ jsonrpc: "2.0", id, error: { code: -32601, message: "unsupported method" } });
});

app.listen(PORT, () => {
  console.log(`Bridge listening on http://localhost:${PORT}`);
  console.log(`Using orchestrator root: ${ORCHESTRATOR_ROOT}`);
});

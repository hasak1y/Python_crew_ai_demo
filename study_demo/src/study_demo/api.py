from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from study_demo.schemas import AnalyzeRequest, AnalyzeResponse, ErrorResponse
from study_demo.service import ServiceError, analyze_topic_service
from study_demo.versioning import get_runtime_versions

# 启动接口时主动加载 .env，避免依赖外部手工注入环境变量。
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

app = FastAPI(title="Study Demo API")


INDEX_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Study Demo</title>
  <style>
    :root {
      --bg: #f5efe6;
      --panel: #fffaf3;
      --line: #e6dccb;
      --text: #1f2a24;
      --muted: #677368;
      --accent: #b85b2b;
      --accent-deep: #7d3918;
      --ok: #2f6c52;
      --error: #a63c29;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(184, 91, 43, 0.18), transparent 28%),
        radial-gradient(circle at bottom right, rgba(47, 108, 82, 0.16), transparent 25%),
        linear-gradient(135deg, #f7f1e8, #efe6d7);
    }

    .page {
      width: min(980px, calc(100vw - 32px));
      margin: 28px auto;
      display: grid;
      gap: 18px;
    }

    .card {
      background: rgba(255, 250, 243, 0.9);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 24px;
      box-shadow: 0 20px 50px rgba(80, 58, 35, 0.12);
      backdrop-filter: blur(10px);
    }

    .hero h1 {
      margin: 0 0 10px;
      font-size: clamp(34px, 5vw, 52px);
      line-height: 0.95;
      letter-spacing: -0.04em;
    }

    .hero p {
      margin: 0;
      color: var(--muted);
      line-height: 1.75;
      font-size: 15px;
    }

    .badge {
      display: inline-block;
      margin-bottom: 14px;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(184, 91, 43, 0.1);
      color: var(--accent-deep);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .workspace {
      display: grid;
      gap: 16px;
    }

    label {
      display: block;
      margin-bottom: 10px;
      font-size: 14px;
      color: var(--muted);
    }

    textarea {
      width: 100%;
      min-height: 160px;
      resize: vertical;
      border: 1px solid #d9cdb9;
      border-radius: 18px;
      padding: 16px;
      font: inherit;
      font-size: 15px;
      line-height: 1.75;
      background: #fffdf9;
      color: var(--text);
      outline: none;
    }

    textarea:focus {
      border-color: rgba(184, 91, 43, 0.45);
      box-shadow: 0 0 0 4px rgba(184, 91, 43, 0.08);
    }

    .actions {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }

    button {
      border: 0;
      border-radius: 999px;
      padding: 14px 20px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }

    .primary {
      background: linear-gradient(135deg, var(--accent), var(--accent-deep));
      color: #fff8f2;
    }

    .secondary {
      background: #fff;
      border: 1px solid var(--line);
      color: var(--text);
    }

    .status {
      min-height: 24px;
      padding: 12px 14px;
      border-radius: 14px;
      background: #fff;
      border: 1px solid var(--line);
      color: var(--muted);
      font-size: 14px;
      line-height: 1.6;
    }

    .status.ok {
      color: var(--ok);
      background: #eef8f2;
      border-color: #cfe7da;
    }

    .status.error {
      color: var(--error);
      background: #fbefeb;
      border-color: #efd1c9;
    }

    .meta {
      font-size: 13px;
      color: var(--muted);
    }

    .trace-toggle {
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--muted);
      font-size: 14px;
    }

    .trace-toggle input {
      width: 16px;
      height: 16px;
    }

    pre {
      margin: 0;
      min-height: 320px;
      padding: 20px;
      border-radius: 18px;
      background: #171b18;
      color: #f4efe7;
      line-height: 1.8;
      white-space: pre-wrap;
      word-break: break-word;
      overflow: auto;
      font-size: 14px;
    }
  </style>
</head>
<body>
  <main class="page">
    <section class="card hero">
      <div class="badge">Schema V1</div>
      <h1>Study Demo</h1>
      <p>
        这是当前项目的规范化接口页面。请求体只描述本次要做什么，响应体只描述产出和状态。
        如果你勾选步骤摘要，接口会把本次执行的简化 trace 一并返回。
      </p>
    </section>

    <section class="card workspace">
      <div>
        <label for="topicInput">输入主题</label>
        <textarea id="topicInput">分析一下 RAG 技术</textarea>
      </div>

      <label class="trace-toggle" for="traceInput">
        <input id="traceInput" type="checkbox" />
        返回步骤执行摘要
      </label>

      <div class="actions">
        <button id="runButton" class="primary" type="button">开始分析</button>
        <button id="clearButton" class="secondary" type="button">清空结果</button>
      </div>

      <div id="status" class="status">页面已加载，可以直接提交。</div>
      <div class="meta" id="meta">等待请求</div>
      <pre id="result">这里会显示分析结果。</pre>
    </section>
  </main>

  <script>
    const topicInput = document.getElementById("topicInput");
    const traceInput = document.getElementById("traceInput");
    const runButton = document.getElementById("runButton");
    const clearButton = document.getElementById("clearButton");
    const statusBox = document.getElementById("status");
    const metaBox = document.getElementById("meta");
    const resultBox = document.getElementById("result");

    function setStatus(message, type) {
      statusBox.textContent = message;
      statusBox.className = "status";
      if (type) {
        statusBox.classList.add(type);
      }
    }

    async function runAnalyze() {
      const topic = topicInput.value.trim();
      if (!topic) {
        setStatus("请输入主题后再提交。", "error");
        topicInput.focus();
        return;
      }

      runButton.disabled = true;
      metaBox.textContent = "正在请求 /analyze";
      resultBox.textContent = "正在调用接口，请稍候...";
      setStatus("请求已发送。", "");

      try {
        const response = await fetch("/analyze", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            topic,
            include_trace: traceInput.checked
          })
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.message || data.detail || "请求失败");
        }

        metaBox.textContent = "请求成功 | request_id: " + data.request_id;
        if (data.degraded) {
          metaBox.textContent += " | degraded: true";
        }
        resultBox.textContent = data.final_answer || "接口返回为空。";

        if (Array.isArray(data.quality_flags) && data.quality_flags.length > 0) {
          resultBox.textContent += "\\n\\n===== QUALITY FLAGS =====\\n\\n" + JSON.stringify(data.quality_flags, null, 2);
        }

        if (Array.isArray(data.trace_summary) && data.trace_summary.length > 0) {
          resultBox.textContent += "\\n\\n===== TRACE SUMMARY =====\\n\\n" + JSON.stringify(data.trace_summary, null, 2);
        }

        setStatus("分析完成。", "ok");
      } catch (error) {
        metaBox.textContent = "请求失败";
        resultBox.textContent = String(error.message || error);
        setStatus("请求失败，请检查接口日志或稍后重试。", "error");
      } finally {
        runButton.disabled = false;
      }
    }

    runButton.addEventListener("click", runAnalyze);

    clearButton.addEventListener("click", function() {
      resultBox.textContent = "这里会显示分析结果。";
      metaBox.textContent = "等待请求";
      setStatus("已清空结果。", "");
    });

    topicInput.addEventListener("keydown", function(event) {
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        runAnalyze();
      }
    });
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX_HTML


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "ui": "schema-v1",
        "version_info": get_runtime_versions(),
    }


@app.post(
    "/analyze",
    response_model=AnalyzeResponse,
    responses={
        400: {"model": ErrorResponse, "description": "请求参数错误"},
        500: {"model": ErrorResponse, "description": "服务内部错误"},
    },
)
def analyze(req: AnalyzeRequest):
    request_id = str(uuid4())
    try:
        return analyze_topic_service(
            topic=req.topic,
            include_trace=req.include_trace,
            request_id=request_id,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                request_id=request_id,
                status="error",
                error_code="BAD_REQUEST",
                message=str(exc),
                version_info=get_runtime_versions(),
            ).model_dump(),
        )
    except ServiceError as exc:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                request_id=request_id,
                status="error",
                error_code=exc.error_code,
                message=exc.message,
                version_info=get_runtime_versions(),
            ).model_dump(),
        )
    except Exception:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                request_id=request_id,
                status="error",
                error_code="INTERNAL_ERROR",
                message="服务内部错误，请稍后重试",
                version_info=get_runtime_versions(),
            ).model_dump(),
        )

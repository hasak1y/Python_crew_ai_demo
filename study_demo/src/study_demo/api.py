from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from study_demo.main import analyze_topic

# 接口启动时主动加载 .env，避免依赖外部手工注入环境变量。
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

app = FastAPI(title="Study Demo API")


class TopicRequest(BaseModel):
    topic: str


INDEX_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Study Demo Workspace</title>
  <style>
    :root {
      --bg-1: #efe7db;
      --bg-2: #f8f4ed;
      --panel: rgba(255, 250, 242, 0.82);
      --panel-strong: rgba(255, 253, 248, 0.96);
      --text: #1d241f;
      --muted: #627065;
      --line: rgba(29, 36, 31, 0.1);
      --accent: #b95f2f;
      --accent-2: #7f3a19;
      --green: #2f6b54;
      --danger: #a7422a;
      --code: #181b19;
      --shadow: 0 30px 80px rgba(88, 61, 34, 0.14);
      --radius-xl: 30px;
      --radius-lg: 22px;
      --radius-md: 16px;
    }

    * {
      box-sizing: border-box;
    }

    html {
      scroll-behavior: smooth;
    }

    body {
      margin: 0;
      min-height: 100vh;
      font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at 0% 0%, rgba(185, 95, 47, 0.2), transparent 28%),
        radial-gradient(circle at 100% 100%, rgba(47, 107, 84, 0.18), transparent 26%),
        linear-gradient(135deg, var(--bg-1), var(--bg-2));
    }

    .page {
      width: min(1240px, calc(100vw - 32px));
      margin: 24px auto 40px;
      display: grid;
      grid-template-columns: 340px minmax(0, 1fr);
      gap: 20px;
    }

    .panel {
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: var(--radius-xl);
      box-shadow: var(--shadow);
      backdrop-filter: blur(14px);
    }

    .sidebar {
      padding: 28px;
      position: sticky;
      top: 20px;
      height: fit-content;
      overflow: hidden;
    }

    .sidebar::before {
      content: "";
      position: absolute;
      inset: auto -60px -100px auto;
      width: 220px;
      height: 220px;
      border-radius: 999px;
      background: radial-gradient(circle, rgba(185, 95, 47, 0.24), transparent 70%);
      pointer-events: none;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(185, 95, 47, 0.11);
      color: var(--accent-2);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .title {
      margin: 18px 0 14px;
      font-size: clamp(38px, 6vw, 58px);
      line-height: 0.94;
      letter-spacing: -0.05em;
    }

    .desc {
      margin: 0;
      color: var(--muted);
      line-height: 1.78;
      font-size: 15px;
    }

    .tips {
      margin: 24px 0 0;
      padding: 0;
      list-style: none;
      display: grid;
      gap: 10px;
    }

    .tips li {
      padding: 14px 16px;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.6);
      border: 1px solid rgba(29, 36, 31, 0.07);
      font-size: 14px;
      color: #344037;
      line-height: 1.6;
    }

    .main {
      display: grid;
      gap: 18px;
    }

    .hero {
      padding: 26px;
      overflow: hidden;
      position: relative;
    }

    .hero::after {
      content: "";
      position: absolute;
      right: -30px;
      top: -40px;
      width: 220px;
      height: 220px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(47, 107, 84, 0.16), transparent 66%);
      pointer-events: none;
    }

    .hero-top {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      flex-wrap: wrap;
    }

    .hero h2 {
      margin: 0 0 10px;
      font-size: 30px;
      letter-spacing: -0.04em;
    }

    .hero p {
      margin: 0;
      color: var(--muted);
      font-size: 15px;
      line-height: 1.76;
      max-width: 760px;
    }

    .stats {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-top: 20px;
    }

    .stat {
      min-width: 150px;
      padding: 14px 16px;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.72);
      border: 1px solid rgba(29, 36, 31, 0.08);
    }

    .stat b {
      display: block;
      font-size: 18px;
      margin-bottom: 4px;
    }

    .stat span {
      color: var(--muted);
      font-size: 13px;
    }

    .workspace {
      display: grid;
      grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr);
      gap: 18px;
    }

    .editor,
    .viewer {
      padding: 24px;
      background: var(--panel-strong);
      border: 1px solid var(--line);
      border-radius: 26px;
    }

    .section-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 14px;
    }

    .section-head h3 {
      margin: 0;
      font-size: 18px;
      letter-spacing: -0.02em;
    }

    .section-sub {
      color: var(--muted);
      font-size: 13px;
    }

    textarea {
      width: 100%;
      min-height: 260px;
      resize: vertical;
      border: 1px solid rgba(29, 36, 31, 0.12);
      border-radius: 22px;
      padding: 18px 18px 20px;
      font: inherit;
      font-size: 15px;
      line-height: 1.75;
      color: var(--text);
      background: linear-gradient(180deg, #fffefb, #faf4ea);
      outline: none;
      transition: box-shadow 180ms ease, border-color 180ms ease, transform 180ms ease;
    }

    textarea:focus {
      border-color: rgba(185, 95, 47, 0.42);
      box-shadow: 0 0 0 5px rgba(185, 95, 47, 0.08);
      transform: translateY(-1px);
    }

    .quick-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-top: 14px;
    }

    .quick-card {
      border: 1px solid rgba(29, 36, 31, 0.08);
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.7);
      padding: 14px;
      text-align: left;
      cursor: pointer;
      transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
    }

    .quick-card:hover {
      transform: translateY(-2px);
      border-color: rgba(185, 95, 47, 0.24);
      background: rgba(255, 249, 240, 0.96);
    }

    .quick-card b {
      display: block;
      font-size: 14px;
      margin-bottom: 4px;
      color: var(--text);
    }

    .quick-card span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.5;
    }

    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 16px;
      align-items: center;
    }

    button {
      border: 0;
      border-radius: 999px;
      padding: 14px 22px;
      font: inherit;
      font-weight: 700;
      letter-spacing: 0.01em;
      cursor: pointer;
      transition: transform 180ms ease, box-shadow 180ms ease, opacity 180ms ease, background 180ms ease;
    }

    .primary {
      color: #fff6f0;
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
      box-shadow: 0 14px 28px rgba(127, 58, 25, 0.24);
    }

    .secondary {
      color: var(--text);
      background: rgba(255, 255, 255, 0.78);
      border: 1px solid rgba(29, 36, 31, 0.08);
    }

    button:hover:not(:disabled) {
      transform: translateY(-2px);
    }

    button:disabled {
      cursor: wait;
      opacity: 0.72;
    }

    .status-bar {
      margin-top: 16px;
      padding: 14px 16px;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.74);
      border: 1px solid rgba(29, 36, 31, 0.07);
      color: var(--muted);
      font-size: 14px;
      line-height: 1.6;
    }

    .status-bar.ok {
      color: var(--green);
      border-color: rgba(47, 107, 84, 0.18);
      background: rgba(236, 247, 241, 0.96);
    }

    .status-bar.error {
      color: var(--danger);
      border-color: rgba(167, 66, 42, 0.18);
      background: rgba(251, 239, 235, 0.96);
    }

    .viewer-meta {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
      margin-bottom: 14px;
    }

    .viewer-meta span {
      font-size: 13px;
      color: var(--muted);
    }

    .output {
      min-height: 520px;
      margin: 0;
      padding: 22px;
      border-radius: 24px;
      background:
        linear-gradient(180deg, rgba(25, 28, 26, 0.98), rgba(18, 21, 19, 0.99));
      color: #f3efe7;
      font-size: 14px;
      line-height: 1.8;
      white-space: pre-wrap;
      word-break: break-word;
      overflow: auto;
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
    }

    .footer {
      padding: 18px 24px 2px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.7;
    }

    code {
      font-family: "Cascadia Code", "Consolas", monospace;
      font-size: 0.95em;
    }

    .viewer-toolbar {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }

    .tiny-btn {
      padding: 9px 12px;
      border-radius: 999px;
      border: 1px solid rgba(29, 36, 31, 0.08);
      background: rgba(255, 255, 255, 0.72);
      color: var(--text);
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
    }

    .tiny-btn:hover {
      background: rgba(255, 249, 240, 0.98);
    }

    @media (max-width: 1080px) {
      .page {
        grid-template-columns: 1fr;
      }

      .sidebar {
        position: static;
      }

      .workspace {
        grid-template-columns: 1fr;
      }
    }

    @media (max-width: 680px) {
      .page {
        width: min(100vw - 18px, 1240px);
        margin-top: 10px;
      }

      .panel,
      .editor,
      .viewer {
        border-radius: 22px;
      }

      .quick-grid {
        grid-template-columns: 1fr;
      }

      .title {
        font-size: 40px;
      }

      .hero h2 {
        font-size: 24px;
      }
    }
  </style>
</head>
<body>
  <main class="page">
    <aside class="panel sidebar">
      <div class="badge">FastAPI + CrewAI</div>
      <h1 class="title">Study Demo<br>Workspace</h1>
      <p class="desc">
        把原本只有接口的分析流程包装成一个直接可用的网页工具。
        输入主题后，后端会按代码中固定的 knowledge 路径调用 <code>/analyze</code>，再把结果回显到页面。
      </p>
      <ul class="tips">
        <li>更适合技术概念、学习路径、系统设计思路，不适合严格依赖“最新事实”的问题。</li>
        <li>首次请求耗时可能较长，因为会经过规划、研究、审核三个顺序任务。</li>
        <li>本地工具默认只读取 <code>study_demo/knowledge</code>，读取路径在代码里固定，不需要用户手动输入。</li>
      </ul>
    </aside>

    <section class="main">
      <section class="panel hero">
        <div class="hero-top">
          <div>
            <h2>一个像产品 Demo 的 AI 分析页面</h2>
            <p>
              这里不是 Swagger，也不是纯表单页。它更像一个轻量工作台：
              左边输入主题，右边查看输出，中间保留状态反馈和快捷示例。
            </p>
          </div>
        </div>
        <div class="stats">
          <div class="stat">
            <b>3 Agents</b>
            <span>规划、研究、审核</span>
          </div>
          <div class="stat">
            <b>DeepSeek</b>
            <span>显式绑定到 Crew</span>
          </div>
          <div class="stat">
            <b>FastAPI</b>
            <span>页面与接口共用一套后端</span>
          </div>
        </div>
      </section>

      <section class="workspace">
        <div class="editor">
          <div class="section-head">
            <h3>输入参数</h3>
            <span class="section-sub">按下 Ctrl + Enter 也可以直接提交</span>
          </div>

          <textarea id="topicInput" placeholder="例如：CrewAI 的基本工作原理&#10;或者：Python 装饰器的核心概念和常见误区">CrewAI 的基本工作原理</textarea>

          <div class="quick-grid">
            <button class="quick-card" type="button" data-topic="CrewAI 的基本工作原理">
              <b>CrewAI 工作原理</b>
              <span>适合测试当前三角色工作流是否正常。</span>
            </button>
            <button class="quick-card" type="button" data-topic="Python 装饰器的核心概念和常见误区">
              <b>Python 装饰器</b>
              <span>适合解释型、结构化输出场景。</span>
            </button>
            <button class="quick-card" type="button" data-topic="RAG 系统的最小实现方案">
              <b>RAG 最小方案</b>
              <span>适合系统设计与 MVP 思路整理。</span>
            </button>
            <button class="quick-card" type="button" data-topic="FastAPI 项目结构如何规划">
              <b>FastAPI 项目结构</b>
              <span>适合学习路径和工程拆解类问题。</span>
            </button>
          </div>

          <div class="actions">
            <button id="analyzeButton" class="primary" type="button">开始分析</button>
            <button id="clearButton" class="secondary" type="button">清空结果</button>
          </div>

          <div id="statusBar" class="status-bar">
            服务已连接，输入主题后点击“开始分析”。
          </div>
        </div>

        <div class="viewer">
          <div class="viewer-meta">
            <div>
              <div class="section-head" style="margin-bottom: 4px;">
                <h3>结果输出</h3>
                <span class="section-sub" id="resultState">等待请求</span>
              </div>
              <span id="topicMeta">当前没有提交主题</span>
            </div>
            <div class="viewer-toolbar">
              <button id="copyButton" class="tiny-btn" type="button">复制结果</button>
            </div>
          </div>

          <pre id="resultOutput" class="output">这里会显示最终分析结果。</pre>
        </div>
      </section>

      <div class="footer">
        页面入口：<code>/</code>，接口文档：<code>/docs</code>，健康检查：<code>/health</code>。
      </div>
    </section>
  </main>

  <script>
    const topicInput = document.getElementById("topicInput");
    const analyzeButton = document.getElementById("analyzeButton");
    const clearButton = document.getElementById("clearButton");
    const copyButton = document.getElementById("copyButton");
    const statusBar = document.getElementById("statusBar");
    const resultOutput = document.getElementById("resultOutput");
    const resultState = document.getElementById("resultState");
    const topicMeta = document.getElementById("topicMeta");
    const quickCards = Array.from(document.querySelectorAll(".quick-card"));

    function setStatus(message, type) {
      statusBar.textContent = message;
      statusBar.className = "status-bar";
      if (type) {
        statusBar.classList.add(type);
      }
    }

    async function submitTopic() {
      const topic = topicInput.value.trim();
      if (!topic) {
        setStatus("请输入主题后再提交。", "error");
        topicInput.focus();
        return;
      }

      analyzeButton.disabled = true;
      resultState.textContent = "分析中";
      topicMeta.textContent = "当前主题：" + topic;
      resultOutput.textContent = "正在调用后端分析流程，请稍候...";
      setStatus("请求已发送。研究员会按代码中固定的 knowledge 路径调用工具读取目录或文件。");

      try {
        const response = await fetch("/analyze", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ topic })
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || data.error || "请求失败");
        }

        resultOutput.textContent = data.result || "接口已返回，但结果为空。";
        resultState.textContent = "已完成";
        setStatus("分析完成，可以继续更换主题重新提交。", "ok");
      } catch (error) {
        resultOutput.textContent = error.message || "发生未知错误";
        resultState.textContent = "请求失败";
        setStatus("请求失败，请查看终端日志。", "error");
      } finally {
        analyzeButton.disabled = false;
      }
    }

    analyzeButton.addEventListener("click", submitTopic);

    clearButton.addEventListener("click", function() {
      topicInput.value = "";
      resultOutput.textContent = "这里会显示最终分析结果。";
      resultState.textContent = "等待请求";
      topicMeta.textContent = "当前没有提交主题";
      setStatus("已清空输入和输出。");
      topicInput.focus();
    });

    copyButton.addEventListener("click", async function() {
      const text = resultOutput.textContent.trim();
      if (!text || text === "这里会显示最终分析结果。") {
        setStatus("当前没有可复制的结果。", "error");
        return;
      }

      try {
        await navigator.clipboard.writeText(text);
        setStatus("结果已复制到剪贴板。", "ok");
      } catch (error) {
        setStatus("复制失败，请手动复制。", "error");
      }
    });

    quickCards.forEach(function(card) {
      card.addEventListener("click", function() {
        topicInput.value = card.dataset.topic || "";
        topicInput.focus();
        setStatus("示例主题已填入，可以直接提交。");
      });
    });

    topicInput.addEventListener("keydown", function(event) {
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        submitTopic();
      }
    });
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index():
    return INDEX_HTML


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(req: TopicRequest):
    try:
        result = analyze_topic(req.topic)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "topic": req.topic.strip(),
        "result": result,
    }

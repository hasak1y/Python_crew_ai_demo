# Study Demo

版本：`1.0.0`

## 项目简介

`study_demo` 是一个基于 CrewAI 的多 Agent 学习型分析项目。

当前版本的目标，不是做一个复杂的平台，而是先把一个可运行、可调用、可观察的最小闭环搭起来。项目目前已经具备以下基础能力：

- 用户输入一个主题后，可以通过 CrewAI 完成规划、研究、审核三个阶段的串行分析。
- 对通用技术问题，可以直接给出结构化说明。
- 对需要参考本地资料的主题，`researcher` 可以读取 `knowledge` 目录下的真实文件内容。
- 提供 FastAPI 接口和简单 Web 页面，方便直接发起分析请求。
- 提供结构化请求体、响应体和错误体，便于后续前后端联调和接口演进。
- 提供请求级 `request_id` 和步骤日志，方便排查一次调用内部到底发生了什么。

从项目阶段来看，`1.0.0` 可以定义为：

“从单纯验证 CrewAI 能跑，推进到一个具备 API 封装、基础前端和执行链路可观测性的原型版本。”

## 当前版本已完成内容

### 1. 多 Agent 流程

当前 Crew 由 3 个角色组成：

- `planner`：先拆解问题，明确分析步骤和顺序。
- `researcher`：根据规划结果进行研究，并在必要时读取本地资料。
- `reviewer`：检查研究结果是否完整、清晰、贴合原问题，并输出最终版本。

执行方式为串行流程：

`planner -> researcher -> reviewer`

这说明项目已经不再是“单次问答”，而是具备了基础的分工式分析结构。

### 2. 本地知识读取能力

项目内置了本地文件读取工具，`researcher` 在需要时可以查看：

- `knowledge/` 目录
- 项目中的本地文件内容

这意味着当前项目已经具备了一个最基础的“本地知识辅助分析”能力，可以支持：

- 总结已有资料
- 基于本地文档回答问题
- 避免完全脱离项目上下文的泛化输出

### 3. API 化封装

项目已经提供 FastAPI 服务入口，分析能力不再只依赖命令行运行。

当前接口特点：

- `POST /analyze` 负责处理分析请求
- `GET /health` 用于健康检查
- `GET /` 提供简单的浏览器测试页面

当前接口已经做了基础规范化：

- 请求体：`AnalyzeRequest`
- 成功响应：`AnalyzeResponse`
- 错误响应：`ErrorResponse`
- 步骤摘要：`StepSummary`

这说明项目已经从“脚本调用”进入“服务调用”阶段。

### 4. Service 层拆分

分析逻辑已经从 API 层拆分到独立的 `service.py` 中，当前服务层负责：

- 组织一次请求的 `request_id`
- 统计请求耗时
- 调用核心分析逻辑
- 按需拼装 `trace_summary`

这一步的价值是让接口层不再直接承担全部职责，后续扩展测试、日志、鉴权、持久化时更容易维护。

### 5. 执行日志与可观测性

项目已经新增 Crew 执行步骤日志能力。

当前会监听：

- `TaskStarted`
- `TaskCompleted`
- `TaskFailed`
- `ToolUsageFinished`
- `ToolUsageError`

日志会写入：

- `logs/crew_steps.jsonl`

日志中记录的信息包括：

- `request_id`
- `agent_name`
- `task_name`
- `duration_ms`
- `tool_calls_count`
- `tool_names`
- `step_output_preview`
- `llm_model`
- `success`

这说明当前版本已经不只是“能跑出结果”，而是初步具备了“能定位问题”的能力。

## 当前目录结构

```text
study_demo/
├─ knowledge/                     # 本地知识文件
├─ logs/                          # 运行日志目录（不提交）
├─ src/
│  └─ study_demo/
│     ├─ api.py                   # FastAPI 接口和内置测试页面
│     ├─ crew.py                  # Crew、Agent、Task 组装
│     ├─ logger.py                # Crew 步骤日志监听与写入
│     ├─ main.py                  # 命令行入口与 analyze_topic
│     ├─ schemas.py               # 请求/响应数据模型
│     ├─ service.py               # API 服务层封装
│     ├─ config/
│     │  ├─ agents.yaml           # Agent 配置
│     │  └─ tasks.yaml            # Task 配置
│     └─ tools/
│        └─ project_tools.py      # 本地项目工具
├─ .env                           # 本地环境变量
├─ pyproject.toml
└─ README.md
```

## 当前调用链路

一次完整分析的大致链路如下：

1. 用户通过浏览器页面、接口请求或命令行输入主题。
2. API 层接收请求并生成 `request_id`。
3. Service 层记录起始时间，并设置当前请求上下文。
4. `StudyDemoCrew` 按顺序执行 `planner`、`researcher`、`reviewer`。
5. 日志监听器记录每个 task 的执行信息。
6. Service 层汇总最终答案、总耗时，以及可选的 `trace_summary`。
7. API 返回结构化 JSON 响应。

## 当前版本接口说明

### `POST /analyze`

请求体示例：

```json
{
  "topic": "分析一下 RAG 技术",
  "include_trace": true
}
```

成功响应示例：

```json
{
  "request_id": "8a6c2c1a-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "status": "success",
  "final_answer": "这里是最终分析结果",
  "duration_ms": 3210,
  "trace_summary": [
    {
      "agent_name": "planner",
      "task_name": "plan_task",
      "success": true,
      "duration_ms": 840,
      "output_preview": "任务拆解摘要"
    }
  ]
}
```

错误响应示例：

```json
{
  "request_id": "8a6c2c1a-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "status": "error",
  "error_code": "BAD_REQUEST",
  "message": "主题不能为空"
}
```

### `GET /health`

用于基础健康检查。

### `GET /`

返回内置测试页面，便于手动输入主题并观察返回结果。

## 运行方式

### 方式一：命令行运行

在项目当前结构下，可直接调用 `main.py` 的逻辑进行分析。

### 方式二：启动 FastAPI

仓库根目录已提供启动脚本：

`../start_fastapi.bat`

脚本当前会：

- 切到仓库根目录
- 释放 `8001` 端口占用
- 设置 `PYTHONPATH`
- 使用指定 Conda 环境启动 `uvicorn`

启动后默认访问：

- [http://127.0.0.1:8001](http://127.0.0.1:8001)

## 当前版本解决了什么问题

和最初的 Demo 相比，`1.0.0` 已经解决了几个关键问题：

- 不再只适合本地临时试跑，而是可以通过 API 调用。
- 不再只有字符串输出，而是有明确的请求和响应结构。
- 不再难以定位问题，而是能看到任务级日志和步骤摘要。
- 不再所有逻辑都堆在接口文件里，而是开始形成清晰的分层。
- 不再只能“知道能跑”，而是能描述“它是怎么跑的”。

## 当前已知限制

虽然 `1.0.0` 已经完成基础闭环，但它仍然是原型版本，当前限制包括：

- 还没有系统化测试用例。
- 还没有日志轮转或自动清理策略。
- 还没有更细粒度的异常分类与错误码体系。
- 还没有鉴权、限流、任务队列等生产能力。
- `knowledge` 的读取策略仍然比较基础。
- README 之外的部署文档和环境说明还不完整。

## 建议的下一步迭代方向

如果继续推进，建议优先按下面顺序演进：

1. 增加接口测试和服务层测试，先保证行为稳定。
2. 补充环境配置说明和启动说明，降低项目复现成本。
3. 完善日志策略，包括轮转、清理和错误级别。
4. 细化 `trace_summary` 和错误码，让接口更适合前端消费。
5. 进一步明确本地知识读取规则，减少不必要的工具调用。
6. 视使用场景考虑部署方式、鉴权和并发任务处理。

## 阶段总结

`study_demo v1.0.0` 的意义，不在于功能很多，而在于已经完成了一个清晰的第一阶段：

- CrewAI 多 Agent 流程已经跑通
- 本地知识读取能力已经接入
- API 接口已经建立
- 前端调试页面已经可用
- 日志与 trace 能力已经补齐基础形态

如果用一句话总结当前进度：

这个项目已经从“验证想法”进入“可持续迭代的原型开发阶段”。

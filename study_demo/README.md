# Study Demo

版本：`1.0.0`

## 项目简介

`study_demo` 是一个基于 CrewAI 的多 Agent 学习型分析项目。

当前版本的目标不是做复杂平台，而是先把一个可运行、可调用、可观察、可回归的最小闭环搭起来。现在已经具备这些基础能力：

- 基于 `planner -> researcher -> reviewer` 的 3-Agent 串行工作流
- `researcher` 可按需读取 `knowledge/` 中的本地资料
- 提供 FastAPI 接口和内置调试页面
- 提供结构化请求体、成功响应和错误响应
- 提供请求级 `request_id`、步骤日志和 `trace_summary`
- 提供失败策略、降级标记和回退逻辑
- 提供 failure regression tests，用于回归失败策略行为
- 提供基础版本化机制，用于追踪 workflow / prompt / tool / schema 的变更来源

一句话定义当前阶段：

这个项目已经从“验证 CrewAI 能跑”推进到“具备 API、日志、失败策略、回归测试和版本追踪能力的原型服务”。

## 当前版本已完成内容

### 1. 多 Agent 工作流

当前 Crew 由 3 个角色组成：

- `planner`：负责拆解问题和组织分析步骤
- `researcher`：负责生成核心内容，并在需要时读取本地资料
- `reviewer`：负责补齐结构、校验质量和整理最终结果

执行方式为：

`planner -> researcher -> reviewer`

### 2. 本地知识读取能力

项目提供了本地工具，`researcher` 可以按需读取：

- `knowledge/` 目录结构
- `knowledge/` 下的 UTF-8 文本文件

同时做了基础安全限制：

- 只允许访问白名单目录
- 超出目录范围会返回标准化 tool error
- 文件不存在、编码不对、文件过大等情况会返回明确错误前缀

### 3. API 化封装

当前接口包括：

- `POST /analyze`
- `GET /health`
- `GET /`

当前接口模型包括：

- `AnalyzeRequest`
- `AnalyzeResponse`
- `ErrorResponse`
- `StepSummary`
- `VersionInfo`

### 4. Service 层拆分

`service.py` 当前负责：

- 生成和传递 `request_id`
- 统计请求耗时
- 协调失败策略和回退逻辑
- 汇总 `quality_flags`
- 汇总 `trace_summary`
- 注入 `version_info`

### 5. 执行日志与可观测性

项目会把执行过程写入：

- [`crew_steps.jsonl`](D:/CODE/PythonProject/Python_crew_ai_demo/study_demo/logs/crew_steps.jsonl)

日志当前会记录：

- `request_id`
- `agent_name`
- `task_name`
- `duration_ms`
- `tool_calls_count`
- `tool_names`
- `step_output_preview`
- `llm_model`
- `success`
- `version_info`

### 6. 失败策略

当前失败策略已经按“硬失败 / 软失败 / 质量失败”落地：

- `planner` 失败：直接终止请求
- `researcher` 核心失败：直接终止请求
- `reviewer` 失败：如有 `researcher` 结果则回退
- tool 失败：返回标准化 tool error，并记录质量标记
- 该用 tool 却没用：返回 `degraded=true`，并写入 `quality_flags`
- 日志失败：不阻断主流程

### 7. 配置管理与版本化

当前版本已经补上基础版本化机制，目的不是做复杂平台，而是先解决一个工程问题：

“结果变了，但不知道是哪次改动引起的。”

目前已经纳入追踪的版本信息包括：

- `workflow_version`
- `prompt_version`
- `agents_config_version`
- `tasks_config_version`
- `model_config_version`
- `tool_version`
- `schema_version`
- `model_name`

这些版本信息现在会同时落在三个地方：

- 配置文件：[`agents.yaml`](D:/CODE/PythonProject/Python_crew_ai_demo/study_demo/src/study_demo/config/agents.yaml) 和 [`tasks.yaml`](D:/CODE/PythonProject/Python_crew_ai_demo/study_demo/src/study_demo/config/tasks.yaml) 顶部保留版本标记
- 服务日志：[`crew_steps.jsonl`](D:/CODE/PythonProject/Python_crew_ai_demo/study_demo/logs/crew_steps.jsonl) 的 task 记录和质量标记都带 `version_info`
- 接口响应：成功响应、错误响应、`/health` 返回和 `trace_summary` 第一条摘要都会带当前运行版本

这意味着以后一次请求出现异常、质量波动、或行为变化时，至少可以直接追溯：

- 当时跑的是哪一版 workflow
- 当时对应的是哪一版 prompt / task 配置
- 当时使用的是哪一版 tool 逻辑
- 当时暴露的是哪一版 API schema
- 当时绑定的是哪个模型名

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
│     ├─ schemas.py               # 请求/响应模型
│     ├─ service.py               # 请求编排、降级和回退逻辑
│     ├─ versioning.py            # workflow / prompt / tool / schema 版本清单
│     ├─ config/
│     │  ├─ agents.yaml           # Agent 配置
│     │  └─ tasks.yaml            # Task 配置
│     └─ tools/
│        └─ project_tools.py      # 本地知识工具
├─ tests/
│  ├─ README.md                   # 测试说明
│  ├─ datasets/
│  │  └─ failure_strategy_cases.json
│  ├─ test_api_failure_strategy.py
│  └─ test_service_failure_strategy.py
├─ .env
├─ pyproject.toml
└─ README.md
```

## 当前调用链路

一次完整请求的链路如下：

1. 用户通过页面、接口或命令行输入主题
2. API 生成 `request_id`
3. Service 初始化请求上下文和版本信息
4. Crew 按顺序执行 `planner`、`researcher`、`reviewer`
5. 日志监听器记录 task、tool 和质量标记
6. Service 根据执行结果决定正常返回、降级返回或失败返回
7. API 返回结构化 JSON 响应

## 接口说明

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
  "degraded": false,
  "quality_flags": null,
  "version_info": {
    "workflow_version": "workflow-v1.1.0",
    "prompt_version": "prompt-v1.1.0",
    "agents_config_version": "agents-v1.1.0",
    "tasks_config_version": "tasks-v1.1.0",
    "model_config_version": "model-v1.0.0",
    "tool_version": "tool-v1.1.0",
    "schema_version": "schema-v1.1.0",
    "model_name": "deepseek-chat"
  },
  "trace_summary": [
    {
      "agent_name": "system",
      "task_name": "version_info",
      "success": true,
      "duration_ms": 0,
      "output_preview": "workflow=workflow-v1.1.0, prompt=prompt-v1.1.0, model_config=model-v1.0.0, tool=tool-v1.1.0, schema=schema-v1.1.0, model_name=deepseek-chat"
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
  "message": "主题不能为空",
  "version_info": {
    "workflow_version": "workflow-v1.1.0",
    "prompt_version": "prompt-v1.1.0",
    "agents_config_version": "agents-v1.1.0",
    "tasks_config_version": "tasks-v1.1.0",
    "model_config_version": "model-v1.0.0",
    "tool_version": "tool-v1.1.0",
    "schema_version": "schema-v1.1.0",
    "model_name": "deepseek-chat"
  }
}
```

### `GET /health`

返回服务健康状态和当前 `version_info`。

### `GET /`

返回内置调试页面，用于手工输入主题并观察结果。

## 运行方式

### 方式一：命令行运行

直接调用 `main.py` 中的分析入口。

### 方式二：启动 FastAPI

仓库根目录已提供启动脚本：

`../start_fastapi.bat`

启动后默认访问：

- [http://127.0.0.1:8001](http://127.0.0.1:8001)

## 测试说明

当前测试目录为：

- [`tests`](D:/CODE/PythonProject/Python_crew_ai_demo/study_demo/tests)

后续改动统一遵循这个顺序：

1. 先改 `datasets/` 里的固定样例
2. 再补测试
3. 先跑测试，确认新增预期有效
4. 再改业务实现
5. 最后全量回归

当前测试重点覆盖：

- failure strategy
- degraded success
- reviewer fallback
- tool error
- API outward behavior
- version info exposure

运行命令：

```powershell
& 'C:\Users\24044\.conda\envs\Python_crew_ai_demo\python.exe' -m unittest discover -s study_demo/tests -p "test_*.py" -v
```

## 当前版本解决了什么问题

和最初的 Demo 相比，`1.0.0` 已经解决了几个关键问题：

- 不再只适合本地临时试跑，而是可以通过 API 调用
- 不再只有字符串输出，而是有明确的请求和响应结构
- 不再难以定位问题，而是能看到任务级日志和步骤摘要
- 不再难以追溯行为变化，而是能看到这次请求实际运行的是哪一版 workflow / prompt / tool / schema
- 不再所有逻辑都堆在接口文件里，而是开始形成清晰的分层
- 不再只知道“能跑”，而是能描述“它为什么这样跑”

## 当前已知限制

虽然 `1.0.0` 已经形成了功能闭环，但它仍然更接近“可运行原型”，距离“稳定服务”还有几个明显缺口：

- 评估机制还没有落地，暂时无法系统判断一次结果到底是变好了还是变差了
- 版本意识已经补上基础形态，但还没有细化到 prompt 片段级、实验组级或发布批次级
- 日志虽然已经具备基础 trace 能力，但还没有形成面向长期运行的轮转、归档和治理策略
- 生产化能力仍然缺失，例如鉴权、限流、并发控制和部署规范

## 下一阶段路线图

下一阶段的目标，不再是“继续加功能”，而是把当前系统从“能跑”升级到“稳定、可测、可控、可维护”。

建议优先级如下：

1. 继续补评估机制，把“测试通过”和“质量变好”区分开
2. 继续扩展黄金样例测试，把真实 topic 输出纳入回归
3. 继续细化版本标记，把版本号收敛到 prompt 片段和实验批次
4. 完善日志治理，包括轮转、清理和错误级别
5. 再考虑鉴权、限流、并发控制和部署规范

## 阶段总结

`study_demo v1.0.0` 的意义不在于功能很多，而在于已经完成了一个清晰的第一阶段：

- 多 Agent 工作流已经跑通
- 本地知识读取能力已经接入
- API 接口已经建立
- 失败策略已经落地
- 测试和固定测试集已经建立
- 版本化机制已经补上基础形态

如果用一句话总结当前进度：

这个项目已经从“验证想法”进入“可持续迭代的原型开发阶段”。

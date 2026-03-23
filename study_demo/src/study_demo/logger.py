from __future__ import annotations

from contextvars import ContextVar
from pathlib import Path
import json
import os
import threading
import time
from typing import Any

from crewai.events.event_bus import crewai_event_bus
from crewai.events.types.task_events import (
    TaskCompletedEvent,
    TaskFailedEvent,
    TaskStartedEvent,
)
from crewai.events.types.tool_usage_events import (
    ToolUsageErrorEvent,
    ToolUsageFinishedEvent,
)

# 当前请求的 request_id 通过上下文变量在一次调用链中传递。
REQUEST_ID_CONTEXT: ContextVar[str | None] = ContextVar(
    "study_demo_request_id",
    default=None,
)

# 当前项目里的 task 与 agent 是固定映射，便于写结构化日志。
TASK_AGENT_MAP = {
    "plan_task": "planner",
    "research_task": "researcher",
    "review_task": "reviewer",
}


def set_request_id(request_id: str) -> None:
    """在当前上下文中写入 request_id，供事件监听阶段复用。"""
    REQUEST_ID_CONTEXT.set(request_id)


def clear_request_id() -> None:
    """在请求结束后清理 request_id，避免后续调用误复用。"""
    REQUEST_ID_CONTEXT.set(None)


def get_request_id() -> str | None:
    """返回当前上下文中的 request_id。"""
    return REQUEST_ID_CONTEXT.get()


class CrewStepLogger:
    """收集 task/tool 执行过程中的关键指标，并按 JSONL 方式写入日志文件。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._task_state: dict[str, dict[str, Any]] = {}
        self._log_path = Path(__file__).resolve().parents[2] / "logs" / "crew_steps.jsonl"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def _write_jsonl(self, payload: dict[str, Any]) -> None:
        with self._lock:
            with self._log_path.open("a", encoding="utf-8") as file:
                file.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _build_preview(self, value: Any) -> str:
        text = str(value).replace("\r", " ").replace("\n", " ").strip()
        return text[:200]

    def on_task_started(self, event: TaskStartedEvent) -> None:
        task_id = str(event.task_id)
        task_name = event.task_name or getattr(event.task, "name", None) or "unknown_task"
        agent_name = TASK_AGENT_MAP.get(task_name, "unknown_agent")

        self._task_state[task_id] = {
            "request_id": get_request_id(),
            "agent_name": agent_name,
            "task_name": task_name,
            "started_at": time.perf_counter(),
            "tool_names": [],
            "tool_calls_count": 0,
            "llm_model": os.getenv("OPENAI_MODEL_NAME", "deepseek-chat"),
        }

    def _append_tool(self, task_id: str, tool_name: str) -> None:
        state = self._task_state.get(task_id)
        if not state:
            return

        state["tool_calls_count"] += 1
        if tool_name and tool_name not in state["tool_names"]:
            state["tool_names"].append(tool_name)

    def on_tool_finished(self, event: ToolUsageFinishedEvent) -> None:
        from_task = getattr(event, "from_task", None)
        task_id = str(getattr(from_task, "id", ""))
        self._append_tool(task_id, event.tool_name)

    def on_tool_error(self, event: ToolUsageErrorEvent) -> None:
        from_task = getattr(event, "from_task", None)
        task_id = str(getattr(from_task, "id", ""))
        self._append_tool(task_id, event.tool_name)

    def _finalize_task(self, task_id: str, success: bool, output_preview: str) -> None:
        state = self._task_state.pop(task_id, None)
        if not state:
            return

        duration_ms = int((time.perf_counter() - state["started_at"]) * 1000)
        payload = {
            "request_id": state["request_id"],
            "agent_name": state["agent_name"],
            "task_name": state["task_name"],
            "duration_ms": duration_ms,
            "tool_calls_count": state["tool_calls_count"],
            "tool_names": state["tool_names"],
            "step_output_preview": output_preview,
            "llm_model": state["llm_model"],
            "success": success,
        }
        self._write_jsonl(payload)

    def on_task_completed(self, event: TaskCompletedEvent) -> None:
        task_id = str(event.task_id)
        output_preview = self._build_preview(getattr(event.output, "raw", event.output))
        self._finalize_task(task_id, True, output_preview)

    def on_task_failed(self, event: TaskFailedEvent) -> None:
        task_id = str(event.task_id)
        output_preview = self._build_preview(event.error)
        self._finalize_task(task_id, False, output_preview)


_LOGGER = CrewStepLogger()
_REGISTERED = False


def init_step_logging() -> None:
    """注册 CrewAI 事件监听器；重复调用时自动跳过。"""
    global _REGISTERED
    if _REGISTERED:
        return

    @crewai_event_bus.on(TaskStartedEvent)
    def _handle_task_started(source: Any, event: TaskStartedEvent) -> None:
        _LOGGER.on_task_started(event)

    @crewai_event_bus.on(TaskCompletedEvent)
    def _handle_task_completed(source: Any, event: TaskCompletedEvent) -> None:
        _LOGGER.on_task_completed(event)

    @crewai_event_bus.on(TaskFailedEvent)
    def _handle_task_failed(source: Any, event: TaskFailedEvent) -> None:
        _LOGGER.on_task_failed(event)

    @crewai_event_bus.on(ToolUsageFinishedEvent)
    def _handle_tool_finished(source: Any, event: ToolUsageFinishedEvent) -> None:
        _LOGGER.on_tool_finished(event)

    @crewai_event_bus.on(ToolUsageErrorEvent)
    def _handle_tool_error(source: Any, event: ToolUsageErrorEvent) -> None:
        _LOGGER.on_tool_error(event)

    _REGISTERED = True

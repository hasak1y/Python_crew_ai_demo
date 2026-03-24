from __future__ import annotations

from contextvars import ContextVar
from pathlib import Path
import json
import os
import sys
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
from study_demo.versioning import get_runtime_versions

REQUEST_ID_CONTEXT: ContextVar[str | None] = ContextVar(
    "study_demo_request_id",
    default=None,
)

TASK_AGENT_MAP = {
    "plan_task": "planner",
    "research_task": "researcher",
    "review_task": "reviewer",
}

_REQUEST_STATE_LOCK = threading.Lock()
_REQUEST_STATE: dict[str, dict[str, Any]] = {}


def set_request_id(request_id: str) -> None:
    REQUEST_ID_CONTEXT.set(request_id)


def clear_request_id() -> None:
    REQUEST_ID_CONTEXT.set(None)


def get_request_id() -> str | None:
    return REQUEST_ID_CONTEXT.get()


def init_request_state(request_id: str) -> None:
    with _REQUEST_STATE_LOCK:
        _REQUEST_STATE[request_id] = {
            "task_outputs": {},
            "task_status": {},
            "quality_flags": [],
        }


def get_request_state(request_id: str) -> dict[str, Any]:
    with _REQUEST_STATE_LOCK:
        state = _REQUEST_STATE.get(request_id, {})
        return {
            "task_outputs": dict(state.get("task_outputs", {})),
            "task_status": dict(state.get("task_status", {})),
            "quality_flags": list(state.get("quality_flags", [])),
        }


def clear_request_state(request_id: str) -> None:
    with _REQUEST_STATE_LOCK:
        _REQUEST_STATE.pop(request_id, None)


class CrewStepLogger:
    """Persist task-level execution records and lightweight request state."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._task_state: dict[str, dict[str, Any]] = {}
        self._log_path = Path(__file__).resolve().parents[2] / "logs" / "crew_steps.jsonl"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def _write_jsonl(self, payload: dict[str, Any]) -> None:
        try:
            with self._lock:
                with self._log_path.open("a", encoding="utf-8") as file:
                    file.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except OSError as exc:
            print(f"[study_demo.logger] failed to write log: {exc}", file=sys.stderr)

    def _build_preview(self, value: Any) -> str:
        text = str(value).replace("\r", " ").replace("\n", " ").strip()
        return text[:200]

    def record_quality_flag(
        self,
        *,
        request_id: str | None,
        code: str,
        message: str,
        agent_name: str = "service",
        task_name: str = "failure_strategy",
        severity: str = "warning",
    ) -> None:
        if not request_id:
            return

        payload = {
            "record_type": "quality_flag",
            "request_id": request_id,
            "agent_name": agent_name,
            "task_name": task_name,
            "code": code,
            "message": message,
            "severity": severity,
            "version_info": get_runtime_versions(),
        }

        with _REQUEST_STATE_LOCK:
            state = _REQUEST_STATE.setdefault(
                request_id,
                {"task_outputs": {}, "task_status": {}, "quality_flags": []},
            )
            state["quality_flags"].append(payload)

        self._write_jsonl(payload)

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
            "version_info": get_runtime_versions(),
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
        self._append_tool(task_id, getattr(event, "tool_name", ""))

    def on_tool_error(self, event: ToolUsageErrorEvent) -> None:
        from_task = getattr(event, "from_task", None)
        task_id = str(getattr(from_task, "id", ""))
        tool_name = getattr(event, "tool_name", "")
        self._append_tool(task_id, tool_name)

        state = self._task_state.get(task_id)
        self.record_quality_flag(
            request_id=state.get("request_id") if state else get_request_id(),
            code="tool_usage_error",
            message=f"Tool execution raised an error: {tool_name or 'unknown_tool'}",
            agent_name="researcher",
            task_name="research_task",
        )

    def _finalize_task(self, task_id: str, success: bool, output_preview: str) -> None:
        state = self._task_state.pop(task_id, None)
        if not state:
            return

        duration_ms = int((time.perf_counter() - state["started_at"]) * 1000)
        payload = {
            "record_type": "task",
            "request_id": state["request_id"],
            "agent_name": state["agent_name"],
            "task_name": state["task_name"],
            "duration_ms": duration_ms,
            "tool_calls_count": state["tool_calls_count"],
            "tool_names": state["tool_names"],
            "step_output_preview": output_preview,
            "llm_model": state["llm_model"],
            "version_info": state["version_info"],
            "success": success,
        }

        request_id = state["request_id"]
        if request_id:
            with _REQUEST_STATE_LOCK:
                request_state = _REQUEST_STATE.setdefault(
                    request_id,
                    {"task_outputs": {}, "task_status": {}, "quality_flags": []},
                )
                request_state["task_status"][state["task_name"]] = {
                    "success": success,
                    "duration_ms": duration_ms,
                    "tool_calls_count": state["tool_calls_count"],
                    "tool_names": list(state["tool_names"]),
                    "output_preview": output_preview,
                }

        self._write_jsonl(payload)

    def on_task_completed(self, event: TaskCompletedEvent) -> None:
        task_id = str(event.task_id)
        raw_output = str(getattr(event.output, "raw", event.output))
        output_preview = self._build_preview(raw_output)

        state = self._task_state.get(task_id)
        request_id = state.get("request_id") if state else None
        task_name = state.get("task_name") if state else None
        if request_id and task_name:
            with _REQUEST_STATE_LOCK:
                request_state = _REQUEST_STATE.setdefault(
                    request_id,
                    {"task_outputs": {}, "task_status": {}, "quality_flags": []},
                )
                request_state["task_outputs"][task_name] = raw_output

        self._finalize_task(task_id, True, output_preview)

    def on_task_failed(self, event: TaskFailedEvent) -> None:
        task_id = str(event.task_id)
        output_preview = self._build_preview(event.error)
        self._finalize_task(task_id, False, output_preview)


_LOGGER = CrewStepLogger()
_REGISTERED = False


def record_quality_flag(
    code: str,
    message: str,
    *,
    agent_name: str = "service",
    task_name: str = "failure_strategy",
    severity: str = "warning",
    request_id: str | None = None,
) -> None:
    _LOGGER.record_quality_flag(
        request_id=request_id or get_request_id(),
        code=code,
        message=message,
        agent_name=agent_name,
        task_name=task_name,
        severity=severity,
    )


def init_step_logging() -> None:
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

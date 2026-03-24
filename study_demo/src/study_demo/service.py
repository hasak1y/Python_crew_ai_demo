from __future__ import annotations

from pathlib import Path
from time import perf_counter
from uuid import uuid4
import json

from study_demo.logger import (
    clear_request_id,
    clear_request_state,
    get_request_id,
    get_request_state,
    init_request_state,
    record_quality_flag,
    set_request_id,
)
from study_demo.main import analyze_topic
from study_demo.versioning import get_runtime_versions

LOG_PATH = Path(__file__).resolve().parents[2] / "logs" / "crew_steps.jsonl"

TOOL_REQUIRED_HINTS = (
    "knowledge",
    "文件",
    "目录",
    "本地",
    "源码",
    "代码",
    "项目",
    "read",
    "file",
    "folder",
    "repo",
)


class ServiceError(Exception):
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


def _count_log_lines() -> int:
    if not LOG_PATH.exists():
        return 0

    with LOG_PATH.open("r", encoding="utf-8") as file:
        return sum(1 for _ in file)


def _read_log_records_from(start_line: int, request_id: str | None = None) -> list[dict]:
    if not LOG_PATH.exists():
        return []

    records: list[dict] = []
    with LOG_PATH.open("r", encoding="utf-8") as file:
        for index, line in enumerate(file):
            if index < start_line:
                continue

            line = line.strip()
            if not line:
                continue

            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue

            if request_id and payload.get("request_id") != request_id:
                continue
            records.append(payload)

    return records


def _build_trace_summary(records: list[dict]) -> list[dict]:
    version_info = get_runtime_versions()
    summary: list[dict] = [
        {
            "agent_name": "system",
            "task_name": "version_info",
            "success": True,
            "duration_ms": 0,
            "output_preview": (
                f"workflow={version_info['workflow_version']}, "
                f"prompt={version_info['prompt_version']}, "
                f"model_config={version_info['model_config_version']}, "
                f"tool={version_info['tool_version']}, "
                f"schema={version_info['schema_version']}, "
                f"model_name={version_info['model_name']}"
            ),
        }
    ]
    for item in records:
        record_type = item.get("record_type", "task")

        if record_type == "task":
            summary.append(
                {
                    "agent_name": item.get("agent_name", "unknown_agent"),
                    "task_name": item.get("task_name", "unknown_task"),
                    "success": bool(item.get("success", False)),
                    "duration_ms": int(item.get("duration_ms", 0)),
                    "output_preview": str(item.get("step_output_preview", "")),
                }
            )
            continue

        if record_type == "quality_flag":
            summary.append(
                {
                    "agent_name": item.get("agent_name", "service"),
                    "task_name": item.get("task_name", "failure_strategy"),
                    "success": False,
                    "duration_ms": 0,
                    "output_preview": str(item.get("message", "")),
                }
            )

    return summary


def _topic_requires_tooling(topic: str) -> bool:
    lowered = topic.lower()
    return any(hint in lowered for hint in TOOL_REQUIRED_HINTS)


def _quality_flag_codes(state: dict) -> list[str]:
    codes: list[str] = []
    for item in state.get("quality_flags", []):
        code = item.get("code")
        if code and code not in codes:
            codes.append(code)
    return codes


def _apply_research_quality_checks(topic: str, state: dict) -> dict:
    research_status = state.get("task_status", {}).get("research_task", {})

    if _topic_requires_tooling(topic) and research_status.get("tool_calls_count", 0) == 0:
        existing_codes = _quality_flag_codes(state)
        if "tool_not_used" not in existing_codes:
            record_quality_flag(
                "tool_not_used",
                "Research task completed without calling the expected local knowledge tools.",
                agent_name="researcher",
                task_name="research_task",
            )
            current_request_id = get_request_id()
            if current_request_id:
                return get_request_state(current_request_id)

    return state


def _build_success_response(
    *,
    request_id: str,
    final_answer: str,
    duration_ms: int,
    include_trace: bool,
    start_line: int,
    degraded: bool,
    quality_flags: list[str],
) -> dict:
    response = {
        "request_id": request_id,
        "status": "success",
        "final_answer": final_answer,
        "duration_ms": duration_ms,
        "degraded": degraded,
        "quality_flags": quality_flags or None,
        "version_info": get_runtime_versions(),
        "trace_summary": None,
    }

    if include_trace:
        response["trace_summary"] = _build_trace_summary(
            _read_log_records_from(start_line, request_id=request_id)
        )

    return response


def _classify_failure(state: dict) -> str:
    task_status = state.get("task_status", {})

    if task_status.get("plan_task", {}).get("success") is False:
        return "planner_failed"

    if task_status.get("research_task", {}).get("success") is False:
        return "researcher_failed"

    if task_status.get("review_task", {}).get("success") is False:
        return "reviewer_failed"

    return "unknown_failure"


def analyze_topic_service(
    topic: str,
    include_trace: bool = False,
    request_id: str | None = None,
) -> dict:
    request_id = request_id or str(uuid4())
    start = perf_counter()
    start_line = _count_log_lines()

    init_request_state(request_id)
    set_request_id(request_id)

    try:
        final_answer = analyze_topic(topic)
        state = get_request_state(request_id)
        state = _apply_research_quality_checks(topic, state)

        quality_flags = _quality_flag_codes(state)
        degraded = bool(quality_flags)
        duration_ms = int((perf_counter() - start) * 1000)

        return _build_success_response(
            request_id=request_id,
            final_answer=final_answer,
            duration_ms=duration_ms,
            include_trace=include_trace,
            start_line=start_line,
            degraded=degraded,
            quality_flags=quality_flags,
        )

    except Exception as exc:
        state = get_request_state(request_id)
        failure_kind = _classify_failure(state)
        duration_ms = int((perf_counter() - start) * 1000)

        if failure_kind == "reviewer_failed":
            researcher_output = state.get("task_outputs", {}).get("research_task")
            if researcher_output:
                record_quality_flag(
                    "reviewer_fallback",
                    "Reviewer failed and the service fell back to the researcher result.",
                    agent_name="service",
                    task_name="review_task",
                )
                state = get_request_state(request_id)
                state = _apply_research_quality_checks(topic, state)

                return _build_success_response(
                    request_id=request_id,
                    final_answer=researcher_output,
                    duration_ms=duration_ms,
                    include_trace=include_trace,
                    start_line=start_line,
                    degraded=True,
                    quality_flags=_quality_flag_codes(state),
                )

        if failure_kind == "planner_failed":
            raise ServiceError(
                "PLANNER_FAILED",
                "Planner failed, so the request was terminated early.",
            ) from exc

        if failure_kind == "researcher_failed":
            raise ServiceError(
                "RESEARCHER_FAILED",
                "Researcher failed to produce the core analysis result.",
            ) from exc

        raise ServiceError(
            "INTERNAL_ERROR",
            "Service failed before a recoverable fallback could be applied.",
        ) from exc

    finally:
        clear_request_id()
        clear_request_state(request_id)

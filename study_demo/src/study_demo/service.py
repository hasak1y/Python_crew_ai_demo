from __future__ import annotations

from pathlib import Path
from time import perf_counter
from uuid import uuid4
import json

from study_demo.logger import clear_request_id, set_request_id
from study_demo.main import analyze_topic


LOG_PATH = Path(__file__).resolve().parents[2] / "logs" / "crew_steps.jsonl"


def _count_log_lines() -> int:
    """返回当前日志文件的行数，用于截取本次请求新增的步骤日志。"""
    if not LOG_PATH.exists():
        return 0

    with LOG_PATH.open("r", encoding="utf-8") as file:
        return sum(1 for _ in file)


def _read_log_records_from(start_line: int, request_id: str | None = None) -> list[dict]:
    """读取从指定行号之后新增的 JSONL 记录，并可按 request_id 过滤。"""
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
                if request_id and payload.get("request_id") != request_id:
                    continue
                records.append(payload)
            except json.JSONDecodeError:
                continue
    return records


def _build_trace_summary(records: list[dict]) -> list[dict]:
    """把步骤日志收束为接口可返回的 trace_summary 结构。"""
    summary: list[dict] = []
    for item in records:
        summary.append(
            {
                "agent_name": item.get("agent_name", "unknown_agent"),
                "task_name": item.get("task_name", "unknown_task"),
                "success": bool(item.get("success", False)),
                "duration_ms": int(item.get("duration_ms", 0)),
                "output_preview": str(item.get("step_output_preview", "")),
            }
        )
    return summary


def analyze_topic_service(
    topic: str,
    include_trace: bool = False,
    request_id: str | None = None,
) -> dict:
    """组织 request_id、耗时和可选步骤摘要，供 API 层直接调用。"""
    request_id = request_id or str(uuid4())
    start = perf_counter()
    start_line = _count_log_lines()

    set_request_id(request_id)
    try:
        final_answer = analyze_topic(topic)
    finally:
        clear_request_id()

    duration_ms = int((perf_counter() - start) * 1000)

    response = {
        "request_id": request_id,
        "status": "success",
        "final_answer": final_answer,
        "duration_ms": duration_ms,
        "trace_summary": None,
    }

    if include_trace:
        response["trace_summary"] = _build_trace_summary(
            _read_log_records_from(start_line, request_id=request_id)
        )

    return response

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    topic: str = Field(
        min_length=1,
        max_length=500,
        description="Topic or task description for the current analysis request.",
        examples=["Analyze the structure and entry files of this CrewAI project."],
    )
    include_trace: bool = Field(
        default=False,
        description="Whether to include summarized execution trace data in the response.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "topic": "Analyze the structure and entry files of this CrewAI project.",
                    "include_trace": True,
                }
            ]
        }
    }


class StepSummary(BaseModel):
    agent_name: str = Field(description="Agent or service stage responsible for this step.")
    task_name: str = Field(description="Task name or synthetic decision stage.")
    success: bool = Field(description="Whether the step completed successfully.")
    duration_ms: int = Field(
        ge=0,
        description="Observed step duration in milliseconds.",
    )
    output_preview: str = Field(description="Short preview of task output or degradation note.")


class AnalyzeResponse(BaseModel):
    request_id: str = Field(description="Unique identifier for correlating response and logs.")
    status: Literal["success"] = Field(description="Successful request status.")
    final_answer: str = Field(description="Final answer returned to the caller.")
    duration_ms: int = Field(
        ge=0,
        description="Total request duration in milliseconds.",
    )
    degraded: bool = Field(
        default=False,
        description="Whether the request completed with fallback or reduced quality guarantees.",
    )
    quality_flags: list[str] | None = Field(
        default=None,
        description="Machine-readable flags describing degradation or quality concerns.",
    )
    trace_summary: list[StepSummary] | None = Field(
        default=None,
        description="Optional summarized execution trace for the request.",
    )


class ErrorResponse(BaseModel):
    request_id: str = Field(description="Unique identifier for correlating response and logs.")
    status: Literal["error"] = Field(description="Failed request status.")
    error_code: str = Field(description="Stable error code for programmatic handling.")
    message: str = Field(description="Human-readable error message.")

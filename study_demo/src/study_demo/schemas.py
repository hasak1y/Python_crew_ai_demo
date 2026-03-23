from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """第一版请求体只保留真正影响执行行为的字段。"""

    topic: str = Field(
        min_length=1,
        max_length=500,
        description="要分析的主题或任务描述；它是本次调用的核心输入，所以第一版必须保留。",
        examples=["分析这个 CrewAI 项目的结构和入口文件"],
    )
    include_trace: bool = Field(
        default=False,
        description="是否返回简化后的步骤执行摘要；它会影响响应内容，所以属于请求体控制项。",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "topic": "分析这个 CrewAI 项目的结构和入口文件",
                    "include_trace": True,
                }
            ]
        }
    }


class StepSummary(BaseModel):
    """步骤摘要只暴露对调用方有价值的最小信息。"""

    agent_name: str = Field(
        description="执行该步骤的 agent 名称；用于让调用方快速知道是谁完成了这一步。"
    )
    task_name: str = Field(
        description="当前步骤对应的 task 名称；用于把输出和流程节点对齐。"
    )
    success: bool = Field(
        description="该步骤是否成功；它是最直接的执行状态信号。"
    )
    duration_ms: int = Field(
        ge=0,
        description="该步骤耗时，单位毫秒；它用于性能观察和排障。",
    )
    output_preview: str = Field(
        description="步骤输出摘要；第一版只返回摘要，避免把完整内部内容直接暴露给前端。"
    )


class AnalyzeResponse(BaseModel):
    """成功响应聚焦业务结果和必要的观测信息。"""

    request_id: str = Field(
        description="本次请求的唯一标识；用于把接口响应和后端日志串起来。"
    )
    status: Literal["success"] = Field(
        description="请求状态；第一版固定为 success，方便前端按状态分支处理。"
    )
    final_answer: str = Field(
        description="最终返回给用户的结果；这是第一版最核心的业务产物。"
    )
    duration_ms: int = Field(
        ge=0,
        description="整次请求耗时，单位毫秒；用于接口层面的性能观察。",
    )
    trace_summary: list[StepSummary] | None = Field(
        default=None,
        description="可选的步骤摘要；仅在 include_trace=true 时返回，避免默认暴露过多内部细节。",
    )


class ErrorResponse(BaseModel):
    """错误响应和成功响应分离，避免把错误信息塞进业务结果字段。"""

    request_id: str = Field(
        description="本次请求的唯一标识；即使失败也保留，便于排查。"
    )
    status: Literal["error"] = Field(
        description="请求状态；第一版固定为 error，用于和成功响应清晰区分。"
    )
    error_code: str = Field(
        description="错误码；前端和测试可以基于它做稳定判断，而不是依赖自然语言文案。"
    )
    message: str = Field(
        description="面向调用方的错误说明；用于展示和人工排查。"
    )

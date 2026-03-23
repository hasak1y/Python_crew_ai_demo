from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient


# 让测试直接从 src 导入当前仓库代码。
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from study_demo import api
from study_demo.service import ServiceError


client = TestClient(api.app)


class ApiFailureStrategyTests(unittest.TestCase):
    """覆盖 API 层对失败策略的对外暴露行为。"""

    def test_api_returns_service_error_code(self) -> None:
        """service 抛出业务错误时，API 应保留稳定 error_code，而不是吞掉细节。"""

        def fake_analyze_topic_service(topic: str, include_trace: bool, request_id: str) -> dict:
            raise ServiceError("PLANNER_FAILED", "Planner failed, so the request was terminated early.")

        with patch.object(api, "analyze_topic_service", fake_analyze_topic_service):
            response = client.post("/analyze", json={"topic": "test", "include_trace": False})

        self.assertEqual(response.status_code, 500)
        payload = response.json()
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error_code"], "PLANNER_FAILED")

    def test_api_exposes_degraded_success_fields(self) -> None:
        """降级成功不能和标准成功混在一起，对外必须显式暴露 degraded 和 quality_flags。"""

        def fake_analyze_topic_service(topic: str, include_trace: bool, request_id: str) -> dict:
            return {
                "request_id": request_id,
                "status": "success",
                "final_answer": "fallback answer",
                "duration_ms": 12,
                "degraded": True,
                "quality_flags": ["reviewer_fallback"],
                "trace_summary": None,
            }

        with patch.object(api, "analyze_topic_service", fake_analyze_topic_service):
            response = client.post("/analyze", json={"topic": "test", "include_trace": True})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")
        self.assertTrue(payload["degraded"])
        self.assertEqual(payload["quality_flags"], ["reviewer_fallback"])

    def test_api_rejects_empty_topic_at_entry(self) -> None:
        """空 topic 属于入口非法请求，应该在进入主流程前就被拒绝。"""
        response = client.post("/analyze", json={"topic": "", "include_trace": False})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()

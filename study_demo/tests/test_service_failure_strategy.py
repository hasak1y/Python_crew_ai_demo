from __future__ import annotations

from pathlib import Path
import json
import sys
import unittest
from unittest.mock import patch


# 让测试直接从 src 导入项目代码，避免依赖额外安装包步骤。
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from study_demo import logger, service
from study_demo.tools import project_tools


DATASET_PATH = Path(__file__).resolve().parent / "datasets" / "failure_strategy_cases.json"


def load_case(case_id: str) -> dict:
    """从固定测试集里读取一个样例，避免预期散落在测试代码里。"""
    cases = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    for case in cases:
        if case["id"] == case_id:
            return case
    raise AssertionError(f"Missing dataset case: {case_id}")


class ServiceFailureStrategyTests(unittest.TestCase):
    """覆盖 service 层的失败分类、降级和回退策略。"""

    def setUp(self) -> None:
        # 每个测试前清空请求级状态，避免上一个测试污染本次断言。
        logger._REQUEST_STATE.clear()

    def test_service_marks_response_degraded_when_expected_tool_not_used(self) -> None:
        """当 topic 明显要求读文件，但 researcher 没有调工具时，结果应标记为降级成功。"""
        case = load_case("tool_not_used")

        def fake_analyze_topic(topic: str) -> str:
            request_id = logger.get_request_id()
            logger._REQUEST_STATE[request_id]["task_status"] = {
                "plan_task": {"success": True, "tool_calls_count": 0, "tool_names": [], "output_preview": "plan"},
                "research_task": {"success": True, "tool_calls_count": 0, "tool_names": [], "output_preview": "research"},
                "review_task": {"success": True, "tool_calls_count": 0, "tool_names": [], "output_preview": "review"},
            }
            logger._REQUEST_STATE[request_id]["task_outputs"] = {
                "research_task": "research result",
                "review_task": "reviewed result",
            }
            return "reviewed result"

        with patch.object(service, "analyze_topic", fake_analyze_topic):
            response = service.analyze_topic_service(case["topic"], include_trace=False, request_id="req-tool")

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["degraded"], case["expected_degraded"])
        self.assertEqual(response["quality_flags"], case["expected_quality_flags"])
        self.assertEqual(response["final_answer"], "reviewed result")

    def test_service_adds_quality_flag_into_trace_when_include_trace_enabled(self) -> None:
        """降级成功不仅要体现在字段里，也要能在 trace 里看见证据。"""
        case = load_case("tool_not_used")

        def fake_analyze_topic(topic: str) -> str:
            request_id = logger.get_request_id()
            logger._REQUEST_STATE[request_id]["task_status"] = {
                "plan_task": {"success": True, "tool_calls_count": 0, "tool_names": [], "output_preview": "plan"},
                "research_task": {"success": True, "tool_calls_count": 0, "tool_names": [], "output_preview": "research"},
                "review_task": {"success": True, "tool_calls_count": 0, "tool_names": [], "output_preview": "review"},
            }
            logger._REQUEST_STATE[request_id]["task_outputs"] = {
                "research_task": "research result",
                "review_task": "reviewed result",
            }
            return "reviewed result"

        with patch.object(service, "analyze_topic", fake_analyze_topic):
            response = service.analyze_topic_service(case["topic"], include_trace=True, request_id="req-trace")

        self.assertEqual(response["quality_flags"], ["tool_not_used"])
        self.assertIsInstance(response["trace_summary"], list)
        self.assertTrue(
            any("expected local knowledge tools" in item["output_preview"] for item in response["trace_summary"])
        )

    def test_service_falls_back_to_researcher_when_reviewer_fails(self) -> None:
        """reviewer 属于软依赖，失败后应优先回退 researcher 已产出的结果。"""
        case = load_case("reviewer_fallback")

        def fake_analyze_topic(topic: str) -> str:
            request_id = logger.get_request_id()
            logger._REQUEST_STATE[request_id]["task_status"] = {
                "plan_task": {"success": True, "tool_calls_count": 0, "tool_names": [], "output_preview": "plan"},
                "research_task": {"success": True, "tool_calls_count": 0, "tool_names": [], "output_preview": "research"},
                "review_task": {"success": False, "tool_calls_count": 0, "tool_names": [], "output_preview": "review failed"},
            }
            logger._REQUEST_STATE[request_id]["task_outputs"] = {
                "research_task": "research fallback answer",
            }
            raise RuntimeError("reviewer timeout")

        with patch.object(service, "analyze_topic", fake_analyze_topic):
            response = service.analyze_topic_service(case["topic"], include_trace=False, request_id="req-reviewer")

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["degraded"], case["expected_degraded"])
        self.assertEqual(response["quality_flags"], case["expected_quality_flags"])
        self.assertEqual(response["final_answer"], "research fallback answer")

    def test_service_returns_internal_error_when_reviewer_fails_without_research_output(self) -> None:
        """如果 reviewer 失败且 researcher 没留下可回退结果，就不能伪装成功。"""
        case = load_case("reviewer_failed_without_research_output")

        def fake_analyze_topic(topic: str) -> str:
            request_id = logger.get_request_id()
            logger._REQUEST_STATE[request_id]["task_status"] = {
                "plan_task": {"success": True, "tool_calls_count": 0, "tool_names": [], "output_preview": "plan"},
                "research_task": {"success": True, "tool_calls_count": 0, "tool_names": [], "output_preview": "research"},
                "review_task": {"success": False, "tool_calls_count": 0, "tool_names": [], "output_preview": "review failed"},
            }
            raise RuntimeError("reviewer timeout without fallback")

        with patch.object(service, "analyze_topic", fake_analyze_topic):
            with self.assertRaises(service.ServiceError) as exc_info:
                service.analyze_topic_service(case["topic"], include_trace=False, request_id="req-reviewer-no-fallback")

        self.assertEqual(exc_info.exception.error_code, case["expected_error_code"])

    def test_service_fails_fast_when_planner_fails(self) -> None:
        """planner 是硬依赖节点，失败后必须立即终止请求。"""
        case = load_case("planner_failed")

        def fake_analyze_topic(topic: str) -> str:
            request_id = logger.get_request_id()
            logger._REQUEST_STATE[request_id]["task_status"] = {
                "plan_task": {"success": False, "tool_calls_count": 0, "tool_names": [], "output_preview": "planner failed"},
            }
            raise RuntimeError("planner failed")

        with patch.object(service, "analyze_topic", fake_analyze_topic):
            with self.assertRaises(service.ServiceError) as exc_info:
                service.analyze_topic_service(case["topic"], include_trace=False, request_id="req-planner")

        self.assertEqual(exc_info.exception.error_code, case["expected_error_code"])

    def test_service_fails_fast_when_researcher_fails(self) -> None:
        """researcher 的核心生成失败属于硬失败，不允许回退成伪结果。"""
        case = load_case("researcher_failed")

        def fake_analyze_topic(topic: str) -> str:
            request_id = logger.get_request_id()
            logger._REQUEST_STATE[request_id]["task_status"] = {
                "plan_task": {"success": True, "tool_calls_count": 0, "tool_names": [], "output_preview": "plan"},
                "research_task": {"success": False, "tool_calls_count": 0, "tool_names": [], "output_preview": "research failed"},
            }
            raise RuntimeError("researcher failed")

        with patch.object(service, "analyze_topic", fake_analyze_topic):
            with self.assertRaises(service.ServiceError) as exc_info:
                service.analyze_topic_service(case["topic"], include_trace=False, request_id="req-researcher")

        self.assertEqual(exc_info.exception.error_code, case["expected_error_code"])

    def test_service_returns_internal_error_for_unknown_failure_kind(self) -> None:
        """如果异常没有命中已知失败分类，service 也要统一折叠成内部错误。"""
        case = load_case("unknown_internal_failure")

        def fake_analyze_topic(topic: str) -> str:
            raise RuntimeError("unexpected failure before any task state is written")

        with patch.object(service, "analyze_topic", fake_analyze_topic):
            with self.assertRaises(service.ServiceError) as exc_info:
                service.analyze_topic_service(case["topic"], include_trace=False, request_id="req-unknown")

        self.assertEqual(exc_info.exception.error_code, case["expected_error_code"])

    def test_tool_returns_standardized_error_marker_for_missing_file(self) -> None:
        """tool 缺文件时应该返回可识别错误前缀，便于上层做降级判断。"""
        result = project_tools.read_local_file.func("missing-file.txt")
        self.assertTrue(result.startswith("[TOOL_ERROR:tool_file_not_found]"))

    def test_tool_rejects_paths_outside_allowed_directory(self) -> None:
        """tool 不能读取 knowledge 白名单之外的路径，避免越权访问。"""
        case = load_case("tool_path_not_allowed")
        result = project_tools.read_local_file.func("../README.md")
        self.assertTrue(result.startswith(case["expected_error_prefix"]))


if __name__ == "__main__":
    unittest.main()

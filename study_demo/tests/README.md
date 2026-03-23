# 测试说明

这个目录用于存放 `study_demo` 的回归测试。

## 约定

后续改动统一按下面顺序进行：

1. 先在 `datasets/` 里新增或修改固定测试样例。
2. 再补对应的测试代码，让预期行为先被写清楚。
3. 先运行测试，确认新增测试在修改实现前会按预期失败。
4. 再修改业务代码。
5. 修改完成后重新跑测试，直到全部通过。

这套流程的目标不是“补作业”，而是确保后续每次改 prompt、task、tool、schema 或失败策略时，都有明确的回归依据。

## 当前测试文件

`test_service_failure_strategy.py`

- 覆盖 service 层的失败分类、降级策略、回退策略和质量标记。
- 重点验证硬依赖失败是否 fail-fast，软依赖失败是否 graceful degradation。

`test_api_failure_strategy.py`

- 覆盖 API 层对 service 结果的对外暴露行为。
- 重点验证错误码、降级成功字段和非法请求的返回。

`datasets/failure_strategy_cases.json`

- 存放固定失败样例。
- 后续如果要补“黄金样例测试”，也优先继续放在 `datasets/` 下单独管理。

## 当前失败策略测试覆盖范围

目前已经覆盖的核心场景包括：

- `planner` 失败时，是否直接终止请求。
- `researcher` 核心失败时，是否直接终止请求。
- `reviewer` 失败但 `researcher` 已有结果时，是否回退到 `researcher` 结果。
- `reviewer` 失败且没有可回退结果时，是否返回内部错误。
- 请求整体异常但没有命中已知分类时，是否返回内部错误。
- 需要使用 tool 却没有使用时，是否标记为降级成功。
- `include_trace=true` 时，降级标记是否能进入 `trace_summary`。
- tool 缺文件或越权访问时，是否返回标准化错误标记。
- API 是否正确暴露 `error_code`、`degraded`、`quality_flags`。
- API 对空 topic 这类入口错误是否按预期拒绝。

## 运行命令

当前项目环境下建议使用你的 Conda 环境执行：

```powershell
& 'C:\Users\24044\.conda\envs\Python_crew_ai_demo\python.exe' -m unittest discover -s study_demo/tests -p "test_*.py" -v
```

# 03 评估预期、实际结果与限制

## 运行环境与方法

本地环境：Windows、Python 3.11.9。离线运行 `python -m unittest discover -s tests -v` 与 `python examples/generate_mock_examples.py`。Mock 输入、终端输出和完整 Trace 在 `examples/mock/`。2026-10-30 又以真实 `deepseek-flash` 运行，结果在 `examples/live/`；密钥只从本机环境变量读取，未写入示例。

## 离线流程结果

| 示例 | 预期 | 实际 | 证据 |
| --- | --- | --- | --- |
| 01 普通事假 | L01 明确回答 | `answered`，3 步、3 次工具调用 | `examples/mock/01-normal.*` |
| 02 一般报销 | D01/D02 冲突并追问 | `conflict`，5 步、5 次工具调用 | `examples/mock/02-conflict.*` |
| 03 远程办公天数 | 不编造数字 | `insufficient`，3 步、3 次工具调用 | `examples/mock/03-insufficient.*` |
| 04 搜索失败 | 不伪装成功 | `tool_error`，2 步、2 次工具调用 | `examples/mock/04-tool-failure.*` |
| 05 相似问法 | 与 01 同一依据 | `answered`，L01 引文 | `examples/mock/05-paraphrase.*` |
| 06 差旅范围 | 用 D03，不套一般费用 | `answered`，D03 引文 | `examples/mock/06-travel-scope.*` |

15 项单元测试通过，覆盖冲突、范围、资料不足、工具故障、伪造引用拒绝、未引用文档/数值拒绝、执行上限、正常证据链、上下文追问、历史输入校验、DeepSeek 请求格式和展示服务的 HTTP 行为。

## DeepSeek 真实运行结果

模型为 `deepseek-flash`，日期为 2026-10-30。运行命令格式：`python main.py ask "问题" --provider deepseek --trace run-output/文件名.json`。原始 Trace 和输出已复制到 `examples/live/`，可核对每次工具参数、返回摘要与最终状态。

| 场景 | 实际状态与工具路径 | 结果与证据 |
| --- | --- | --- | --- |
| 普通事假 | `answered`；检索 → 读 L01 → 回答 | 通过；`live-normal.*` |
| 一般报销首次 | `conflict`；检索 → 读 D01/D02 → 查冲突 → 回答 | **内容未通过人工复核**：附带未引用的差旅期限；`live-conflict.*` |
| 一般报销首次修复后 | `conflict`；同一路径 | **仍未通过人工复核**：未写 D03 ID，但仍附带该数值；`live-conflict-fixed.*` |
| 一般报销最终 | `conflict`；检索 → 读 D01/D02 → 查冲突 → 提交被拒 → 修正提交 | 通过；双引用、无旁支数值、明确追问；`live-conflict-final.*` |
| 远程办公天数 | `insufficient`；检索 → 读 R01 → 说明缺口 | 通过；`live-insufficient.*` |
| 相似问法 | `answered`；检索 → 读 L01 → 回答 | 通过；`live-paraphrase.*` |
| 检索故障 | `tool_error`；检索失败 → 再试失败 → 停止 | 通过；未伪造答案；`live-tool-failure.*` |
| 上下文追问 | `answered`；带前轮问答 → 检索 → 读 L01 → 回答 | 通过；引用紧急情况原文；`live-follow-up.*` |

另以 Chrome 对本地展示界面进行真实浏览器联调：逐一点击明确答案、资料冲突和资料缺口示例，等待真实模型返回后检查状态、证据卡片和工具轨迹。实际页面截图见 `docs/screenshots/01-home.png` 至 `04-insufficient.png`；截图仅证明可见结果，模型决策细节以 JSON Trace 为准。

## 已知问题与失效边界

字符二元组检索可能漏掉语义相近但字面差异大的表达；同范围判断采用精确字符串相等，复杂的部门/日期包含关系尚未覆盖。逐字引用校验不能完全证明自然语言回答的逻辑正确性。真实模型输出可能因型号、服务版本和采样而变化，必须以实测 Trace 为准。工具错误与 API 错误已区分，但没有生产级监控或权限隔离。

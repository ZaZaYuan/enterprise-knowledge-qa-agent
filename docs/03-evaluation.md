# 03 评估预期、实际结果与限制

## 运行环境与方法

本地环境：Windows、Python 3.11.9。离线运行 `python -m unittest discover -s tests -v` 与 `python examples/generate_mock_examples.py`。实际输入、终端输出和完整 Trace 在 `examples/mock/`，均标为 `OFFLINE_MOCK`。真实模型所需 `DEEPSEEK_API_KEY` 尚未在本地进程配置；因此下面不声称完成 DeepSeek 实测。

## 离线流程结果

| 示例 | 预期 | 实际 | 证据 |
| --- | --- | --- | --- |
| 01 普通事假 | L01 明确回答 | `answered`，3 步、3 次工具调用 | `examples/mock/01-normal.*` |
| 02 一般报销 | D01/D02 冲突并追问 | `conflict`，5 步、5 次工具调用 | `examples/mock/02-conflict.*` |
| 03 远程办公天数 | 不编造数字 | `insufficient`，3 步、3 次工具调用 | `examples/mock/03-insufficient.*` |
| 04 搜索失败 | 不伪装成功 | `tool_error`，2 步、2 次工具调用 | `examples/mock/04-tool-failure.*` |
| 05 相似问法 | 与 01 同一依据 | `answered`，L01 引文 | `examples/mock/05-paraphrase.*` |
| 06 差旅范围 | 用 D03，不套一般费用 | `answered`，D03 引文 | `examples/mock/06-travel-scope.*` |

7 项单元测试通过，覆盖冲突、范围、资料不足、工具故障、伪造引用拒绝、执行上限与正常证据链。这些是程序流程验证，不构成真实模型效果评估。

## DeepSeek 实测待填

完成本机新密钥配置后，运行至少三种不同输入，保存 `examples/live/` 的实际输出和 Trace，并在这里记录模型名、运行日期、通过/未通过、主要工具路径及失败原因。若模型未选择预期工具、回答被护栏拒绝或 API 不可用，应如实记录为未通过或未验证，不能拿 Mock 结果替代。

| 场景 | 模型与日期 | 实际状态/路径 | 结果 |
| --- | --- | --- | --- |
| 明确答案 | 待实测 | 待实测 | 未验证 |
| 冲突资料 | 待实测 | 待实测 | 未验证 |
| 资料不足或工具故障 | 待实测 | 待实测 | 未验证 |

## 已知问题与失效边界

字符二元组检索可能漏掉语义相近但字面差异大的表达；同范围判断采用精确字符串相等，复杂的部门/日期包含关系尚未覆盖。逐字引用校验不能完全证明自然语言回答的逻辑正确性。真实模型输出可能因型号、服务版本和采样而变化，必须以实测 Trace 为准。工具错误与 API 错误已区分，但没有生产级监控或权限隔离。

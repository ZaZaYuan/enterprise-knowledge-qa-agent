# 示例运行记录

`mock/` 文件由 `python examples/generate_mock_examples.py` 实际生成，明确标记 `OFFLINE_MOCK`。它们只证明 CLI、工具、引用校验、冲突处理和执行上限的流程可以复现，**不证明真实模型会作出同样决策**。

`live/` 保存 2026-10-30 使用真实 `deepseek-flash` 运行的 JSON Trace 与对应终端输出。运行时从本机 `DEEPSEEK_API_KEY` 读取凭据；文件内没有密钥。`live-conflict.json` 是首次回答：状态为 `conflict`，但人工复核发现顺带提及未引用的差旅期限；它保留为失败证据。加入额外引用校验后，`live-conflict-fixed.json` 仍暴露同类缺口；`live-conflict-final.json` 的 Trace 记录了程序拒绝未引用数值、模型修正后再次提交的过程。不要把首次状态码 `conflict` 误当成内容全部合格。

| 编号 | 问题类型 | 预期重点 |
| --- | --- | --- |
| 01 | 普通事假 | 有原文支持的明确答案 |
| 02 | 一般费用报销 | D01/D02 冲突、双引用、请求确认 |
| 03 | 远程办公天数 | 资料不足，不编造数字 |
| 04 | 搜索工具故障 | 明确故障与未核实状态 |
| 05 | 相似问法 | 与 01 相同的证据链 |
| 06 | 差旅适用范围 | D03 的返程后期限，不误套一般费用规则 |
| 07 | 上下文追问 | 结合 `context-history.json` 理解“那紧急情况呢？”并引用 L01 |

真实模型追问记录见 `live/live-follow-up.json` 与同名输出文本；命令为 `python main.py ask "那紧急情况呢？" --provider deepseek --history examples/context-history.json --trace run-output/live-follow-up.json`。

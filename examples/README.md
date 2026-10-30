# 示例运行记录

`mock/` 文件由 `python examples/generate_mock_examples.py` 实际生成，明确标记 `OFFLINE_MOCK`。它们只证明 CLI、工具、引用校验、冲突处理和执行上限的流程可以复现，**不证明真实模型会作出同样决策**。

取得安全配置的真实 DeepSeek API 密钥后，使用 `python main.py ask "问题" --provider deepseek --trace examples/live/文件名.json` 逐条运行，再将终端输出、模型名和 Trace 放入 `examples/live/`。未真实执行前，不创建或伪造 live 文件。

| 编号 | 问题类型 | 预期重点 |
| --- | --- | --- |
| 01 | 普通事假 | 有原文支持的明确答案 |
| 02 | 一般费用报销 | D01/D02 冲突、双引用、请求确认 |
| 03 | 远程办公天数 | 资料不足，不编造数字 |
| 04 | 搜索工具故障 | 明确故障与未核实状态 |
| 05 | 相似问法 | 与 01 相同的证据链 |
| 06 | 差旅适用范围 | D03 的返程后期限，不误套一般费用规则 |

"""ReportAgent — 汇总各子 Agent 结果, 生成 Markdown 诊断报告"""

NAME = "report_agent"
DESCRIPTION = "汇总各子 Agent 的检查结果, 生成诊断报告"

# ReportAgent 无外部工具, 通过 llm 直接生成
TOOLS = []

SYSTEM_PROMPT = """你是运维诊断报告生成器。你会收到多个子 Agent 的检查结果:
- 服务发现结果 (哪些服务在运行)
- 健康检查结果 (端口/HTTP 状态)
- 日志分析结果 (错误日志)
- 数据库状态 (MySQL/Redis)

请生成一份结构化的 Markdown 诊断报告, 包含:
1. 系统概览: 服务数量、实例数、整体状态
2. 异常汇总: 哪些服务异常, 异常类型
3. 数据库健康: MySQL/Redis 关键指标, 是否有隐患
4. 诊断建议: 按严重程度排序的行动建议

要求: 基于事实, 不编造。若某服务未运行, 明确标注"已下线"而非推断原因。"""


def build_context(discovery_result: str, health_result: str,
                   log_result: str, db_result: str) -> str:
    """把各子 Agent 的原始输出拼成 context"""
    return f"""## 服务发现结果
{discovery_result}

## 健康检查结果
{health_result}

## 日志分析结果
{log_result}

## 数据库状态
{db_result}
"""

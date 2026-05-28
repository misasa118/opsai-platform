# backend/app/services/agent_service.py
# 这段代码 = 给 AI 巡检机器人定义一个「记忆本」
# 规定机器人必须记住：
# 用户要干嘛 → 意图是什么 → 查了哪些数据 → 发现什么问题 → 最终报告

from typing import TypedDict, List, Optional, Annotated # TypedDict：给字典定结构（interface）
import operator 

# 定义一个叫 InspectionState 的字典结构 = AI 机器人的全局记忆
class InspectionState(TypedDict):
    # ── 用户输入（用户想干嘛）：巡检哪台机器/用户说了什么
    server_name: str              # 要巡检的服务器名
    user_request: str             # 用户原始请求

    # ── 意图判断（AI 先判断能不能做）
    intent: str                   # 'inspect' | 'dangerous' | 'unknown'
    reject_reason: Optional[str]  # 如果是危险操作，拒绝原因

    # ── 各节点的检查结果
    metrics_result: Optional[dict]    # CPU/内存指标
    sql_result: Optional[list]        # 慢 SQL 列表
    tablespace_result: Optional[dict] # 表空间使用率

    # ── 发现的问题列表（使用 Annotated + operator.add 支持并行追加）
    # operator.add 的作用：多个节点同时写 issues 时，自动合并而不是覆盖
    # issues：存所有发现的问题
    # Annotated[List[str], operator.add]
    # → 多个节点同时发现问题，自动合并列表，不会覆盖！
    # 普通列表：
    # 节点 1 写 → 覆盖
    # 节点 2 写 → 覆盖
    # 最后只剩最后一个
    # 用了 Annotated + operator.add：
    # 节点 1 添加 → [问题A]
    # 节点 2 添加 → [问题A, 问题B]
    # 节点 3 添加 → [问题A, B, C]
    # 自动合并，不会覆盖！
    # 这就是 LangGraph 并行执行的核心魔法。
    issues: Annotated[List[str], operator.add]

    # ── 进度日志（实时推送给前端）
    progress: Annotated[List[str], operator.add]

    # ── 最终产出
    report_md: Optional[str]      # Markdown 格式的巡检报告
    is_completed: bool            # 是否完成

# backend/app/services/agent_service.py（续）
# 这段代码 = AI 巡检机器人的安全大门 + 意图识别器
# 先拦危险操作（删库、删表、关机… 绝对不让过）
# 再判断用户想干嘛
# 巡检 → 放行
# 危险 → 拒绝
# 听不懂 → 回复不知道
import re

# ── 危险操作关键词（Rule-based，硬编码，不让 AI 决定）
DANGEROUS_PATTERNS = [
    r'delete\s+from',      # DELETE 操作
    r'drop\s+table',       # DROP TABLE
    r'truncate',            # TRUNCATE
    r'shutdown',            # 数据库关闭
    r'rm\s+-rf',           # 危险 shell 命令
    r'format',              # 格式化
]

# 危险检测函数 扫描用户输入 → 发现危险关键词 → 返回 True/False + 原因
def is_dangerous_request(user_request: str) -> tuple[bool, str]:
    '''
    Rule-based 危险操作检测。
    返回 (是否危险, 拒绝原因)
    这里绝对不能用 AI 判断 —— AI 可能被提示词注入攻击欺骗。
    '''
    request_lower = user_request.lower()
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, request_lower):
            return True, f'检测到危险操作关键词: [{pattern}]，已自动拒绝'
    return False, ''

# 核心：意图分类节点（Node 1） 输入：state（记忆本） 输出：更新后的 state
async def classify_intent(state: InspectionState) -> InspectionState:
    '''
    节点1：意图分类
    先用 Rule-based 检查是否是危险操作，再用 AI 理解用户意图。
    '''
    user_request = state['user_request']

    # Rule-based 检查（优先级最高） 先做最高优先级的安全检查 
    is_dangerous, reason = is_dangerous_request(user_request)
    if is_dangerous:
        return {
            'intent': 'dangerous',
            'reject_reason': reason,
            'progress': [f'🚫 请求被拒绝：{reason}'],
            'issues': [],
        }

    # AI 分类（只有通过 Rule-based 检查才走这里）
    # 简化版：直接判断是否是巡检请求
    inspect_keywords = ['巡检', '检查', '查看', '状态', '健康', 'inspect', 'check']
    if any(kw in user_request.lower() for kw in inspect_keywords):
        return {
            'intent': 'inspect',
            'reject_reason': None,
            'progress': [f'✅ 意图识别：开始巡检 {state["server_name"]}'],
            'issues': [],
        }

    return {
        'intent': 'unknown',
        'reject_reason': '无法识别请求意图，请描述您要执行的巡检任务',
        'progress': ['❓ 意图未识别'],
        'issues': [],
    }

# backend/app/services/agent_service.py（续）
# 这 3 个 async 函数 = LangGraph 里的 3 个并行执行节点
# check_metrics → 查服务器 CPU / 内存
# check_slow_sql → 查慢 SQL
# check_tablespace → 查表空间使用率
# 它们同时并行跑，不互相等待，最后结果自动合并！
import random, asyncio
from datetime import datetime

async def check_metrics(state: InspectionState) -> InspectionState:
    '''节点2a：检查 CPU / 内存指标（模拟数据，生产环境连接真实监控API）'''
    server = state['server_name']
    await asyncio.sleep(0.5)  # 模拟查询耗时

    # 生产环境替换为：调用 AWS CloudWatch / OCI Monitoring API
    cpu_avg  = round(random.uniform(45, 95), 1)
    cpu_peak = round(random.uniform(cpu_avg, 100), 1)
    mem_pct  = round(random.uniform(55, 92), 1)

    issues = []
    if cpu_peak > 90:
        issues.append(f'⚠️ CPU 峰值 {cpu_peak}% 超过阈值（90%）')
    if mem_pct > 85:
        issues.append(f'⚠️ 内存使用率 {mem_pct}% 超过阈值（85%）')

    return {
        'metrics_result': {
            'cpu_avg': cpu_avg, 'cpu_peak': cpu_peak, 'mem_pct': mem_pct
        },
        'issues': issues,
        'progress': [f'✅ 性能指标检查完成：CPU均值{cpu_avg}% / 内存{mem_pct}%'],
    }


async def check_slow_sql(state: InspectionState) -> InspectionState:
    '''节点2b：检查慢 SQL（模拟数据）'''
    await asyncio.sleep(0.8)

    mock_sqls = [
        {'sql': "SELECT * FROM orders WHERE TO_CHAR(dt,'YYYY')='2024'",
         'elapsed_ms': 12300, 'executions': 1520},
        {'sql': 'SELECT COUNT(*) FROM logs WHERE status != \'OK\'',
         'elapsed_ms': 8700, 'executions': 8900},
    ]

    issues = []
    for s in mock_sqls:
        if s['elapsed_ms'] > 5000:
            issues.append(f"⚠️ 慢SQL：{s['sql'][:50]}... 平均耗时{s['elapsed_ms']}ms")

    return {
        'sql_result': mock_sqls,
        'issues': issues,
        'progress': [f'✅ 慢SQL分析完成：发现 {len(mock_sqls)} 条慢查询'],
    }


async def check_tablespace(state: InspectionState) -> InspectionState:
    '''节点2c：检查表空间使用率（模拟数据）'''
    await asyncio.sleep(0.6)

    tablespaces = [
        {'name': 'USERS',   'used_pct': round(random.uniform(70, 98), 1)},
        {'name': 'UNDOTBS1','used_pct': round(random.uniform(40, 85), 1)},
        {'name': 'TEMP',    'used_pct': round(random.uniform(20, 70), 1)},
        {'name': 'SYSTEM',  'used_pct': round(random.uniform(30, 55), 1)},
    ]

    issues = [
        f"⚠️ 表空间 {ts['name']} 使用率 {ts['used_pct']}% 超过阈值（80%）"
        for ts in tablespaces if ts['used_pct'] > 80
    ]

    return {
        'tablespace_result': {'tablespaces': tablespaces},
        'issues': issues,
        'progress': [f'✅ 表空间检查完成：{len(tablespaces)} 个表空间已检查'],
    }

# backend/app/services/agent_service.py（续）
# 把前面所有节点，用 LangGraph 拼成一个自动化巡检工作流！
from openai import AsyncOpenAI
from langgraph.graph import StateGraph, END
from ..config import settings

# LLM 客户端初始化 调用大模型生成最终的巡检报告
llm_client = AsyncOpenAI(
    api_key=settings.GROQ_API_KEY,
    base_url='https://api.groq.com/openai/v1'
)

# 节点 3：generate_report —— 生成最终报告
# 这是汇总所有数据 → 调用 LLM → 输出专业 Markdown 报告
async def generate_report(state: InspectionState) -> InspectionState:
    '''节点3：调用 LLM 生成 Markdown 巡检报告'''
    server = state['server_name']
    metrics = state.get('metrics_result', {})
    sqls = state.get('sql_result', [])
    ts = state.get('tablespace_result', {}).get('tablespaces', [])
    issues = state.get('issues', [])

    prompt = f'''请基于以下巡检数据，生成一份专业的 Oracle 数据库巡检报告。
用 Markdown 格式，包含：摘要、详细数据、问题清单、处理建议。

服务器：{server}
巡检时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}

性能指标：
- CPU 均值：{metrics.get('cpu_avg')}%，峰值：{metrics.get('cpu_peak')}%
- 内存使用率：{metrics.get('mem_pct')}%

慢 SQL（Top {len(sqls)} 条）：
{chr(10).join([f'- {s["sql"][:60]}... 耗时{s["elapsed_ms"]}ms' for s in sqls])}

表空间使用率：
{chr(10).join([f'- {t["name"]}: {t["used_pct"]}%' for t in ts])}

发现问题：
{chr(10).join(issues) if issues else '未发现异常'}
'''

    resp = await llm_client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[
            {'role': 'system', 'content': '你是专业的 Oracle DBA，用简洁专业的中文生成巡检报告。'},
            {'role': 'user', 'content': prompt}
        ],
        temperature=0.3,
    )
    report = resp.choices[0].message.content

    return {
        'report_md': report,
        'is_completed': True,
        'progress': ['📋 巡检报告生成完成'],
    }

# 节点：reject_request —— 危险 / 未知请求拒绝节点
# 用户想删库、搞破坏、或说听不懂的话 → 直接返回拒绝文案
async def reject_request(state: InspectionState) -> InspectionState:
    '''节点：拒绝危险操作'''
    return {
        'report_md': f'# 请求被拒绝\n\n{state.get("reject_reason", "危险操作")}',
        'is_completed': True,
        'progress': [],
    }


# ── 条件路由函数（Rule-based 决策）
def route_by_intent(state: InspectionState) -> str:
    '''根据意图分类结果，决定走哪条路径'''
    intent = state.get('intent', 'unknown')
    if intent == 'inspect':
        return 'run_checks'   # 正常巡检
    else:
        return 'reject'       # 拒绝危险/未知操作


# ── 构建 LangGraph 工作流图 最核心：构建 LangGraph 图
def build_inspection_graph():
    graph = StateGraph(InspectionState)

    # 添加节点
    graph.add_node('classify_intent', classify_intent)
    graph.add_node('check_metrics',   check_metrics)
    graph.add_node('check_slow_sql',  check_slow_sql)
    graph.add_node('check_tablespace',check_tablespace)
    graph.add_node('generate_report', generate_report)
    graph.add_node('reject_request',  reject_request)

    # 设置入口节点
    graph.set_entry_point('classify_intent')

    # 条件边：意图分类后，根据结果路由
    graph.add_conditional_edges(
        'classify_intent',
        route_by_intent,
        {
            'run_checks': 'check_metrics',  # 正常路径：先执行第一个检查
            'reject': 'reject_request',     # 拒绝路径
        }
    )

    # 普通边：三个检查节点都连向报告生成
    # 注意：LangGraph 会等三个节点都完成后才执行 generate_report
    graph.add_edge('check_metrics',    'check_slow_sql')
    graph.add_edge('check_slow_sql',   'check_tablespace')
    graph.add_edge('check_tablespace', 'generate_report')
    graph.add_edge('generate_report',  END)
    graph.add_edge('reject_request',   END)

    return graph.compile()


# 全局单例（应用启动时初始化一次）
inspection_graph = build_inspection_graph()
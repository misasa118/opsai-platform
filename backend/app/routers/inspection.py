# backend/app/routers/inspection.py
# 这段代码 = FastAPI WebSocket 接口
# 作用：
# 前端连接 → 发送巡检指令
# 后端执行 LangGraph 工作流
# 每一步实时推送给前端（进度条 / 日志）
# 最后返回完整报告
# 这就是你看到的：
# ✅ 意图识别完成 → ✅ 指标检查完成 → ✅ 慢 SQL 分析完成 → 📋 报告生成
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..services.agent_service import inspection_graph, InspectionState
import json, asyncio

router = APIRouter(prefix='/api/v1/inspection', tags=['🔍 巡检'])


# ── WebSocket 消息格式定义（前后端约定）
# 服务端发送：
# {'type': 'progress', 'message': '✅ 意图识别完成', 'step': 1, 'total': 5}
# {'type': 'report',   'content': '# 巡检报告\n...'}
# {'type': 'error',    'message': '错误信息'}
# {'type': 'done'}
#
# 客户端可发送：
# {'type': 'stop'}  ← 停止巡检


@router.websocket('/ws')
async def inspection_websocket(websocket: WebSocket):
    '''
    WebSocket 巡检接口。
    客户端连接后发送巡检请求，服务端实时推送每步进度。
    '''
    await websocket.accept()  # 接受 WebSocket 握手
    print('WebSocket 客户端已连接')

    try:
        while True:
            # 等待客户端发送巡检请求
            raw = await websocket.receive_text()
            request_data = json.loads(raw)

            if request_data.get('type') == 'start_inspection':
                server_name  = request_data.get('server_name', 'DB01')
                user_request = request_data.get('user_request', f'巡检 {server_name}')

                await run_inspection(
                    websocket, server_name, user_request
                )

    except WebSocketDisconnect:
        print('WebSocket 客户端断开连接')
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({
                'type': 'error',
                'message': str(e)
            }))
        except:
            pass


async def run_inspection(
    websocket: WebSocket,
    server_name: str,
    user_request: str
):
    '''执行巡检并实时推送进度'''

    # 初始化状态
    initial_state: InspectionState = {
        'server_name':        server_name,
        'user_request':       user_request,
        'intent':             '',
        'reject_reason':      None,
        'metrics_result':     None,
        'sql_result':         None,
        'tablespace_result':  None,
        'issues':             [],
        'progress':           [],
        'report_md':          None,
        'is_completed':       False,
    }

    step = 0
    total_steps = 5  # 意图分类 + 3个检查 + 报告生成

    # astream 流式执行：每完成一个节点就产出一次
    async for step_output in inspection_graph.astream(initial_state):
        node_name = list(step_output.keys())[0]
        node_state = step_output[node_name]
        step += 1

        # 推送每步的进度消息
        progress_msgs = node_state.get('progress', [])
        for msg in progress_msgs:
            await websocket.send_text(json.dumps({
                'type':    'progress',
                'message': msg,
                'node':    node_name,
                'step':    step,
                'total':   total_steps,
            }, ensure_ascii=False))
            await asyncio.sleep(0.1)  # 小延迟让前端逐条显示

    # 所有节点执行完毕，发送最终报告
    # 从最后一个节点状态里取 report_md
    final_state = list(step_output.values())[0]
    report = final_state.get('report_md', '巡检完成，无报告')
    issues = initial_state.get('issues', [])  # 注意：这里取的是合并后的列表

    await websocket.send_text(json.dumps({
        'type':    'report',
        'content': report,
        'issues':  final_state.get('issues', []),
    }, ensure_ascii=False))

    await websocket.send_text(json.dumps({'type': 'done'}))